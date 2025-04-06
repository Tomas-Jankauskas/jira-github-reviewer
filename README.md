# Code Review GitHub Action with RAG

This repository contains a GitHub Action for automated code reviews based on JIRA guidelines using RAG (Retrieval-Augmented Generation).

## Features

- Automatically analyzes code when a PR is labeled with "needs-review"
- Uses RAG to identify relevant coding guidelines for the specific code changes
- Provides contextualized feedback with violations and recommendations
- Supports direct URL access to guidelines (no JIRA credentials required)

## Setup Instructions

1. Fork this repository or create a new one with these files

2. Configure the following secrets in your GitHub repository:
   - `GITHUB_TOKEN` (automatically provided by GitHub Actions)
   - `JIRA_API_TOKEN` (if using JIRA, otherwise skip)
   - `JIRA_EMAIL` (if using JIRA, otherwise skip)
   - `JIRA_URL` (if using JIRA, otherwise skip)

3. Configure the following variables in your GitHub repository:
   - `JIRA_PROJECT_KEY` (if using JIRA, otherwise skip)
   - `JIRA_GUIDELINES_PAGE_ID` (if using JIRA, otherwise skip)
   - `GUIDELINES_DIRECT_URL` (if using direct URL instead of JIRA)

4. Create a "needs-review" label in your repository

5. Apply the "needs-review" label to any PR you want to be automatically reviewed

## Sample Files

This repository includes sample files with deliberate coding issues to test the review functionality:

- `sample.py`: Python file with various coding issues
- `sample.vue`: Vue component with various frontend best practice violations

## Testing Locally

To test this action locally:

1. Clone the repository
2. Create a PR with some code changes
3. Set the required environment variables
4. Run the review script:

```bash
python .github/scripts/review_pr.py
```
