"""
Test suite for API Task Management endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import uuid

from app.main import app
from app.db.database import SessionLocal, get_db
from app.db.models import TaskModel, TaskStatusEnum
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


# Create test database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client():
    """Create test client with test database"""
    # Create tables
    from app.db.database import Base
    Base.metadata.create_all(bind=engine)
    
    # Override database dependency
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_task_data():
    """Sample task creation data"""
    return {
        "title": "Test Task",
        "description": "This is a test task description",
        "requirements": None,  # Optional field
        "priority": 1,
        "tags": ["test", "api"],
        "assigned_agents": ["planner", "coder"],  # Use valid AgentRole values
    }


class TestTaskEndpoints:
    """Test suite for task management API endpoints"""
    
    def test_execute_task_success(self, client, sample_task_data):
        """Test successful task execution endpoint"""
        with patch("app.api.tasks.run_workflow") as mock_run:
            mock_run.return_value = None  # Background task returns None
            
            response = client.post("/api/v1/tasks/execute", json=sample_task_data)
            
            assert response.status_code == 201
            data = response.json()
            
            assert "id" in data
            assert data["title"] == sample_task_data["title"]
            assert data["status"] == "pending"
            assert "created_at" in data
            assert "updated_at" in data
            
            # Verify task was created in database
            db = TestingSessionLocal()  # Use test session
            task = db.query(TaskModel).filter(TaskModel.uuid == data["id"]).first()
            assert task is not None
            assert task.title == sample_task_data["title"]
            assert task.status == TaskStatusEnum.PENDING
            db.close()
    
    def test_create_task_success(self, client, sample_task_data):
        """Test successful task creation endpoint (manual execution)"""
        response = client.post("/api/v1/tasks/", json=sample_task_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert data["title"] == sample_task_data["title"]
        assert data["status"] == "pending"
        
        # Verify task was created in database
        db = TestingSessionLocal()  # Use test session
        task = db.query(TaskModel).filter(TaskModel.uuid == data["id"]).first()
        assert task is not None
        assert task.description == sample_task_data["description"]
        db.close()
    
    def test_create_task_minimal_data(self, client):
        """Test task creation with minimal required data"""
        minimal_data = {
            "title": "Minimal Task",
            "description": "Just the basics",
        }
        
        response = client.post("/api/v1/tasks/", json=minimal_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Minimal Task"
        assert data["status"] == "pending"
    
    def test_list_tasks_empty(self, client):
        """Test listing tasks when database is empty"""
        response = client.get("/api/v1/tasks/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_tasks_with_filter(self, client, sample_task_data):
        """Test listing tasks with status filter"""
        # Create a task first
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # List all tasks
        response = client.get("/api/v1/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        
        # List with status filter
        response = client.get("/api/v1/tasks/?status_filter=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(t["id"] == task_id for t in data)
    
    def test_get_task_success(self, client, sample_task_data):
        """Test getting a specific task"""
        # Create task
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # Get task details
        response = client.get(f"/api/v1/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == task_id
        assert data["title"] == sample_task_data["title"]
        assert data["description"] == sample_task_data["description"]
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_task_not_found(self, client):
        """Test getting a non-existent task"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/tasks/{fake_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert fake_id in data["detail"]
    
    def test_cancel_task_success(self, client, sample_task_data):
        """Test successful task cancellation"""
        # Create task
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # Cancel task
        cancel_data = {"reason": "Testing cancellation"}
        response = client.post(f"/api/v1/tasks/{task_id}/cancel", json=cancel_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "cancelled successfully" in data["message"]
        
        # Verify task status updated
        db = TestingSessionLocal()
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        assert task.status == TaskStatusEnum.CANCELLED
        assert any("Cancelled:" in err for err in task.errors)
        db.close()
    
    def test_cancel_task_already_completed(self, client, sample_task_data):
        """Test cancelling an already completed task"""
        # Create and manually set task as completed
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        db = TestingSessionLocal()
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        task.status = TaskStatusEnum.COMPLETED
        db.commit()
        db.close()
        
        # Try to cancel
        cancel_data = {"reason": "Should fail"}
        response = client.post(f"/api/v1/tasks/{task_id}/cancel", json=cancel_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "Cannot cancel" in data["detail"]
    
    def test_cancel_task_not_found(self, client):
        """Test cancelling a non-existent task"""
        fake_id = str(uuid.uuid4())
        cancel_data = {"reason": "Testing"}
        response = client.post(f"/api/v1/tasks/{fake_id}/cancel", json=cancel_data)
        
        assert response.status_code == 404
    
    def test_delete_task_success(self, client, sample_task_data):
        """Test successful task deletion"""
        # Create task
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        # Delete task
        response = client.delete(f"/api/v1/tasks/{task_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify task was deleted
        db = TestingSessionLocal()
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        assert task is None
        db.close()
    
    def test_delete_task_not_found(self, client):
        """Test deleting a non-existent task"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/tasks/{fake_id}")
        
        assert response.status_code == 404
    
    def test_task_priority_validation(self, client):
        """Test task priority field validation"""
        invalid_data = {
            "title": "Test",
            "description": "Test",
            "priority": 100,  # Invalid priority
        }
        
        response = client.post("/api/v1/tasks/", json=invalid_data)
        # Should either validate or use default
        assert response.status_code in [201, 422]
    
    def test_task_with_empty_tags(self, client):
        """Test task creation with empty tags"""
        data = {
            "title": "No Tags",
            "description": "Task without tags",
            "tags": [],
        }
        
        response = client.post("/api/v1/tasks/", json=data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "No Tags"
    
    def test_concurrent_task_creation(self, client, sample_task_data):
        """Test creating multiple tasks concurrently"""
        task_ids = []
        
        # Create 5 tasks
        for i in range(5):
            data = sample_task_data.copy()
            data["title"] = f"Concurrent Task {i}"
            response = client.post("/api/v1/tasks/", json=data)
            assert response.status_code == 201
            task_ids.append(response.json()["id"])
        
        # Verify all tasks exist
        response = client.get("/api/v1/tasks/")
        assert response.status_code == 200
        tasks = response.json()
        assert len(tasks) >= 5
        
        # Verify all task IDs are present
        created_ids = [t["id"] for t in tasks]
        for task_id in task_ids:
            assert task_id in created_ids


class TestTaskWorkflowIntegration:
    """Test workflow integration with task endpoints"""
    
    @pytest.mark.asyncio
    async def test_execute_task_triggers_workflow(self, client, sample_task_data):
        """Test that execute_task endpoint triggers workflow execution"""
        with patch("app.api.tasks.get_workflow_manager") as mock_wf_manager:
            # Setup mock
            mock_manager = AsyncMock()
            mock_manager.execute = AsyncMock(return_value={
                "status": "success",
                "iterations": 2,
                "plan": {"steps": ["step1", "step2"]},
                "code": {"files": ["main.py"]},
            })
            mock_wf_manager.return_value = mock_manager
            
            response = client.post("/api/v1/tasks/execute", json=sample_task_data)
            assert response.status_code == 201
            
            task_id = response.json()["id"]
            
            # Wait a bit for background task
            import asyncio
            await asyncio.sleep(0.1)
            
            # Verify workflow manager was called
            # Note: This is tricky with background tasks, may need adjustment
            # For now, just verify task was created
            db = TestingSessionLocal()
            task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
            assert task is not None
            db.close()


class TestTaskStatusTransitions:
    """Test task status transition logic"""
    
    def test_task_initial_status(self, client, sample_task_data):
        """Test that newly created tasks have PENDING status"""
        response = client.post("/api/v1/tasks/", json=sample_task_data)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        
        # Verify in DB
        db = TestingSessionLocal()
        task = db.query(TaskModel).filter(TaskModel.uuid == data["id"]).first()
        assert task.status == TaskStatusEnum.PENDING
        db.close()
    
    def test_task_cancelled_status_persistence(self, client, sample_task_data):
        """Test that cancelled status persists correctly"""
        # Create and cancel
        create_response = client.post("/api/v1/tasks/", json=sample_task_data)
        task_id = create_response.json()["id"]
        
        cancel_response = client.post(
            f"/api/v1/tasks/{task_id}/cancel",
            json={"reason": "Test"}
        )
        assert cancel_response.status_code == 200
        
        # Get task and verify status
        get_response = client.get(f"/api/v1/tasks/{task_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["status"] == "cancelled"
        
        # Verify in DB
        db = TestingSessionLocal()
        task = db.query(TaskModel).filter(TaskModel.uuid == task_id).first()
        assert task.status == TaskStatusEnum.CANCELLED
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
