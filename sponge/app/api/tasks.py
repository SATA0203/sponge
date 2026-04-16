"""
API Router for Task Management
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import asyncio
from loguru import logger

from app.schemas import (
    CreateTaskRequest,
    TaskResponse,
    TaskDetailResponse,
    CancelTaskRequest,
    TaskStatus,
)
from app.workflow import get_workflow_manager
from app.core.llm_service import get_llm
from app.db.database import get_db, SessionLocal
from app.db.models import TaskModel, TaskStatusEnum
from sqlalchemy.orm import Session

router = APIRouter()

# Active workflows tracking (in-memory, but tasks are persisted in DB)
active_workflows = {}


async def run_workflow(task_id: str, description: str, language: str):
    """Run the workflow asynchronously"""
    db = SessionLocal()
    try:
        # Get task from database
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found in database")
            return
        
        # Update task status
        task.status = TaskStatusEnum.PLANNING
        task.updated_at = datetime.utcnow()
        db.commit()
        
        # Get workflow manager and execute
        workflow_manager = get_workflow_manager()
        result = await workflow_manager.execute(
            description=description,
            language=language,
            task_id=task_id,
            max_iterations=3,
        )
        
        # Update task with results
        task.updated_at = datetime.utcnow()
        task.iterations = result.get("iterations", 0)
        
        if result.get("status") == "failed":
            task.status = TaskStatusEnum.FAILED
            errors = task.errors or []
            errors.append(result.get("error", "Unknown error"))
            task.errors = errors
        else:
            task.status = TaskStatusEnum.COMPLETED
            task.result = {
                "plan": result.get("plan", {}),
                "code": result.get("code", {}),
                "execution_result": result.get("execution_result", {}),
                "review_result": result.get("review_result", {}),
            }
        
        db.commit()
        
        # Remove from active workflows
        if task_id in active_workflows:
            del active_workflows[task_id]
            
    except Exception as e:
        logger.error(f"Workflow execution failed for task {task_id}: {e}")
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        if task:
            task.status = TaskStatusEnum.FAILED
            task.updated_at = datetime.utcnow()
            errors = task.errors or []
            errors.append(str(e))
            task.errors = errors
            db.commit()
        if task_id in active_workflows:
            del active_workflows[task_id]
    finally:
        db.close()


@router.post("/execute", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def execute_task(
    request: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create and execute a development task using multi-agent workflow"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Initialize task in database
    task = TaskModel(
        uuid=task_id,
        title=request.title,
        description=request.description,
        requirements=request.requirements,
        priority=request.priority,
        tags=request.tags or [],
        assigned_agents=request.assigned_agents or [],
        status=TaskStatusEnum.PENDING,
        current_step=None,
        iterations=0,
        errors=[],
        result=None,
    )
    
    db.add(task)
    db.commit()
    
    # Start workflow in background
    background_tasks.add_task(
        run_workflow,
        task_id,
        request.description,
        "python",  # Default language
    )
    
    return TaskResponse(
        id=task_id,
        title=request.title,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: CreateTaskRequest,
    db: Session = Depends(get_db),
):
    """Create a new development task (manual execution)"""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    task = TaskModel(
        uuid=task_id,
        title=request.title,
        description=request.description,
        requirements=request.requirements,
        priority=request.priority,
        tags=request.tags or [],
        assigned_agents=request.assigned_agents or [],
        status=TaskStatusEnum.PENDING,
        current_step=None,
        iterations=0,
        errors=[],
        result=None,
    )
    
    db.add(task)
    db.commit()
    
    return TaskResponse(
        id=task_id,
        title=request.title,
        status=TaskStatus.PENDING,
        created_at=now,
        updated_at=now,
    )


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status_filter: TaskStatus | None = None,
    db: Session = Depends(get_db),
):
    """List all tasks with optional status filter"""
    query = db.query(TaskModel)
    
    if status_filter:
        # Map TaskStatus to TaskStatusEnum
        status_enum = TaskStatusEnum(status_filter.value)
        query = query.filter(TaskModel.status == status_enum)
    
    # Sort by created_at descending
    tasks = query.order_by(TaskModel.created_at.desc()).all()
    
    return [
        TaskResponse(
            id=t.uuid,
            title=t.title,
            status=TaskStatus(t.status.value),
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific task"""
    task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    return TaskDetailResponse(
        id=task.uuid,
        title=task.title,
        description=task.description,
        requirements=task.requirements,
        priority=task.priority,
        tags=task.tags or [],
        assigned_agents=task.assigned_agents or [],
        status=TaskStatus(task.status.value),
        created_at=task.created_at,
        updated_at=task.updated_at,
        current_step=task.current_step,
        iterations=task.iterations,
        errors=task.errors or [],
        result=task.result,
    )


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: CancelTaskRequest,
    db: Session = Depends(get_db),
):
    """Cancel a running task"""
    task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    if task.status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status {task.status.value}",
        )
    
    task.status = TaskStatusEnum.CANCELLED
    task.updated_at = datetime.utcnow()
    if request.reason:
        errors = task.errors or []
        errors.append(f"Cancelled: {request.reason}")
        task.errors = errors
    
    db.commit()
    
    return {"message": f"Task {task_id} cancelled successfully"}


@router.delete("/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """Delete a task"""
    task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    db.delete(task)
    db.commit()
    
    return {"message": f"Task {task_id} deleted successfully"}
