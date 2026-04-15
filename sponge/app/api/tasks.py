"""
API Router for Task Management
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from datetime import datetime
import uuid

from app.schemas import (
    CreateTaskRequest,
    TaskResponse,
    TaskDetailResponse,
    CancelTaskRequest,
    TaskStatus,
)

router = APIRouter()

# In-memory task storage (replace with database in production)
tasks_db = {}


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(request: CreateTaskRequest):
    """Create a new development task"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    task = {
        "id": task_id,
        "title": request.title,
        "description": request.description,
        "requirements": request.requirements,
        "priority": request.priority,
        "tags": request.tags or [],
        "assigned_agents": request.assigned_agents or [],
        "status": TaskStatus.PENDING,
        "created_at": now,
        "updated_at": now,
        "current_step": None,
        "iterations": 0,
        "errors": [],
        "result": None,
    }
    
    tasks_db[task_id] = task
    
    # TODO: Trigger workflow execution via Celery
    # execute_workflow.delay(task_id)
    
    return TaskResponse(
        id=task_id,
        title=request.title,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(status_filter: TaskStatus | None = None):
    """List all tasks with optional status filter"""
    tasks = list(tasks_db.values())
    
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    
    # Sort by created_at descending
    tasks.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [
        TaskResponse(
            id=t["id"],
            title=t["title"],
            status=t["status"],
            created_at=t["created_at"],
            updated_at=t["updated_at"],
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """Get detailed information about a specific task"""
    task = tasks_db.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    return TaskDetailResponse(**task)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, request: CancelTaskRequest):
    """Cancel a running task"""
    task = tasks_db.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    if task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status {task['status']}",
        )
    
    task["status"] = TaskStatus.CANCELLED
    task["updated_at"] = datetime.utcnow()
    if request.reason:
        task["errors"].append(f"Cancelled: {request.reason}")
    
    return {"message": f"Task {task_id} cancelled successfully"}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Delete a task"""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    del tasks_db[task_id]
    
    return {"message": f"Task {task_id} deleted successfully"}
