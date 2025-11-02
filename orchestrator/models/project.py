"""
Project models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ProjectStatus(str, Enum):
    PLANNING = "planning"
    REFINING = "refining"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    SETUP = "setup"
    FEATURE = "feature"
    BUG = "bug"
    TEST = "test"
    DOCUMENTATION = "documentation"
    REFACTOR = "refactor"
    DEPLOYMENT = "deployment"


class ProjectCreate(BaseModel):
    """Request to create a new project"""
    initial_description: str = Field(..., description="Initial project description")


class ProjectResponse(BaseModel):
    """Project response"""
    id: UUID
    name: str
    description: str
    status: ProjectStatus
    github_repo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationMessage(BaseModel):
    """A message in a conversation"""
    role: str  # "user" or "assistant"
    content: str


class ConversationContinue(BaseModel):
    """Continue a conversation"""
    project_id: UUID
    message: str


class ProjectFinalize(BaseModel):
    """Request to finalize a project"""
    project_id: UUID
    create_github_repo: bool = True
    create_issues: bool = True


class TaskExecuteRequest(BaseModel):
    """Request to execute a task"""
    task_id: UUID
    context: Optional[str] = None
