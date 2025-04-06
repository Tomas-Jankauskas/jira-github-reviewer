# JIRA GitHub Code Review - GitHub Action Setup

This document explains how to set up the automated code review GitHub Action that integrates with JIRA to check code against your team's coding guidelines.

## How It Works

1. When a pull request gets labeled with "needs-review", the workflow automatically:
   - Fetches coding guidelines from your specified JIRA Confluence page
   - Retrieves the PR code and diff information
   - Analyzes the code against the guidelines
   - Posts a review comment to the PR with findings and recommendations

## Setup Steps

### 1. Configure GitHub Secrets

In your repository settings, add the following secrets:

- `JIRA_API_TOKEN`: Your JIRA API token for authentication
- `JIRA_EMAIL`: Email address associated with your JIRA account
- `JIRA_URL`: Base URL of your JIRA instance (e.g., "https://your-company.atlassian.net")
- `GITHUB_TOKEN`: This is automatically provided by GitHub Actions, no need to set it

### 2. Configure GitHub Variables

In your repository settings, add the following variables:

- `JIRA_PROJECT_KEY`: The project key in JIRA (e.g., "DEV", "PROJ")
- `JIRA_GUIDELINES_PAGE_ID`: The ID of the Confluence page containing your coding guidelines

### 3. Create a "needs-review" Label

In your repository's Issues/PR section, create a label named "needs-review" that will trigger the automated code review.

## Usage

1. Create a pull request as usual
2. When you want an automated code review, add the "needs-review" label to the PR
3. The GitHub Action will run and post a review comment with its findings

## Customizing the Code Review Logic

The code review logic in `.github/scripts/review_pr.py` can be customized to:

1. Extract specific rules from your JIRA guidelines 
2. Add custom code analysis rules
3. Change the review comment format
4. Add language-specific checks

To extract specific rules from the JIRA guidelines, you may need to:
- Parse the HTML content from the Confluence page
- Use NLP techniques to identify rules and requirements
- Create specific checks for each identified rule

## Example Workflow

1. Developer submits a PR
2. Reviewer or developer adds the "needs-review" label
3. GitHub Action runs an automated review against JIRA guidelines
4. Reviewer examines both the automated review and the code manually
5. After addressing any issues, the PR can be approved

## Troubleshooting

If the GitHub Action fails:

1. Check the Action logs for error messages
2. Verify your secrets and variables are correctly set
3. Ensure the JIRA page ID is correct and accessible
4. Verify that the GitHub token has sufficient permissions 