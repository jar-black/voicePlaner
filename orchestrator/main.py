"""
AI Project Orchestrator - Main Application
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import json
from typing import Optional
from uuid import UUID

from config import get_settings, Settings
from services.claude_service import ClaudeService
from services.mcp_client import MCPClientManager
from models.project import (
    ProjectCreate,
    ProjectResponse,
    ConversationContinue,
    ProjectFinalize,
    TaskExecuteRequest,
    ProjectStatus
)


# Global state
db_pool: Optional[asyncpg.Pool] = None
claude_service: Optional[ClaudeService] = None
mcp_manager: Optional[MCPClientManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    global db_pool, claude_service, mcp_manager

    settings = get_settings()

    # Initialize database
    db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
    print("Database pool initialized")

    # Initialize Claude service
    claude_service = ClaudeService(
        api_key=settings.anthropic_api_key,
        model=settings.claude_model
    )
    print("Claude service initialized")

    # Initialize MCP clients
    mcp_manager = MCPClientManager(
        planning_url=settings.planning_mcp_url,
        github_url=settings.github_mcp_url,
        claude_code_url=settings.claude_code_mcp_url
    )
    print("MCP clients initialized")

    # Check MCP health
    health = await mcp_manager.check_health()
    print(f"MCP Health: {health}")

    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
    if mcp_manager:
        await mcp_manager.close_all()
    print("Shutdown complete")


app = FastAPI(
    title="AI Project Orchestrator",
    description="Orchestrate AI-powered software project creation and execution",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Project Orchestrator",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    mcp_health = await mcp_manager.check_health()

    return {
        "status": "healthy",
        "database": db_pool is not None,
        "claude": claude_service is not None,
        "mcp_servers": mcp_health
    }


@app.post("/projects/create")
async def create_project(request: ProjectCreate):
    """
    Start a new project creation conversation

    This initiates the project planning process with Claude
    """
    # Analyze initial description
    analysis = await claude_service.analyze_project_description(
        request.initial_description
    )

    # Create conversation record
    async with db_pool.acquire() as conn:
        # Create project
        project = await conn.fetchrow(
            """
            INSERT INTO projects (name, description, status, tech_stack)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, description, status, created_at, updated_at
            """,
            analysis.get("project_name", "Untitled Project"),
            request.initial_description,
            "planning",
            json.dumps(analysis.get("tech_stack", {}))
        )

        # Create conversation
        messages = [
            {"role": "user", "content": request.initial_description},
            {"role": "assistant", "content": analysis.get("raw_response", "")}
        ]

        await conn.execute(
            """
            INSERT INTO conversations (project_id, phase, messages)
            VALUES ($1, $2, $3)
            """,
            project['id'],
            "creation",
            json.dumps(messages)
        )

    # Formulate response
    response_text = f"""Great! I've analyzed your project idea. Here's what I understand:

**Project Name:** {analysis.get('project_name')}
**Type:** {analysis.get('project_type')}
**Complexity:** {analysis.get('complexity')}

"""

    if analysis.get('tech_stack'):
        response_text += f"**Suggested Tech Stack:** {', '.join(str(v) for v in analysis.get('tech_stack', {}).values())}\n\n"

    if analysis.get('initial_epics'):
        response_text += "**Initial Features:**\n"
        for epic in analysis.get('initial_epics', []):
            response_text += f"- {epic}\n"
        response_text += "\n"

    if analysis.get('clarification_questions'):
        response_text += "**I have a few questions to refine the plan:**\n"
        for i, question in enumerate(analysis.get('clarification_questions', []), 1):
            response_text += f"{i}. {question}\n"

    return {
        "project_id": str(project['id']),
        "project_name": analysis.get('project_name'),
        "status": "refining",
        "response": response_text,
        "analysis": analysis
    }


@app.post("/projects/continue")
async def continue_conversation(request: ConversationContinue):
    """
    Continue refining the project plan

    User provides more information, Claude asks more questions or finalizes
    """
    async with db_pool.acquire() as conn:
        # Get conversation history
        conversation = await conn.fetchrow(
            """
            SELECT messages, phase FROM conversations
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            request.project_id
        )

        if not conversation:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get conversation history
        messages = json.loads(conversation['messages'])

        # Add user message
        messages.append({"role": "user", "content": request.message})

        # Get Claude's response
        refinement = await claude_service.refine_project_plan(
            messages[:-1],  # Previous messages
            request.message  # New message
        )

        # Add assistant response
        messages.append({"role": "assistant", "content": refinement['response']})

        # Update conversation
        await conn.execute(
            """
            UPDATE conversations
            SET messages = $1, updated_at = CURRENT_TIMESTAMP
            WHERE project_id = $2 AND phase = $3
            """,
            json.dumps(messages),
            request.project_id,
            conversation['phase']
        )

        # Update project status if ready
        if refinement['ready_to_finalize']:
            await conn.execute(
                "UPDATE projects SET status = $1 WHERE id = $2",
                "ready",
                request.project_id
            )

    return {
        "project_id": str(request.project_id),
        "response": refinement['response'],
        "ready_to_finalize": refinement['ready_to_finalize'],
        "plan_data": refinement.get('plan_data')
    }


@app.post("/projects/finalize")
async def finalize_project(request: ProjectFinalize):
    """
    Finalize project and create all resources

    This creates:
    1. Project structure in planning MCP
    2. GitHub repository (optional)
    3. GitHub issues from tasks (optional)
    4. Claude Code project initialization
    """
    async with db_pool.acquire() as conn:
        # Get project
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1",
            request.project_id
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get conversation history
        conversation = await conn.fetchrow(
            """
            SELECT messages FROM conversations
            WHERE project_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            request.project_id
        )

        messages = json.loads(conversation['messages'])

        # Generate final project structure
        structure = await claude_service.generate_project_structure(messages)

        # Create epics, stories, and tasks in planning MCP
        epic_ids = []
        for epic_data in structure.get('epics', []):
            epic = await mcp_manager.planning.call_tool(
                "create_epic",
                {
                    "project_id": str(request.project_id),
                    "title": epic_data['title'],
                    "description": epic_data.get('description'),
                    "priority": epic_data.get('priority', 5)
                }
            )
            epic_id = epic['epic_id']
            epic_ids.append(epic_id)

            # Create stories
            for story_data in epic_data.get('stories', []):
                story = await mcp_manager.planning.call_tool(
                    "create_story",
                    {
                        "epic_id": epic_id,
                        "title": story_data['title'],
                        "description": story_data.get('description'),
                        "user_story": story_data.get('user_story'),
                        "acceptance_criteria": story_data.get('acceptance_criteria', []),
                        "story_points": story_data.get('story_points')
                    }
                )
                story_id = story['story_id']

                # Create tasks
                for task_data in story_data.get('tasks', []):
                    await mcp_manager.planning.call_tool(
                        "create_task",
                        {
                            "story_id": story_id,
                            "title": task_data['title'],
                            "description": task_data.get('description'),
                            "task_type": task_data.get('task_type', 'feature'),
                            "estimated_hours": task_data.get('estimated_hours'),
                            "technical_details": task_data.get('technical_details', {})
                        }
                    )

        # Create GitHub repository if requested
        github_repo_url = None
        if request.create_github_repo:
            repo_result = await mcp_manager.github.call_tool(
                "create_repository",
                {
                    "name": project['name'].lower().replace(' ', '-'),
                    "description": project['description'],
                    "private": True,
                    "auto_init": True
                }
            )
            github_repo_url = repo_result['repo_url']

            # Create project structure
            project_type = structure.get('project', {}).get('tech_stack', {}).get('type', 'generic')
            await mcp_manager.github.call_tool(
                "create_project_structure",
                {
                    "repo_name": project['name'].lower().replace(' ', '-'),
                    "project_type": project_type
                }
            )

            # Create labels
            await mcp_manager.github.call_tool(
                "create_labels",
                {
                    "repo_name": project['name'].lower().replace(' ', '-'),
                    "label_set": "extended"
                }
            )

            # Update project with GitHub URL
            await conn.execute(
                "UPDATE projects SET github_repo_url = $1, github_repo_name = $2 WHERE id = $3",
                github_repo_url,
                project['name'].lower().replace(' ', '-'),
                request.project_id
            )

        # Create GitHub issues if requested
        if request.create_issues and github_repo_url:
            tasks_result = await mcp_manager.planning.call_tool(
                "query_tasks_by_status",
                {"project_id": str(request.project_id)}
            )

            if tasks_result.get('tasks'):
                issues_result = await mcp_manager.github.call_tool(
                    "create_issues_from_tasks",
                    {
                        "repo_name": project['name'].lower().replace(' ', '-'),
                        "tasks": tasks_result['tasks']
                    }
                )

                # Update tasks with GitHub issue URLs
                for issue_info in issues_result.get('issues', []):
                    if issue_info.get('task_id'):
                        await conn.execute(
                            """
                            UPDATE tasks
                            SET github_issue_number = $1, github_issue_url = $2
                            WHERE id = $3
                            """,
                            issue_info['issue_number'],
                            issue_info['issue_url'],
                            issue_info['task_id']
                        )

        # Initialize Claude Code project if GitHub repo was created
        if github_repo_url:
            await mcp_manager.claude_code.call_tool(
                "init_project",
                {
                    "project_id": str(request.project_id),
                    "repo_url": github_repo_url,
                    "project_name": project['name']
                }
            )

        # Update project status
        await conn.execute(
            "UPDATE projects SET status = $1 WHERE id = $2",
            "ready",
            request.project_id
        )

    return {
        "success": True,
        "project_id": str(request.project_id),
        "github_repo_url": github_repo_url,
        "epic_count": len(epic_ids),
        "message": "Project successfully finalized and resources created"
    }


@app.get("/projects/{project_id}")
async def get_project(project_id: UUID):
    """Get project details"""
    async with db_pool.acquire() as conn:
        project = await conn.fetchrow(
            "SELECT * FROM projects WHERE id = $1",
            project_id
        )

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "id": str(project['id']),
            "name": project['name'],
            "description": project['description'],
            "status": project['status'],
            "github_repo_url": project['github_repo_url'],
            "tech_stack": project['tech_stack'],
            "created_at": project['created_at'].isoformat(),
            "updated_at": project['updated_at'].isoformat()
        }


@app.get("/projects/{project_id}/plan")
async def get_project_plan(project_id: UUID):
    """Get complete project plan"""
    plan = await mcp_manager.planning.call_tool(
        "get_project_plan",
        {"project_id": str(project_id)}
    )
    return plan


@app.get("/projects/{project_id}/next-tasks")
async def get_next_tasks(project_id: UUID, limit: int = 5):
    """Get next prioritized tasks to work on"""
    tasks = await mcp_manager.planning.call_tool(
        "get_next_tasks",
        {
            "project_id": str(project_id),
            "limit": limit
        }
    )
    return tasks


@app.post("/tasks/execute")
async def execute_task(request: TaskExecuteRequest):
    """Execute a task using Claude Code"""
    async with db_pool.acquire() as conn:
        # Get task details with project info
        task = await conn.fetchrow(
            """
            SELECT t.*, s.title as story_title, e.title as epic_title, p.id as project_id
            FROM tasks t
            JOIN stories s ON t.story_id = s.id
            JOIN epics e ON s.epic_id = e.id
            JOIN projects p ON e.project_id = p.id
            WHERE t.id = $1
            """,
            request.task_id
        )

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Prepare task data
        task_data = {
            "id": str(task['id']),
            "title": task['title'],
            "description": task['description'],
            "task_type": task['task_type'],
            "estimated_hours": float(task['estimated_hours']) if task['estimated_hours'] else None,
            "technical_details": task['technical_details'],
            "story_title": task['story_title'],
            "epic_title": task['epic_title']
        }

        # Execute task via Claude Code MCP
        result = await mcp_manager.claude_code.call_tool(
            "execute_task",
            {
                "project_id": str(task['project_id']),
                "task": task_data,
                "context": request.context
            }
        )

        # Update task status
        await conn.execute(
            "UPDATE tasks SET status = $1 WHERE id = $2",
            "in_progress",
            request.task_id
        )

        # Log execution
        await conn.execute(
            """
            INSERT INTO execution_logs (task_id, execution_type, status, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            request.task_id,
            "claude_code",
            "started",
            json.dumps(result)
        )

    return {
        "success": True,
        "task_id": str(request.task_id),
        "execution_result": result
    }


@app.get("/projects")
async def list_projects(status: Optional[str] = None, limit: int = 20):
    """List all projects"""
    async with db_pool.acquire() as conn:
        if status:
            projects = await conn.fetch(
                """
                SELECT * FROM projects
                WHERE status = $1
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                status,
                limit
            )
        else:
            projects = await conn.fetch(
                """
                SELECT * FROM projects
                ORDER BY updated_at DESC
                LIMIT $1
                """,
                limit
            )

        return {
            "projects": [
                {
                    "id": str(p['id']),
                    "name": p['name'],
                    "description": p['description'],
                    "status": p['status'],
                    "github_repo_url": p['github_repo_url'],
                    "created_at": p['created_at'].isoformat(),
                    "updated_at": p['updated_at'].isoformat()
                }
                for p in projects
            ]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
