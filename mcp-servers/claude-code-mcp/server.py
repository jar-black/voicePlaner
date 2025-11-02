#!/usr/bin/env python3
"""
Claude Code MCP Server Wrapper
Provides tools for managing Claude Code projects and task execution
"""

import os
import subprocess
import json
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic
import uvicorn


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


app = FastAPI(title="Claude Code MCP Server")

# Global configuration
WORKSPACE_DIR = Path("/workspace")
claude_client: Optional[anthropic.Anthropic] = None


def init_claude():
    """Initialize Claude client"""
    global claude_client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")

    claude_client = anthropic.Anthropic(api_key=api_key)
    print("Claude client initialized")


@app.on_event("startup")
async def startup():
    init_claude()
    WORKSPACE_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "claude-code-mcp"}


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "init_project",
                "description": "Initialize a Claude Code project from GitHub repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "repo_url": {"type": "string", "description": "GitHub repository URL"},
                        "project_name": {"type": "string", "description": "Project name"}
                    },
                    "required": ["project_id", "repo_url", "project_name"]
                }
            },
            {
                "name": "execute_task",
                "description": "Execute a task using Claude Code",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "task": {"type": "object", "description": "Task details"},
                        "context": {"type": "string", "description": "Additional context for the task"}
                    },
                    "required": ["project_id", "task"]
                }
            },
            {
                "name": "get_project_status",
                "description": "Get status of a Claude Code project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "run_command",
                "description": "Run a command in the project workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "command": {"type": "string", "description": "Command to run"}
                    },
                    "required": ["project_id", "command"]
                }
            },
            {
                "name": "create_branch",
                "description": "Create a new git branch for task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "branch_name": {"type": "string", "description": "Branch name"},
                        "base_branch": {"type": "string", "default": "main", "description": "Base branch"}
                    },
                    "required": ["project_id", "branch_name"]
                }
            },
            {
                "name": "commit_changes",
                "description": "Commit changes in project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "message": {"type": "string", "description": "Commit message"},
                        "push": {"type": "boolean", "default": False, "description": "Push to remote"}
                    },
                    "required": ["project_id", "message"]
                }
            }
        ]
    }


@app.post("/call_tool", response_model=ToolResponse)
async def call_tool(tool_call: ToolCall):
    """Execute an MCP tool"""
    try:
        if tool_call.name == "init_project":
            result = await init_project(tool_call.arguments)
        elif tool_call.name == "execute_task":
            result = await execute_task(tool_call.arguments)
        elif tool_call.name == "get_project_status":
            result = await get_project_status(tool_call.arguments)
        elif tool_call.name == "run_command":
            result = await run_command(tool_call.arguments)
        elif tool_call.name == "create_branch":
            result = await create_branch(tool_call.arguments)
        elif tool_call.name == "commit_changes":
            result = await commit_changes(tool_call.arguments)
        else:
            return ToolResponse(success=False, error=f"Unknown tool: {tool_call.name}")

        return ToolResponse(success=True, data=result)
    except Exception as e:
        return ToolResponse(success=False, error=str(e))


def get_project_path(project_id: str) -> Path:
    """Get project workspace path"""
    return WORKSPACE_DIR / project_id


def run_git_command(project_path: Path, command: List[str]) -> Dict:
    """Run a git command in project directory"""
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=project_path,
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "error": str(e)
        }


# Tool implementations

async def init_project(args: Dict) -> Dict:
    """Initialize a Claude Code project"""
    project_id = args['project_id']
    repo_url = args['repo_url']
    project_name = args['project_name']

    project_path = get_project_path(project_id)

    if project_path.exists():
        return {
            "status": "already_exists",
            "project_path": str(project_path),
            "message": "Project already initialized"
        }

    # Clone repository
    try:
        result = subprocess.run(
            ["git", "clone", repo_url, str(project_path)],
            capture_output=True,
            text=True,
            check=True
        )

        # Create project metadata
        metadata = {
            "project_id": project_id,
            "project_name": project_name,
            "repo_url": repo_url,
            "initialized_at": None  # Would use timestamp here
        }

        metadata_file = project_path / ".claude-project.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        return {
            "status": "initialized",
            "project_path": str(project_path),
            "project_id": project_id,
            "message": "Project successfully initialized"
        }
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clone repository: {e.stderr}"
        )


async def execute_task(args: Dict) -> Dict:
    """Execute a task using Claude Code"""
    project_id = args['project_id']
    task = args['task']
    context = args.get('context', '')

    project_path = get_project_path(project_id)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not initialized")

    # Build task prompt for Claude
    task_prompt = f"""Please help implement the following task:

**Task:** {task['title']}

**Description:** {task.get('description', '')}

**Type:** {task.get('task_type', 'feature')}

"""

    if task.get('technical_details'):
        task_prompt += f"**Technical Details:**\n{json.dumps(task['technical_details'], indent=2)}\n\n"

    if context:
        task_prompt += f"**Additional Context:**\n{context}\n\n"

    task_prompt += """Please:
1. Analyze the codebase structure
2. Implement the required changes
3. Add appropriate tests if applicable
4. Ensure code quality and best practices
5. Provide a summary of changes made
"""

    # For now, we'll return instructions for manual execution
    # In production, this would integrate with Claude Code CLI or API
    return {
        "status": "prepared",
        "project_path": str(project_path),
        "task_id": task.get('id'),
        "task_title": task['title'],
        "prompt": task_prompt,
        "message": "Task prepared for execution. Use Claude Code CLI to execute.",
        "next_steps": [
            f"cd {project_path}",
            "Open with Claude Code",
            "Execute the task prompt"
        ]
    }


async def get_project_status(args: Dict) -> Dict:
    """Get project status"""
    project_id = args['project_id']
    project_path = get_project_path(project_id)

    if not project_path.exists():
        return {
            "status": "not_initialized",
            "project_id": project_id
        }

    # Get git status
    git_status = run_git_command(project_path, ["status", "--porcelain"])

    # Get current branch
    branch_result = run_git_command(project_path, ["branch", "--show-current"])
    current_branch = branch_result.get('stdout', '').strip()

    # Count files
    files = list(project_path.rglob("*"))
    file_count = len([f for f in files if f.is_file()])

    return {
        "status": "initialized",
        "project_id": project_id,
        "project_path": str(project_path),
        "current_branch": current_branch,
        "file_count": file_count,
        "has_changes": bool(git_status.get('stdout')),
        "git_status": git_status.get('stdout', '')
    }


async def run_command(args: Dict) -> Dict:
    """Run a command in project workspace"""
    project_id = args['project_id']
    command = args['command']
    project_path = get_project_path(project_id)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not initialized")

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command execution timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")


async def create_branch(args: Dict) -> Dict:
    """Create a new git branch"""
    project_id = args['project_id']
    branch_name = args['branch_name']
    base_branch = args.get('base_branch', 'main')

    project_path = get_project_path(project_id)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not initialized")

    # Checkout base branch and pull
    run_git_command(project_path, ["checkout", base_branch])
    run_git_command(project_path, ["pull", "origin", base_branch])

    # Create and checkout new branch
    result = run_git_command(project_path, ["checkout", "-b", branch_name])

    if not result['success']:
        raise HTTPException(status_code=400, detail=f"Failed to create branch: {result.get('stderr')}")

    return {
        "branch_name": branch_name,
        "base_branch": base_branch,
        "message": f"Branch '{branch_name}' created and checked out"
    }


async def commit_changes(args: Dict) -> Dict:
    """Commit changes in project"""
    project_id = args['project_id']
    message = args['message']
    push = args.get('push', False)

    project_path = get_project_path(project_id)

    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not initialized")

    # Stage all changes
    run_git_command(project_path, ["add", "-A"])

    # Commit
    commit_result = run_git_command(project_path, ["commit", "-m", message])

    if not commit_result['success']:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to commit: {commit_result.get('stderr')}"
        )

    result = {
        "committed": True,
        "message": message,
        "commit_output": commit_result['stdout']
    }

    # Push if requested
    if push:
        branch_result = run_git_command(project_path, ["branch", "--show-current"])
        current_branch = branch_result.get('stdout', '').strip()

        push_result = run_git_command(project_path, ["push", "origin", current_branch])
        result['pushed'] = push_result['success']
        result['push_output'] = push_result.get('stdout', '')

    return result


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
