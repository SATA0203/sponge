"""
SQLAlchemy models for Sponge application
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class TaskStatusEnum(str, enum.Enum):
    """Task status enumeration"""
    PENDING = "pending"
    PLANNING = "planning"
    CODING = "coding"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskModel(Base):
    """Database model for development tasks"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    priority = Column(String(50), default="medium")
    tags = Column(JSON, default=list)
    assigned_agents = Column(JSON, default=list)
    
    status = Column(Enum(TaskStatusEnum), default=TaskStatusEnum.PENDING)
    current_step = Column(String(100), nullable=True)
    iterations = Column(Integer, default=0)
    
    errors = Column(JSON, default=list)
    result = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = relationship("FileModel", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Task(id={self.uuid}, title='{self.title}', status={self.status})>"


class FileModel(Base):
    """Database model for files created/modified by tasks"""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    task_uuid = Column(String(36), ForeignKey("tasks.uuid"), nullable=False)
    
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    content = Column(Text, nullable=True)
    file_type = Column(String(50), nullable=True)
    size = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    task = relationship("TaskModel", back_populates="files")

    def __repr__(self):
        return f"<File(id={self.uuid}, name='{self.filename}', path='{self.filepath}')>"
