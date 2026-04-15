"""
Database-backed task manager for Sponge
"""

from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
import uuid
from typing import Optional, List

from app.db.models import TaskModel, TaskStatusEnum, FileModel


class DatabaseTaskManager:
    """Manage tasks using database persistence"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_task(
        self,
        title: str,
        description: str,
        requirements: Optional[str] = None,
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        assigned_agents: Optional[List[str]] = None,
    ) -> TaskModel:
        """Create a new task in the database"""
        task_uuid = str(uuid.uuid4())
        
        task = TaskModel(
            uuid=task_uuid,
            title=title,
            description=description,
            requirements=requirements,
            priority=priority,
            tags=tags or [],
            assigned_agents=assigned_agents or [],
            status=TaskStatusEnum.PENDING,
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def get_task(self, task_uuid: str) -> Optional[TaskModel]:
        """Get a task by UUID"""
        stmt = select(TaskModel).where(TaskModel.uuid == task_uuid)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def update_task_status(
        self,
        task_uuid: str,
        status: TaskStatusEnum,
        current_step: Optional[str] = None,
        iterations: Optional[int] = None,
    ) -> Optional[TaskModel]:
        """Update task status"""
        task = self.get_task(task_uuid)
        if not task:
            return None
        
        task.status = status
        task.updated_at = datetime.utcnow()
        
        if current_step is not None:
            task.current_step = current_step
        
        if iterations is not None:
            task.iterations = iterations
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def add_error(self, task_uuid: str, error: str) -> Optional[TaskModel]:
        """Add an error to a task"""
        task = self.get_task(task_uuid)
        if not task:
            return None
        
        if task.errors is None:
            task.errors = []
        
        task.errors.append(error)
        task.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def set_result(self, task_uuid: str, result: dict) -> Optional[TaskModel]:
        """Set task result"""
        task = self.get_task(task_uuid)
        if not task:
            return None
        
        task.result = result
        task.status = TaskStatusEnum.COMPLETED
        task.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def list_tasks(
        self,
        status_filter: Optional[TaskStatusEnum] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TaskModel]:
        """List tasks with optional filtering"""
        stmt = select(TaskModel)
        
        if status_filter:
            stmt = stmt.where(TaskModel.status == status_filter)
        
        stmt = stmt.order_by(TaskModel.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        
        return self.db.execute(stmt).scalars().all()
    
    def delete_task(self, task_uuid: str) -> bool:
        """Delete a task"""
        task = self.get_task(task_uuid)
        if not task:
            return False
        
        self.db.delete(task)
        self.db.commit()
        return True
    
    def cancel_task(self, task_uuid: str, reason: Optional[str] = None) -> Optional[TaskModel]:
        """Cancel a task"""
        task = self.get_task(task_uuid)
        if not task:
            return None
        
        if task.status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.FAILED, TaskStatusEnum.CANCELLED]:
            raise ValueError(f"Cannot cancel task with status {task.status}")
        
        task.status = TaskStatusEnum.CANCELLED
        task.updated_at = datetime.utcnow()
        
        if reason:
            if task.errors is None:
                task.errors = []
            task.errors.append(f"Cancelled: {reason}")
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
