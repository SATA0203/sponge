"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    REVIEWING = "reviewing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRole(str, Enum):
    """Agent role enumeration"""
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DEPLOYER = "deployer"


# Request Schemas
class CreateTaskRequest(BaseModel):
    """Request to create a new task"""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    requirements: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    tags: Optional[List[str]] = None
    assigned_agents: Optional[List[AgentRole]] = None


class UpdateFileRequest(BaseModel):
    """Request to update a file"""
    file_path: str = Field(..., min_length=1)
    content: str
    operation: str = Field(default="write", pattern="^(write|append|delete)$")


class CancelTaskRequest(BaseModel):
    """Request to cancel a task"""
    reason: Optional[str] = None


class ExecuteCodeRequest(BaseModel):
    """Request to execute code"""
    code: str
    language: str = Field(default="python")
    timeout: int = Field(default=30, ge=1, le=600)
    dependencies: Optional[List[str]] = None


# Response Schemas
class TaskResponse(BaseModel):
    """Basic task response"""
    id: str
    title: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskDetailResponse(TaskResponse):
    """Detailed task response"""
    description: str
    requirements: Optional[str] = None
    priority: int
    tags: Optional[List[str]] = None
    assigned_agents: List[AgentRole] = []
    current_step: Optional[str] = None
    iterations: int = 0
    errors: List[str] = []
    result: Optional[Dict[str, Any]] = None


class FileListResponse(BaseModel):
    """Response for file list"""
    files: List[Dict[str, Any]]
    total: int


class FileContentResponse(BaseModel):
    """Response for file content"""
    file_path: str
    content: str
    language: Optional[str] = None
    size: int


class ExecutionResult(BaseModel):
    """Code execution result"""
    success: bool
    output: str
    error: Optional[str] = None
    execution_time: float
    memory_used: Optional[int] = None


class AgentStateResponse(BaseModel):
    """Agent state response"""
    agent_id: str
    role: AgentRole
    status: str
    current_task: Optional[str] = None
    last_updated: datetime


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, bool] = {}
