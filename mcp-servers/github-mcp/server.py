#!/usr/bin/env python3
"""
GitHub MCP Server
Provides tools for GitHub repository and project management
"""

import os
from typing import Any, Dict, List, Optional
import base64

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from github import Github, GithubException
import uvicorn


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


app = FastAPI(title="GitHub MCP Server")

# Global GitHub client
github_client: Optional[Github] = None
github_org: Optional[str] = None


def init_github():
    """Initialize GitHub client"""
    global github_client, github_org
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")

    github_client = Github(token)
    github_org = os.getenv('GITHUB_ORG')  # Optional: organization name
    print(f"GitHub client initialized. Organization: {github_org or 'Personal'}")


@app.on_event("startup")
async def startup():
    init_github()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "github-mcp"}


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "create_repository",
                "description": "Create a new GitHub repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Repository name"},
                        "description": {"type": "string", "description": "Repository description"},
                        "private": {"type": "boolean", "default": True, "description": "Make repository private"},
                        "auto_init": {"type": "boolean", "default": True, "description": "Initialize with README"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "create_file",
                "description": "Create or update a file in repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"},
                        "file_path": {"type": "string", "description": "File path in repository"},
                        "content": {"type": "string", "description": "File content"},
                        "commit_message": {"type": "string", "description": "Commit message"},
                        "branch": {"type": "string", "default": "main", "description": "Branch name"}
                    },
                    "required": ["repo_name", "file_path", "content", "commit_message"]
                }
            },
            {
                "name": "create_project_structure",
                "description": "Create initial project structure with multiple files",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"},
                        "project_type": {"type": "string", "description": "Project type (e.g., python, javascript, react, fullstack)"},
                        "files": {"type": "object", "description": "Dictionary of file paths and their contents"}
                    },
                    "required": ["repo_name", "project_type"]
                }
            },
            {
                "name": "create_issue",
                "description": "Create a GitHub issue",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body/description"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Issue labels"},
                        "assignees": {"type": "array", "items": {"type": "string"}, "description": "Assignees"}
                    },
                    "required": ["repo_name", "title"]
                }
            },
            {
                "name": "create_issues_from_tasks",
                "description": "Create GitHub issues from project tasks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"},
                        "tasks": {"type": "array", "description": "Array of task objects"}
                    },
                    "required": ["repo_name", "tasks"]
                }
            },
            {
                "name": "create_labels",
                "description": "Create standard labels for project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"},
                        "label_set": {"type": "string", "enum": ["basic", "extended", "priority"], "default": "basic"}
                    },
                    "required": ["repo_name"]
                }
            },
            {
                "name": "get_repository_info",
                "description": "Get repository information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string", "description": "Repository name"}
                    },
                    "required": ["repo_name"]
                }
            }
        ]
    }


@app.post("/call_tool", response_model=ToolResponse)
async def call_tool(tool_call: ToolCall):
    """Execute an MCP tool"""
    try:
        if tool_call.name == "create_repository":
            result = await create_repository(tool_call.arguments)
        elif tool_call.name == "create_file":
            result = await create_file(tool_call.arguments)
        elif tool_call.name == "create_project_structure":
            result = await create_project_structure(tool_call.arguments)
        elif tool_call.name == "create_issue":
            result = await create_issue(tool_call.arguments)
        elif tool_call.name == "create_issues_from_tasks":
            result = await create_issues_from_tasks(tool_call.arguments)
        elif tool_call.name == "create_labels":
            result = await create_labels(tool_call.arguments)
        elif tool_call.name == "get_repository_info":
            result = await get_repository_info(tool_call.arguments)
        else:
            return ToolResponse(success=False, error=f"Unknown tool: {tool_call.name}")

        return ToolResponse(success=True, data=result)
    except Exception as e:
        return ToolResponse(success=False, error=str(e))


def get_repo(repo_name: str):
    """Get repository object"""
    try:
        if github_org:
            full_name = f"{github_org}/{repo_name}"
        else:
            user = github_client.get_user()
            full_name = f"{user.login}/{repo_name}"

        return github_client.get_repo(full_name)
    except GithubException as e:
        raise HTTPException(status_code=404, detail=f"Repository not found: {e.data.get('message', str(e))}")


# Tool implementations

async def create_repository(args: Dict) -> Dict:
    """Create a new GitHub repository"""
    try:
        if github_org:
            org = github_client.get_organization(github_org)
            repo = org.create_repo(
                name=args['name'],
                description=args.get('description', ''),
                private=args.get('private', True),
                auto_init=args.get('auto_init', True)
            )
        else:
            user = github_client.get_user()
            repo = user.create_repo(
                name=args['name'],
                description=args.get('description', ''),
                private=args.get('private', True),
                auto_init=args.get('auto_init', True)
            )

        return {
            "repo_name": repo.name,
            "repo_url": repo.html_url,
            "clone_url": repo.clone_url,
            "ssh_url": repo.ssh_url,
            "owner": repo.owner.login
        }
    except GithubException as e:
        raise HTTPException(status_code=400, detail=f"Failed to create repository: {e.data.get('message', str(e))}")


async def create_file(args: Dict) -> Dict:
    """Create or update a file in repository"""
    repo = get_repo(args['repo_name'])
    branch = args.get('branch', 'main')

    try:
        # Try to get existing file
        existing_file = repo.get_contents(args['file_path'], ref=branch)
        # Update existing file
        repo.update_file(
            path=args['file_path'],
            message=args['commit_message'],
            content=args['content'],
            sha=existing_file.sha,
            branch=branch
        )
        action = "updated"
    except GithubException:
        # Create new file
        repo.create_file(
            path=args['file_path'],
            message=args['commit_message'],
            content=args['content'],
            branch=branch
        )
        action = "created"

    return {
        "action": action,
        "file_path": args['file_path'],
        "repo": repo.name
    }


async def create_project_structure(args: Dict) -> Dict:
    """Create initial project structure"""
    repo = get_repo(args['repo_name'])
    project_type = args.get('project_type', 'generic')
    custom_files = args.get('files', {})

    # Default project structures
    structures = {
        "python": {
            ".gitignore": """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
""",
            "requirements.txt": "# Add your dependencies here\n",
            "README.md": f"# {repo.name}\n\nA Python project\n",
            "src/__init__.py": "",
            "tests/__init__.py": ""
        },
        "javascript": {
            ".gitignore": """node_modules/
.env
dist/
build/
""",
            "package.json": """{
  "name": \"""" + repo.name + """\",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "test": "echo \\"Error: no test specified\\" && exit 1"
  }
}
""",
            "README.md": f"# {repo.name}\n\nA JavaScript project\n",
            "src/index.js": "// Entry point\n"
        },
        "react": {
            ".gitignore": """node_modules/
.env
build/
.DS_Store
""",
            "README.md": f"# {repo.name}\n\nA React application\n",
            "public/index.html": """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>React App</title>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
""",
            "src/App.js": """import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Welcome to React</h1>
    </div>
  );
}

export default App;
""",
            "src/index.js": """import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';

ReactDOM.render(<App />, document.getElementById('root'));
"""
        }
    }

    # Merge custom files with defaults
    files_to_create = structures.get(project_type, {})
    files_to_create.update(custom_files)

    created_files = []
    for file_path, content in files_to_create.items():
        try:
            repo.create_file(
                path=file_path,
                message=f"Initialize project: add {file_path}",
                content=content
            )
            created_files.append(file_path)
        except GithubException as e:
            # Skip if file already exists
            if e.status != 422:
                raise

    return {
        "repo": repo.name,
        "project_type": project_type,
        "created_files": created_files
    }


async def create_issue(args: Dict) -> Dict:
    """Create a GitHub issue"""
    repo = get_repo(args['repo_name'])

    issue = repo.create_issue(
        title=args['title'],
        body=args.get('body', ''),
        labels=args.get('labels', []),
        assignees=args.get('assignees', [])
    )

    return {
        "issue_number": issue.number,
        "issue_url": issue.html_url,
        "title": issue.title
    }


async def create_issues_from_tasks(args: Dict) -> Dict:
    """Create GitHub issues from project tasks"""
    repo = get_repo(args['repo_name'])
    tasks = args.get('tasks', [])

    created_issues = []

    for task in tasks:
        # Format issue body
        body = f"{task.get('description', '')}\n\n"

        if task.get('task_type'):
            body += f"**Type:** {task['task_type']}\n"

        if task.get('estimated_hours'):
            body += f"**Estimated Hours:** {task['estimated_hours']}\n"

        if task.get('story_title'):
            body += f"**Story:** {task['story_title']}\n"

        if task.get('epic_title'):
            body += f"**Epic:** {task['epic_title']}\n"

        # Determine labels based on task type
        labels = []
        task_type = task.get('task_type', 'feature')
        labels.append(task_type)

        # Create issue
        issue = repo.create_issue(
            title=task['title'],
            body=body,
            labels=labels
        )

        created_issues.append({
            "task_id": task.get('id'),
            "issue_number": issue.number,
            "issue_url": issue.html_url,
            "title": issue.title
        })

    return {
        "repo": repo.name,
        "created_count": len(created_issues),
        "issues": created_issues
    }


async def create_labels(args: Dict) -> Dict:
    """Create standard labels for project"""
    repo = get_repo(args['repo_name'])
    label_set = args.get('label_set', 'basic')

    label_definitions = {
        "basic": [
            {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
            {"name": "feature", "color": "a2eeef", "description": "New feature or request"},
            {"name": "documentation", "color": "0075ca", "description": "Improvements or additions to documentation"},
            {"name": "enhancement", "color": "84b6eb", "description": "Enhancement to existing feature"}
        ],
        "extended": [
            {"name": "bug", "color": "d73a4a", "description": "Something isn't working"},
            {"name": "feature", "color": "a2eeef", "description": "New feature or request"},
            {"name": "documentation", "color": "0075ca", "description": "Improvements or additions to documentation"},
            {"name": "enhancement", "color": "84b6eb", "description": "Enhancement to existing feature"},
            {"name": "setup", "color": "fef2c0", "description": "Setup and configuration tasks"},
            {"name": "test", "color": "c5def5", "description": "Testing related tasks"},
            {"name": "refactor", "color": "fbca04", "description": "Code refactoring"},
            {"name": "deployment", "color": "0e8a16", "description": "Deployment related tasks"}
        ],
        "priority": [
            {"name": "priority: high", "color": "b60205", "description": "High priority"},
            {"name": "priority: medium", "color": "fbca04", "description": "Medium priority"},
            {"name": "priority: low", "color": "0e8a16", "description": "Low priority"}
        ]
    }

    labels = label_definitions.get(label_set, label_definitions['basic'])
    created_labels = []

    for label_def in labels:
        try:
            label = repo.create_label(
                name=label_def['name'],
                color=label_def['color'],
                description=label_def.get('description', '')
            )
            created_labels.append(label.name)
        except GithubException as e:
            # Skip if label already exists
            if e.status != 422:
                raise

    return {
        "repo": repo.name,
        "label_set": label_set,
        "created_labels": created_labels
    }


async def get_repository_info(args: Dict) -> Dict:
    """Get repository information"""
    repo = get_repo(args['repo_name'])

    return {
        "name": repo.name,
        "full_name": repo.full_name,
        "description": repo.description,
        "url": repo.html_url,
        "clone_url": repo.clone_url,
        "ssh_url": repo.ssh_url,
        "default_branch": repo.default_branch,
        "private": repo.private,
        "created_at": repo.created_at.isoformat(),
        "updated_at": repo.updated_at.isoformat(),
        "language": repo.language,
        "stars": repo.stargazers_count,
        "forks": repo.forks_count,
        "open_issues": repo.open_issues_count
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
