#!/usr/bin/env python3

import asyncio
import json
import os
import sys
import re
from typing import Any, Dict, List, Optional, Tuple
from html.parser import HTMLParser
import tempfile
import uuid
from collections import defaultdict

import aiohttp

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

# Constants from environment variables
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL")
JIRA_URL = os.environ.get("JIRA_URL", "").rstrip("/")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
PROJECT_KEY = os.environ.get("PROJECT_KEY")
GUIDELINES_PAGE_ID = os.environ.get("GUIDELINES_PAGE_ID")
GUIDELINES_DIRECT_URL = os.environ.get("GUIDELINES_DIRECT_URL")

# GitHub context
GITHUB_EVENT_PATH = os.environ.get("GITHUB_EVENT_PATH")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_API_URL = os.environ.get("GITHUB_API_URL", "https://api.github.com")

class GuidelinesHTMLParser(HTMLParser):
    """Simple HTML parser to extract guidelines from Confluence HTML content."""
    
    def __init__(self):
        super().__init__()
        self.rules = []
        self.current_text = []
        self.in_li = False
        self.in_p = False
        self.in_heading = False
    
    def handle_starttag(self, tag, attrs):
        if tag == 'li':
            self.in_li = True
            self.current_text = []
        elif tag == 'p':
            self.in_p = True
            self.current_text = []
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.in_heading = True
            self.current_text = []
    
    def handle_endtag(self, tag):
        if tag == 'li' and self.in_li:
            rule_text = ''.join(self.current_text).strip()
            if rule_text:
                self.rules.append(('guideline', rule_text))
            self.in_li = False
        elif tag == 'p' and self.in_p:
            text = ''.join(self.current_text).strip()
            if text and len(text) > 15:  # Avoid short paragraphs that aren't likely rules
                self.rules.append(('paragraph', text))
            self.in_p = False
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6') and self.in_heading:
            text = ''.join(self.current_text).strip()
            if text:
                self.rules.append(('heading', text))
            self.in_heading = False
    
    def handle_data(self, data):
        if self.in_li or self.in_p or self.in_heading:
            self.current_text.append(data)

class GuidelinesRAG:
    """Retrieval-Augmented Generation for code guidelines."""
    
    def __init__(self, guidelines: List[Dict[str, str]]):
        self.guidelines = guidelines
        self.model = None
        self.embeddings = None
        self.initialize_embeddings()
        
        # Default categories for guidelines
        self.categories = {
            "indentation": ["indent", "indentation", "spaces", "tabs"],
            "naming": ["naming", "convention", "variable", "function", "class", "camelcase", "snake_case"],
            "documentation": ["document", "documentation", "comment", "docstring"],
            "testing": ["test", "unit test", "integration test", "mock"],
            "line_length": ["line length", "character", "columns", "width"],
            "imports": ["import", "module", "package", "dependency"],
            "error_handling": ["error", "exception", "try", "catch", "except"],
            "formatting": ["format", "style", "lint"],
            "security": ["security", "vulnerability", "injection", "sanitize"],
            "performance": ["performance", "optimization", "efficient"]
        }
    
    def initialize_embeddings(self):
        """Initialize sentence embeddings model if available."""
        if not EMBEDDING_AVAILABLE:
            print("Warning: sentence-transformers not available. Using keyword matching instead.")
            return
        
        try:
            # Use a lightweight model that works well for English text
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Embed all guidelines
            texts = [g["text"] for g in self.guidelines]
            self.embeddings = self.model.encode(texts)
            print(f"Successfully initialized embeddings for {len(texts)} guidelines")
        except Exception as e:
            print(f"Error initializing embeddings: {str(e)}")
            self.model = None
            self.embeddings = None
    
    def categorize_guidelines(self) -> Dict[str, List[Dict[str, str]]]:
        """Categorize guidelines into different topics."""
        categorized = defaultdict(list)
        
        for guideline in self.guidelines:
            text = guideline["text"].lower()
            added = False
            
            # Assign to categories
            for category, keywords in self.categories.items():
                if any(keyword in text for keyword in keywords):
                    categorized[category].append(guideline)
                    added = True
            
            # Add to general category if not assigned
            if not added:
                categorized["general"].append(guideline)
        
        return categorized
    
    def retrieve_relevant_guidelines(self, context: str, file_type: str = None, top_k: int = 5) -> List[Dict[str, str]]:
        """Retrieve guidelines most relevant to the given context."""
        if not self.guidelines:
            return []
        
        # Filter by file type if provided
        file_specific_guidelines = []
        if file_type:
            file_type = file_type.lower()
            for guideline in self.guidelines:
                text = guideline["text"].lower()
                if file_type in text or (file_type == "py" and "python" in text) or (file_type in ["js", "jsx", "ts", "tsx"] and "javascript" in text):
                    file_specific_guidelines.append(guideline)
        
        if self.model and self.embeddings is not None:
            # Use semantic search with embeddings if available
            query_embedding = self.model.encode(context)
            
            # Calculate similarity
            if file_specific_guidelines:
                texts = [g["text"] for g in file_specific_guidelines]
                target_embeddings = self.model.encode(texts)
                similarities = cosine_similarity([query_embedding], target_embeddings)[0]
                
                # Get top k matches
                indices = np.argsort(-similarities)[:top_k]
                return [file_specific_guidelines[i] for i in indices]
            else:
                # Use all guidelines if no file-specific ones
                similarities = cosine_similarity([query_embedding], self.embeddings)[0]
                indices = np.argsort(-similarities)[:top_k]
                return [self.guidelines[i] for i in indices]
        else:
            # Fall back to keyword matching
            context_keywords = set(re.findall(r'\b\w+\b', context.lower()))
            
            # Score each guideline by keyword overlap
            scored_guidelines = []
            search_pool = file_specific_guidelines if file_specific_guidelines else self.guidelines
            
            for guideline in search_pool:
                guideline_keywords = set(re.findall(r'\b\w+\b', guideline["text"].lower()))
                score = len(context_keywords.intersection(guideline_keywords))
                scored_guidelines.append((score, guideline))
            
            # Sort by score and take top k
            scored_guidelines.sort(reverse=True)
            return [g for _, g in scored_guidelines[:top_k]]
    
    def analyze_patch(self, file_path: str, patch: str) -> List[Dict[str, Any]]:
        """Analyze a patch against relevant guidelines."""
        violations = []
        
        if not patch:
            return violations
        
        # Get file extension
        file_ext = file_path.split('.')[-1] if '.' in file_path else ''
        
        # Extract code context from patch
        added_lines = [line[1:] for line in patch.split('\n') if line.startswith('+') and not line.startswith('+++')]
        added_code = '\n'.join(added_lines)
        
        # Get relevant guidelines for this file type and code context
        relevant_guidelines = self.retrieve_relevant_guidelines(
            context=f"File type: {file_ext}\nCode:\n{added_code}", 
            file_type=file_ext
        )
        
        # Check code against relevant guidelines
        for guideline in relevant_guidelines:
            rule_text = guideline["text"].lower()
            
            # Check indentation rules
            if any(keyword in rule_text for keyword in self.categories["indentation"]):
                if "use spaces" in rule_text and "\t" in patch:
                    violations.append({
                        "file": file_path,
                        "rule": "Indentation",
                        "message": f"Uses tabs but guidelines specify spaces. Guideline: '{guideline['text']}'",
                        "guideline": guideline["text"]
                    })
                elif "use tabs" in rule_text and "    " in patch:
                    violations.append({
                        "file": file_path,
                        "rule": "Indentation",
                        "message": f"Uses spaces but guidelines specify tabs. Guideline: '{guideline['text']}'",
                        "guideline": guideline["text"]
                    })
            
            # Check line ending rules
            if any(keyword in rule_text for keyword in ["semicolon", "line ending"]):
                if "no semicolon" in rule_text or "avoid semicolon" in rule_text:
                    if re.search(r';\s*$', patch, re.MULTILINE):
                        violations.append({
                            "file": file_path,
                            "rule": "Line Endings",
                            "message": f"Uses semicolons but guidelines recommend against them. Guideline: '{guideline['text']}'",
                            "guideline": guideline["text"]
                        })
                elif "require semicolon" in rule_text or "use semicolon" in rule_text:
                    added_statements = re.findall(r'\+.*?[a-zA-Z0-9_)\]"\']\s*$', patch, re.MULTILINE)
                    if added_statements and not all(';' in stmt for stmt in added_statements):
                        violations.append({
                            "file": file_path,
                            "rule": "Line Endings",
                            "message": f"Missing semicolons but guidelines require them. Guideline: '{guideline['text']}'",
                            "guideline": guideline["text"]
                        })
            
            # Check naming conventions
            if any(keyword in rule_text for keyword in self.categories["naming"]):
                if "camelcase" in rule_text or "camel case" in rule_text:
                    # This rule specifies camelCase, so check if we're using snake_case instead
                    snake_case_vars = re.findall(r'\b[a-z]+(?:_[a-z0-9]+)+\b', patch)
                    if snake_case_vars and file_ext not in ["py"]:  # Python typically uses snake_case
                        violations.append({
                            "file": file_path,
                            "rule": "Naming Convention",
                            "message": f"Found snake_case variables but guidelines specify camelCase. Guideline: '{guideline['text']}'",
                            "guideline": guideline["text"]
                        })
                elif "snake_case" in rule_text or "snake case" in rule_text:
                    # This rule specifies snake_case, so check if we're using camelCase instead
                    camel_case_vars = re.findall(r'\b[a-z]+[A-Z][a-zA-Z0-9]*\b', patch)
                    if camel_case_vars and file_ext in ["py"]:  # Python typically uses snake_case
                        violations.append({
                            "file": file_path,
                            "rule": "Naming Convention",
                            "message": f"Found camelCase variables: {', '.join(camel_case_vars)}. Guidelines specify snake_case. Guideline: '{guideline['text']}'",
                            "guideline": guideline["text"]
                        })
        
        return violations, relevant_guidelines

async def fetch_jira_guidelines(project_key: str, page_id: str) -> Dict[str, Any]:
    """Fetch coding guidelines from a JIRA Confluence page."""
    # If we have a direct URL, use it instead of constructing from JIRA credentials
    if GUIDELINES_DIRECT_URL:
        print(f"Using direct URL to guidelines: {GUIDELINES_DIRECT_URL}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GUIDELINES_DIRECT_URL) as response:
                    if response.status != 200:
                        print(f"Failed to fetch guidelines from direct URL: HTTP {response.status}")
                        sys.exit(1)
                    
                    html_content = await response.text()
                    
                    return {
                        "title": "Coding Guidelines",
                        "content": html_content,
                        "url": GUIDELINES_DIRECT_URL,
                        "project_key": project_key
                    }
        except Exception as e:
            print(f"Error fetching guidelines from direct URL: {str(e)}")
            sys.exit(1)
    
    # Use JIRA API if no direct URL provided
    if not JIRA_API_TOKEN or not JIRA_EMAIL or not JIRA_URL:
        print("Error: JIRA credentials not configured and no direct URL provided.")
        sys.exit(1)

    try:
        api_url = f"{JIRA_URL}/wiki/rest/api/content/{page_id}?expand=body.storage"
        auth = aiohttp.BasicAuth(login=JIRA_EMAIL, password=JIRA_API_TOKEN)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, auth=auth) as response:
                if response.status != 200:
                    print(f"Failed to fetch JIRA page: HTTP {response.status}")
                    sys.exit(1)
                
                data = await response.json()
                
                return {
                    "title": data.get("title", "Coding Guidelines"),
                    "content": data.get("body", {}).get("storage", {}).get("value", ""),
                    "url": f"{JIRA_URL}/wiki/spaces/{project_key}/pages/{page_id}",
                    "project_key": project_key
                }
    except Exception as e:
        print(f"Error fetching JIRA guidelines: {str(e)}")
        sys.exit(1)

async def fetch_github_pr() -> Dict[str, Any]:
    """Fetch the GitHub pull request data from the event payload."""
    if not GITHUB_TOKEN:
        print("Error: GitHub token not configured.")
        sys.exit(1)

    try:
        with open(GITHUB_EVENT_PATH, 'r') as f:
            event_data = json.load(f)
        
        pr_number = event_data.get("pull_request", {}).get("number")
        if not pr_number:
            print("Error: Could not determine PR number from event.")
            sys.exit(1)
        
        repo = GITHUB_REPOSITORY
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        pr_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}"
        
        async with aiohttp.ClientSession() as session:
            # Get PR details
            async with session.get(pr_url, headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch PR: HTTP {response.status}")
                    sys.exit(1)
                pr_data = await response.json()
                
            # Get PR files
            async with session.get(f"{pr_url}/files", headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch PR files: HTTP {response.status}")
                    sys.exit(1)
                files_data = await response.json()
            
            # Get PR diff
            diff_headers = headers.copy()
            diff_headers["Accept"] = "application/vnd.github.v3.diff"
            
            async with session.get(pr_url, headers=diff_headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch PR diff: HTTP {response.status}")
                    sys.exit(1)
                diff_content = await response.text()
            
            return {
                "pr_number": pr_number,
                "title": pr_data.get("title", ""),
                "description": pr_data.get("body", ""),
                "files": files_data,
                "diff": diff_content,
                "repo": repo,
                "url": pr_data.get("html_url", "")
            }
    except Exception as e:
        print(f"Error fetching GitHub PR: {str(e)}")
        sys.exit(1)

def extract_guidelines_from_html(html_content: str) -> List[Dict[str, str]]:
    """Extract guidelines from HTML content."""
    parser = GuidelinesHTMLParser()
    parser.feed(html_content)
    
    extracted_rules = []
    for rule_type, rule_text in parser.rules:
        # Common coding guideline keywords
        keywords = [
            'should', 'must', 'avoid', 'use', 'don\'t', 'require', 'follow',
            'standard', 'convention', 'pattern', 'practice', 'rule', 'guideline',
            'naming', 'format', 'indent', 'comment', 'documentation', 'test'
        ]
        
        # Only include texts that are likely to be guidelines
        if any(keyword in rule_text.lower() for keyword in keywords):
            extracted_rules.append({
                "type": rule_type,
                "text": rule_text,
                "id": str(uuid.uuid4())  # Add unique ID for each guideline
            })
    
    return extracted_rules

async def analyze_code_against_guidelines(guidelines: Dict[str, Any], pr_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze code changes against JIRA coding guidelines with RAG approach."""
    violations = []
    custom_recommendations = []
    summary = f"Code Review for PR #{pr_data['pr_number']}: {pr_data['title']}"
    
    files = pr_data.get("files", [])
    guidelines_content = guidelines.get("content", "")
    
    # Extract guidelines from HTML content
    extracted_guidelines = extract_guidelines_from_html(guidelines_content)
    print(f"Extracted {len(extracted_guidelines)} potential guidelines from JIRA")
    
    # Initialize RAG engine
    rag = GuidelinesRAG(extracted_guidelines)
    categorized_guidelines = rag.categorize_guidelines()
    print(f"Categorized guidelines into {len(categorized_guidelines)} categories")
    
    # 1. Check for file length
    for file_info in files:
        filename = file_info.get("filename", "")
        changes = file_info.get("changes", 0)
        
        if changes > 300:
            violations.append({
                "file": filename,
                "rule": "File Change Size",
                "message": f"File has {changes} changes, which exceeds the recommended limit of 300"
            })
    
    # 2. Use RAG to analyze each file
    all_relevant_guidelines = []
    for file_info in files:
        filename = file_info.get("filename", "")
        patch = file_info.get("patch", "")
        
        if not patch:
            continue
        
        # Use RAG to analyze this file's patch
        file_violations, relevant_guidelines = rag.analyze_patch(filename, patch)
        violations.extend(file_violations)
        all_relevant_guidelines.extend(relevant_guidelines)
        
        # Add specific checks for different file types
        file_ext = filename.split('.')[-1] if '.' in filename else ''
        
        if file_ext == 'py':
            # Python-specific checks
            added_lines = [line[1:] for line in patch.split('\n') if line.startswith('+') and not line.startswith('+++')]
            
            # Check for long lines
            long_lines = [line for line in added_lines if len(line) > 120]
            if long_lines:
                violations.append({
                    "file": filename,
                    "rule": "Line Length",
                    "message": f"Found {len(long_lines)} lines exceeding 120 characters. Consider breaking them up for better readability."
                })
        
        elif file_ext in ['js', 'jsx', 'ts', 'tsx']:
            # JavaScript/TypeScript specific checks
            if re.search(r'console\.log', patch):
                violations.append({
                    "file": filename,
                    "rule": "Console Logging",
                    "message": "Found console.log statements. Remove debugging statements before merging."
                })
        
        # Check for TODO comments in all files
        if re.search(r'(#|//|/\*|\*)\s*TODO', patch, re.IGNORECASE):
            violations.append({
                "file": filename,
                "rule": "TODO Comments",
                "message": "Found TODO comments in the code. Consider resolving them before merging."
            })
    
    # Collect recommendations based on relevant guidelines
    for guideline in all_relevant_guidelines:
        if guideline["text"] not in custom_recommendations:
            custom_recommendations.append(guideline["text"])
    
    # Combine standard recommendations with custom ones from guidelines
    recommendations = [
        "Ensure your code includes appropriate documentation.",
        "Add unit tests for new functionality.",
        "Make sure variable names are descriptive and follow language conventions."
    ]
    
    # Add unique recommendations from guidelines
    for rec in custom_recommendations:
        if rec not in recommendations:
            recommendations.append(rec)
    
    return {
        "summary": summary,
        "violations": violations,
        "recommendations": recommendations,
        "extracted_guidelines": extracted_guidelines,  # Include for reference in the review
        "categorized_guidelines": categorized_guidelines
    }

async def post_review_comments(repo: str, pr_number: int, review_data: Dict[str, Any]) -> None:
    """Post code review comments to GitHub PR."""
    if not GITHUB_TOKEN:
        print("Error: GitHub token not configured.")
        sys.exit(1)

    try:
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        violations = review_data.get("violations", [])
        recommendations = review_data.get("recommendations", [])
        extracted_guidelines = review_data.get("extracted_guidelines", [])
        
        review_body = f"# JIRA Coding Guidelines Review\n\n"
        review_body += f"## Summary\n{review_data.get('summary', '')}\n\n"
        
        if violations:
            review_body += "## Violations\n\n"
            for violation in violations:
                review_body += f"- **{violation.get('file')}**: {violation.get('rule')} - {violation.get('message')}\n"
            review_body += "\n"
        
        if recommendations:
            review_body += "## Recommendations\n\n"
            for recommendation in recommendations:
                review_body += f"- {recommendation}\n"
        
        # Add reference to guidelines source
        review_body += f"\n\nReview based on guidelines from: {guidelines['url']}\n"
        
        # Prepare line-specific comments
        comments = []
        for violation in violations:
            if "position" in violation:
                comments.append({
                    "path": violation.get("file"),
                    "position": violation.get("position"),
                    "body": f"**{violation.get('rule')}**: {violation.get('message')}"
                })
        
        github_review_data = {
            "body": review_body,
            "event": "COMMENT"  # Other options: APPROVE, REQUEST_CHANGES
        }
        
        if comments:
            github_review_data["comments"] = comments
        
        review_url = f"{GITHUB_API_URL}/repos/{repo}/pulls/{pr_number}/reviews"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(review_url, headers=headers, json=github_review_data) as response:
                if response.status not in (200, 201):
                    print(f"Failed to post review: HTTP {response.status}")
                    print(await response.text())
                    sys.exit(1)
                
                result = await response.json()
                print(f"Successfully posted review: {result.get('html_url')}")
    
    except Exception as e:
        print(f"Error posting GitHub review: {str(e)}")
        sys.exit(1)

async def setup_dependencies():
    """Set up dependencies if not already installed."""
    if not EMBEDDING_AVAILABLE:
        try:
            import subprocess
            print("Installing required dependencies for RAG...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers", "scikit-learn", "numpy"])
            print("Dependencies installed successfully")
            global EMBEDDING_AVAILABLE
            EMBEDDING_AVAILABLE = True
        except Exception as e:
            print(f"Failed to install dependencies: {e}")

async def main():
    # Attempt to install dependencies
    await setup_dependencies()
    
    # Validate required environment variables
    if not PROJECT_KEY and not GUIDELINES_DIRECT_URL:
        print("Error: PROJECT_KEY must be set unless using GUIDELINES_DIRECT_URL")
        if GUIDELINES_DIRECT_URL:
            PROJECT_KEY = "UNKNOWN"  # Set a default if we're using direct URL
        else:
            sys.exit(1)
    
    if not GUIDELINES_PAGE_ID and not GUIDELINES_DIRECT_URL:
        print("Error: GUIDELINES_PAGE_ID must be set unless using GUIDELINES_DIRECT_URL")
        sys.exit(1)
    
    print("Fetching coding guidelines...")
    global guidelines
    guidelines = await fetch_jira_guidelines(PROJECT_KEY, GUIDELINES_PAGE_ID)
    print(f"Successfully fetched guidelines: {guidelines['title']}")
    
    print("Fetching GitHub PR data...")
    pr_data = await fetch_github_pr()
    print(f"Successfully fetched PR #{pr_data['pr_number']}: {pr_data['title']}")
    
    print("Analyzing code against guidelines using RAG...")
    review_data = await analyze_code_against_guidelines(guidelines, pr_data)
    
    print("Posting review comments...")
    await post_review_comments(pr_data['repo'], pr_data['pr_number'], review_data)
    
    print("Code review completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 