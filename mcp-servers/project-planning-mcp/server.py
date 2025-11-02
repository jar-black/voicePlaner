#!/usr/bin/env python3
"""
Project Planning MCP Server
Provides tools for managing projects, epics, stories, and tasks
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


app = FastAPI(title="Project Planning MCP Server")

# Global database pool
db_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool"""
    global db_pool
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10
    )
    print("Database connection pool initialized")


@app.on_event("startup")
async def startup():
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "project-planning-mcp"}


@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    return {
        "tools": [
            {
                "name": "create_project",
                "description": "Create a new project with basic information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "description": {"type": "string", "description": "Project description"},
                        "tech_stack": {"type": "object", "description": "Technology stack details"}
                    },
                    "required": ["name", "description"]
                }
            },
            {
                "name": "create_epic",
                "description": "Create an epic within a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "title": {"type": "string", "description": "Epic title"},
                        "description": {"type": "string", "description": "Epic description"},
                        "priority": {"type": "integer", "description": "Priority (0-10)"}
                    },
                    "required": ["project_id", "title"]
                }
            },
            {
                "name": "create_story",
                "description": "Create a user story within an epic",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "epic_id": {"type": "string", "description": "Epic UUID"},
                        "title": {"type": "string", "description": "Story title"},
                        "description": {"type": "string", "description": "Story description"},
                        "user_story": {"type": "string", "description": "User story format (As a... I want... So that...)"},
                        "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Acceptance criteria"},
                        "story_points": {"type": "integer", "description": "Story points"}
                    },
                    "required": ["epic_id", "title"]
                }
            },
            {
                "name": "create_task",
                "description": "Create a technical task within a story",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "story_id": {"type": "string", "description": "Story UUID"},
                        "title": {"type": "string", "description": "Task title"},
                        "description": {"type": "string", "description": "Task description"},
                        "task_type": {"type": "string", "enum": ["setup", "feature", "bug", "test", "documentation", "refactor", "deployment"]},
                        "estimated_hours": {"type": "number", "description": "Estimated hours"},
                        "technical_details": {"type": "object", "description": "Technical implementation details"}
                    },
                    "required": ["story_id", "title"]
                }
            },
            {
                "name": "get_project_plan",
                "description": "Retrieve complete project plan with all epics, stories, and tasks",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "update_task_status",
                "description": "Update the status of a task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task UUID"},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done", "blocked"]}
                    },
                    "required": ["task_id", "status"]
                }
            },
            {
                "name": "update_project_status",
                "description": "Update project status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "status": {"type": "string", "enum": ["planning", "refining", "ready", "in_progress", "completed", "archived"]},
                        "github_repo_url": {"type": "string", "description": "GitHub repository URL"}
                    },
                    "required": ["project_id", "status"]
                }
            },
            {
                "name": "query_tasks_by_status",
                "description": "Query tasks by their status across a project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "status": {"type": "string", "enum": ["todo", "in_progress", "review", "done", "blocked"]}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "get_next_tasks",
                "description": "Get next tasks to work on (prioritized todo tasks)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"},
                        "limit": {"type": "integer", "description": "Number of tasks to return", "default": 5}
                    },
                    "required": ["project_id"]
                }
            },
            {
                "name": "export_project_markdown",
                "description": "Export entire project plan as formatted markdown",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project UUID"}
                    },
                    "required": ["project_id"]
                }
            }
        ]
    }


@app.post("/call_tool", response_model=ToolResponse)
async def call_tool(tool_call: ToolCall):
    """Execute an MCP tool"""
    try:
        if tool_call.name == "create_project":
            result = await create_project(tool_call.arguments)
        elif tool_call.name == "create_epic":
            result = await create_epic(tool_call.arguments)
        elif tool_call.name == "create_story":
            result = await create_story(tool_call.arguments)
        elif tool_call.name == "create_task":
            result = await create_task(tool_call.arguments)
        elif tool_call.name == "get_project_plan":
            result = await get_project_plan(tool_call.arguments)
        elif tool_call.name == "update_task_status":
            result = await update_task_status(tool_call.arguments)
        elif tool_call.name == "update_project_status":
            result = await update_project_status(tool_call.arguments)
        elif tool_call.name == "query_tasks_by_status":
            result = await query_tasks_by_status(tool_call.arguments)
        elif tool_call.name == "get_next_tasks":
            result = await get_next_tasks(tool_call.arguments)
        elif tool_call.name == "export_project_markdown":
            result = await export_project_markdown(tool_call.arguments)
        else:
            return ToolResponse(success=False, error=f"Unknown tool: {tool_call.name}")

        return ToolResponse(success=True, data=result)
    except Exception as e:
        return ToolResponse(success=False, error=str(e))


# Tool implementations

async def create_project(args: Dict) -> Dict:
    """Create a new project"""
    async with db_pool.acquire() as conn:
        project = await conn.fetchrow(
            """
            INSERT INTO projects (name, description, tech_stack, status)
            VALUES ($1, $2, $3, 'planning')
            RETURNING id, name, description, status, created_at
            """,
            args['name'],
            args['description'],
            json.dumps(args.get('tech_stack', {}))
        )
        return {
            "project_id": str(project['id']),
            "name": project['name'],
            "description": project['description'],
            "status": project['status'],
            "created_at": project['created_at'].isoformat()
        }


async def create_epic(args: Dict) -> Dict:
    """Create an epic within a project"""
    async with db_pool.acquire() as conn:
        # Get next order index
        max_order = await conn.fetchval(
            "SELECT COALESCE(MAX(order_index), 0) FROM epics WHERE project_id = $1",
            args['project_id']
        )

        epic = await conn.fetchrow(
            """
            INSERT INTO epics (project_id, title, description, priority, order_index)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, title, description, priority, status, created_at
            """,
            args['project_id'],
            args['title'],
            args.get('description'),
            args.get('priority', 0),
            max_order + 1
        )
        return {
            "epic_id": str(epic['id']),
            "title": epic['title'],
            "description": epic['description'],
            "priority": epic['priority'],
            "status": epic['status'],
            "created_at": epic['created_at'].isoformat()
        }


async def create_story(args: Dict) -> Dict:
    """Create a user story within an epic"""
    async with db_pool.acquire() as conn:
        max_order = await conn.fetchval(
            "SELECT COALESCE(MAX(order_index), 0) FROM stories WHERE epic_id = $1",
            args['epic_id']
        )

        story = await conn.fetchrow(
            """
            INSERT INTO stories (epic_id, title, description, user_story, acceptance_criteria, story_points, priority, order_index)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, title, description, status, created_at
            """,
            args['epic_id'],
            args['title'],
            args.get('description'),
            args.get('user_story'),
            args.get('acceptance_criteria', []),
            args.get('story_points'),
            args.get('priority', 0),
            max_order + 1
        )
        return {
            "story_id": str(story['id']),
            "title": story['title'],
            "description": story['description'],
            "status": story['status'],
            "created_at": story['created_at'].isoformat()
        }


async def create_task(args: Dict) -> Dict:
    """Create a technical task within a story"""
    async with db_pool.acquire() as conn:
        max_order = await conn.fetchval(
            "SELECT COALESCE(MAX(order_index), 0) FROM tasks WHERE story_id = $1",
            args['story_id']
        )

        task = await conn.fetchrow(
            """
            INSERT INTO tasks (story_id, title, description, task_type, estimated_hours, technical_details, order_index)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, title, description, task_type, status, created_at
            """,
            args['story_id'],
            args['title'],
            args.get('description'),
            args.get('task_type', 'feature'),
            args.get('estimated_hours'),
            json.dumps(args.get('technical_details', {})),
            max_order + 1
        )
        return {
            "task_id": str(task['id']),
            "title": task['title'],
            "description": task['description'],
            "task_type": task['task_type'],
            "status": task['status'],
            "created_at": task['created_at'].isoformat()
        }


async def get_project_plan(args: Dict) -> Dict:
    """Retrieve complete project plan"""
    async with db_pool.acquire() as conn:
        # Get project
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1",
            args['project_id']
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get epics with stories and tasks
        epics = await conn.fetch(
            "SELECT * FROM epics WHERE project_id = $1 ORDER BY order_index, created_at",
            args['project_id']
        )

        plan = {
            "project": {
                "id": str(project['id']),
                "name": project['name'],
                "description": project['description'],
                "status": project['status'],
                "github_repo_url": project['github_repo_url'],
                "tech_stack": project['tech_stack'],
                "created_at": project['created_at'].isoformat(),
                "updated_at": project['updated_at'].isoformat()
            },
            "epics": []
        }

        for epic in epics:
            epic_dict = {
                "id": str(epic['id']),
                "title": epic['title'],
                "description": epic['description'],
                "priority": epic['priority'],
                "status": epic['status'],
                "stories": []
            }

            stories = await conn.fetch(
                "SELECT * FROM stories WHERE epic_id = $1 ORDER BY order_index, created_at",
                epic['id']
            )

            for story in stories:
                story_dict = {
                    "id": str(story['id']),
                    "title": story['title'],
                    "description": story['description'],
                    "user_story": story['user_story'],
                    "acceptance_criteria": story['acceptance_criteria'],
                    "story_points": story['story_points'],
                    "status": story['status'],
                    "tasks": []
                }

                tasks = await conn.fetch(
                    "SELECT * FROM tasks WHERE story_id = $1 ORDER BY order_index, created_at",
                    story['id']
                )

                for task in tasks:
                    story_dict['tasks'].append({
                        "id": str(task['id']),
                        "title": task['title'],
                        "description": task['description'],
                        "task_type": task['task_type'],
                        "estimated_hours": float(task['estimated_hours']) if task['estimated_hours'] else None,
                        "status": task['status'],
                        "technical_details": task['technical_details'],
                        "github_issue_url": task['github_issue_url']
                    })

                epic_dict['stories'].append(story_dict)

            plan['epics'].append(epic_dict)

        return plan


async def update_task_status(args: Dict) -> Dict:
    """Update task status"""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "UPDATE tasks SET status = $1 WHERE id = $2 RETURNING id, title, status",
            args['status'],
            args['task_id']
        )

        if not result:
            raise HTTPException(status_code=404, detail="Task not found")

        return {
            "task_id": str(result['id']),
            "title": result['title'],
            "status": result['status']
        }


async def update_project_status(args: Dict) -> Dict:
    """Update project status"""
    async with db_pool.acquire() as conn:
        update_fields = ["status = $1"]
        params = [args['status'], args['project_id']]

        if args.get('github_repo_url'):
            update_fields.append("github_repo_url = $3")
            params.insert(2, args['github_repo_url'])

        query = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = ${len(params)} RETURNING id, name, status, github_repo_url"

        result = await conn.fetchrow(query, *params)

        if not result:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "project_id": str(result['id']),
            "name": result['name'],
            "status": result['status'],
            "github_repo_url": result['github_repo_url']
        }


async def query_tasks_by_status(args: Dict) -> Dict:
    """Query tasks by status"""
    async with db_pool.acquire() as conn:
        query = """
            SELECT t.id, t.title, t.description, t.task_type, t.status, t.estimated_hours,
                   s.title as story_title, e.title as epic_title
            FROM tasks t
            JOIN stories s ON t.story_id = s.id
            JOIN epics e ON s.epic_id = e.id
            WHERE e.project_id = $1
        """
        params = [args['project_id']]

        if args.get('status'):
            query += " AND t.status = $2"
            params.append(args['status'])

        query += " ORDER BY t.order_index, t.created_at"

        tasks = await conn.fetch(query, *params)

        return {
            "tasks": [
                {
                    "id": str(task['id']),
                    "title": task['title'],
                    "description": task['description'],
                    "task_type": task['task_type'],
                    "status": task['status'],
                    "estimated_hours": float(task['estimated_hours']) if task['estimated_hours'] else None,
                    "story_title": task['story_title'],
                    "epic_title": task['epic_title']
                }
                for task in tasks
            ]
        }


async def get_next_tasks(args: Dict) -> Dict:
    """Get next prioritized tasks to work on"""
    async with db_pool.acquire() as conn:
        limit = args.get('limit', 5)

        tasks = await conn.fetch(
            """
            SELECT t.id, t.title, t.description, t.task_type, t.estimated_hours,
                   s.title as story_title, s.priority as story_priority,
                   e.title as epic_title, e.priority as epic_priority
            FROM tasks t
            JOIN stories s ON t.story_id = s.id
            JOIN epics e ON s.epic_id = e.id
            WHERE e.project_id = $1 AND t.status = 'todo'
            ORDER BY e.priority DESC, s.priority DESC, t.order_index
            LIMIT $2
            """,
            args['project_id'],
            limit
        )

        return {
            "next_tasks": [
                {
                    "id": str(task['id']),
                    "title": task['title'],
                    "description": task['description'],
                    "task_type": task['task_type'],
                    "estimated_hours": float(task['estimated_hours']) if task['estimated_hours'] else None,
                    "story": task['story_title'],
                    "epic": task['epic_title']
                }
                for task in tasks
            ]
        }


async def export_project_markdown(args: Dict) -> Dict:
    """Export project plan as markdown"""
    plan = await get_project_plan(args)

    md = f"# {plan['project']['name']}\n\n"
    md += f"{plan['project']['description']}\n\n"
    md += f"**Status:** {plan['project']['status']}\n\n"

    if plan['project'].get('github_repo_url'):
        md += f"**Repository:** {plan['project']['github_repo_url']}\n\n"

    md += "---\n\n"

    for epic in plan['epics']:
        md += f"## Epic: {epic['title']}\n\n"
        if epic['description']:
            md += f"{epic['description']}\n\n"
        md += f"**Priority:** {epic['priority']} | **Status:** {epic['status']}\n\n"

        for story in epic['stories']:
            md += f"### Story: {story['title']}\n\n"
            if story['user_story']:
                md += f"_{story['user_story']}_\n\n"
            if story['description']:
                md += f"{story['description']}\n\n"

            if story['acceptance_criteria']:
                md += "**Acceptance Criteria:**\n"
                for criterion in story['acceptance_criteria']:
                    md += f"- {criterion}\n"
                md += "\n"

            md += "**Tasks:**\n"
            for task in story['tasks']:
                status_icon = "✅" if task['status'] == 'done' else "🔄" if task['status'] == 'in_progress' else "📋"
                md += f"- {status_icon} [{task['task_type']}] {task['title']}"
                if task['estimated_hours']:
                    md += f" ({task['estimated_hours']}h)"
                md += "\n"
            md += "\n"

    return {"markdown": md}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
