"""
Tests for database module
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import uuid

from app.db.models import TaskModel, TaskStatusEnum, FileModel
from app.db.task_manager import DatabaseTaskManager


class TestTaskModel:
    """Test TaskModel database model"""
    
    def test_create_task(self, db_session):
        """Test creating a task"""
        task_uuid = str(uuid.uuid4())
        task = TaskModel(
            uuid=task_uuid,
            title="Test Task",
            description="Test Description",
            requirements="Test Requirements",
            priority="high",
            tags=["test", "demo"],
            assigned_agents=["orchestrator", "worker"],
            status=TaskStatusEnum.PENDING,
        )
        
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        assert task.uuid == task_uuid
        assert task.title == "Test Task"
        assert task.status == TaskStatusEnum.PENDING
        assert task.priority == "high"
        assert task.tags == ["test", "demo"]
    
    def test_task_repr(self):
        """Test TaskModel string representation"""
        task = TaskModel(
            uuid="test-uuid-123",
            title="My Task",
            description="Description",
            status=TaskStatusEnum.PLANNING,
        )
        assert "test-uuid-123" in repr(task)
        assert "My Task" in repr(task)
        assert "PLANNING" in repr(task)
    
    def test_task_status_transitions(self, db_session):
        """Test task status transitions"""
        task_uuid = str(uuid.uuid4())
        task = TaskModel(
            uuid=task_uuid,
            title="Status Test",
            description="Testing status changes",
            status=TaskStatusEnum.PENDING,
        )
        
        db_session.add(task)
        db_session.commit()
        
        # Transition to PLANNING
        task.status = TaskStatusEnum.PLANNING
        db_session.commit()
        assert task.status == TaskStatusEnum.PLANNING
        
        # Transition to CODING
        task.status = TaskStatusEnum.CODING
        db_session.commit()
        assert task.status == TaskStatusEnum.CODING
        
        # Transition to COMPLETED
        task.status = TaskStatusEnum.COMPLETED
        db_session.commit()
        assert task.status == TaskStatusEnum.COMPLETED


class TestFileModel:
    """Test FileModel database model"""
    
    def test_create_file(self, db_session):
        """Test creating a file associated with a task"""
        task_uuid = str(uuid.uuid4())
        file_uuid = str(uuid.uuid4())
        
        task = TaskModel(
            uuid=task_uuid,
            title="Parent Task",
            description="Task with files",
            status=TaskStatusEnum.PENDING,
        )
        db_session.add(task)
        db_session.commit()
        
        file = FileModel(
            uuid=file_uuid,
            task_uuid=task_uuid,
            filename="test.py",
            filepath="/workspace/test.py",
            content="print('hello')",
            file_type="python",
            size=15,
        )
        
        db_session.add(file)
        db_session.commit()
        db_session.refresh(file)
        
        assert file.uuid == file_uuid
        assert file.task_uuid == task_uuid
        assert file.filename == "test.py"
        assert file.content == "print('hello')"
        assert file.size == 15
    
    def test_file_repr(self):
        """Test FileModel string representation"""
        file = FileModel(
            uuid="file-uuid-456",
            task_uuid="task-uuid-789",
            filename="code.py",
            filepath="/path/to/code.py",
        )
        assert "file-uuid-456" in repr(file)
        assert "code.py" in repr(file)


class TestDatabaseTaskManager:
    """Test DatabaseTaskManager operations"""
    
    def test_create_task(self, db_session):
        """Test creating a task via manager"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Manager Created Task",
            description="Created by DatabaseTaskManager",
            requirements="Must work properly",
            priority="high",
            tags=["manager", "test"],
            assigned_agents=["orchestrator"],
        )
        
        assert task.uuid is not None
        assert task.title == "Manager Created Task"
        assert task.status == TaskStatusEnum.PENDING
        assert task.priority == "high"
        assert len(task.tags) == 2
    
    def test_get_task(self, db_session):
        """Test retrieving a task by UUID"""
        manager = DatabaseTaskManager(db=db_session)
        
        # Create a task
        task = manager.create_task(
            title="Get Task Test",
            description="Testing retrieval",
        )
        
        # Retrieve it
        retrieved = manager.get_task(task.uuid)
        
        assert retrieved is not None
        assert retrieved.uuid == task.uuid
        assert retrieved.title == "Get Task Test"
    
    def test_get_task_not_found(self, db_session):
        """Test retrieving a non-existent task"""
        manager = DatabaseTaskManager(db=db_session)
        
        result = manager.get_task("non-existent-uuid")
        assert result is None
    
    def test_update_task_status(self, db_session):
        """Test updating task status"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Status Update Test",
            description="Testing status updates",
        )
        
        assert task.status == TaskStatusEnum.PENDING
        
        updated = manager.update_task_status(
            task_uuid=task.uuid,
            status=TaskStatusEnum.EXECUTING,
            current_step="Running code",
            iterations=2,
        )
        
        assert updated.status == TaskStatusEnum.EXECUTING
        assert updated.current_step == "Running code"
        assert updated.iterations == 2
    
    def test_add_error(self, db_session):
        """Test adding errors to a task"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Error Test",
            description="Testing error tracking",
        )
        
        manager.add_error(task.uuid, "First error occurred")
        manager.add_error(task.uuid, "Second error occurred")
        
        # Need to fetch fresh from DB since JSON columns may not update in-place
        updated_task = db_session.query(TaskModel).filter(TaskModel.uuid == task.uuid).first()
        assert len(updated_task.errors) == 2
        assert "First error occurred" in updated_task.errors
        assert "Second error occurred" in updated_task.errors
    
    def test_set_result(self, db_session):
        """Test setting task result"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Result Test",
            description="Testing result storage",
        )
        
        result_data = {
            "plan": {"steps": ["step1", "step2"]},
            "code": {"main.py": "print('hello')"},
            "execution_result": {"output": "hello", "exit_code": 0},
        }
        
        updated = manager.set_result(task.uuid, result_data)
        
        assert updated.status == TaskStatusEnum.COMPLETED
        assert updated.result == result_data
    
    def test_list_tasks(self, db_session):
        """Test listing tasks"""
        manager = DatabaseTaskManager(db=db_session)
        
        # Create multiple tasks
        manager.create_task(title="Task 1", description="First")
        manager.create_task(title="Task 2", description="Second")
        manager.create_task(title="Task 3", description="Third")
        
        tasks = manager.list_tasks()
        assert len(tasks) == 3
        
        # Test with limit
        tasks_limited = manager.list_tasks(limit=2)
        assert len(tasks_limited) == 2
    
    def test_list_tasks_with_filter(self, db_session):
        """Test listing tasks with status filter"""
        manager = DatabaseTaskManager(db=db_session)
        
        task1 = manager.create_task(title="Pending Task", description="Pending")
        task2 = manager.create_task(title="Completed Task", description="Done")
        manager.set_result(task2.uuid, {"result": "done"})
        
        # Filter by PENDING
        pending_tasks = manager.list_tasks(status_filter=TaskStatusEnum.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].title == "Pending Task"
        
        # Filter by COMPLETED
        completed_tasks = manager.list_tasks(status_filter=TaskStatusEnum.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].title == "Completed Task"
    
    def test_delete_task(self, db_session):
        """Test deleting a task"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Delete Me",
            description="This task will be deleted",
        )
        
        result = manager.delete_task(task.uuid)
        assert result is True
        
        # Verify deletion
        deleted_task = manager.get_task(task.uuid)
        assert deleted_task is None
    
    def test_delete_nonexistent_task(self, db_session):
        """Test deleting a non-existent task"""
        manager = DatabaseTaskManager(db=db_session)
        
        result = manager.delete_task("non-existent-uuid")
        assert result is False
    
    def test_cancel_task(self, db_session):
        """Test cancelling a task"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Cancel Test",
            description="Testing cancellation",
        )
        
        cancelled = manager.cancel_task(task.uuid, reason="User requested")
        
        assert cancelled.status == TaskStatusEnum.CANCELLED
        # Fetch fresh from DB to get updated JSON column
        fresh_task = db_session.query(TaskModel).filter(TaskModel.uuid == task.uuid).first()
        assert any("User requested" in err for err in fresh_task.errors)
    
    def test_cancel_completed_task_raises(self, db_session):
        """Test that cancelling a completed task raises an error"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Already Done",
            description="Cannot cancel",
        )
        manager.set_result(task.uuid, {"result": "done"})
        
        with pytest.raises(ValueError, match="Cannot cancel task"):
            manager.cancel_task(task.uuid)
    
    def test_task_relationships(self, db_session):
        """Test task-file relationships"""
        manager = DatabaseTaskManager(db=db_session)
        
        task = manager.create_task(
            title="Parent Task",
            description="With child files",
        )
        
        # Add files directly
        file1 = FileModel(
            uuid=str(uuid.uuid4()),
            task_uuid=task.uuid,
            filename="file1.py",
            filepath="/path/file1.py",
        )
        file2 = FileModel(
            uuid=str(uuid.uuid4()),
            task_uuid=task.uuid,
            filename="file2.py",
            filepath="/path/file2.py",
        )
        
        db_session.add_all([file1, file2])
        db_session.commit()
        
        # Verify relationship
        retrieved_task = manager.get_task(task.uuid)
        assert len(retrieved_task.files) == 2


# Fixture for database session
@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    from app.db.database import engine, Base, SessionLocal
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.rollback()
    session.close()
    
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
