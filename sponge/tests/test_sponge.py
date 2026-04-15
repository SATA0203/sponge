"""
Test suite for Sponge AI Code Generation System
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

# Import app components
from app.main import app
from app.agents import PlannerAgent, CoderAgent, ReviewerAgent
from app.tools.code_executor import CodeExecutor
from app.core.llm_service import LLMService
from langchain_core.language_models import FakeListLLM


class MockLLM:
    """Simple mock LLM for testing"""
    
    def __init__(self):
        self.responses = []
    
    def invoke(self, messages):
        """Return mock response"""
        from app.models import Plan, PlanStep, CodeResult, Review
        
        # Determine response type based on context
        if isinstance(messages, list) and len(messages) > 0:
            content = str(messages[0]) if hasattr(messages[0], 'content') else str(messages[0])
            
            if "plan" in content.lower() or "step" in content.lower():
                # Return a plan
                return Plan(steps=[PlanStep(description="Execute the task", code_template="print('result')")])
            elif "code" in content.lower() or "generate" in content.lower():
                # Return code
                return CodeResult(code="print('Hello from mock!')", language="python")
            elif "review" in content.lower():
                # Return review
                return Review(score=8, feedback="Good code", suggestions=["Add comments"])
        
        # Default response
        return Plan(steps=[PlanStep(description="Default step", code_template="pass")])


class TestAgents:
    """Test individual agent functionality"""
    
    @pytest.mark.asyncio
    async def test_planner_agent(self):
        """Test planner generates valid plan - integration via workflow"""
        # Test planner through the full workflow which handles the correct input format
        from app.workflow import WorkflowManager
        manager = WorkflowManager()
        result = await manager.execute("Simple test")
        
        assert result is not None
        plan = result.get("plan", {})
        steps = plan.get("steps", []) if isinstance(plan, dict) else getattr(plan, "steps", [])
        assert len(steps) > 0
        print(f"✓ Planner generated {len(steps)} steps via workflow")
    
    @pytest.mark.asyncio
    async def test_coder_agent(self):
        """Test coder generates executable code - integration via workflow"""
        # Test coder through the full workflow
        from app.workflow import WorkflowManager
        manager = WorkflowManager()
        result = await manager.execute("Print hello")
        
        assert result is not None
        code = result.get("code", "")
        assert code is not None and len(code) > 0
        code_preview = code[:50] if len(code) > 50 else code
        print(f"✓ Coder generated code: {code_preview}...")
    
    @pytest.mark.asyncio
    async def test_reviewer_agent(self):
        """Test reviewer evaluates code correctly - integration via workflow"""
        # Test reviewer through the full workflow
        from app.workflow import WorkflowManager
        manager = WorkflowManager()
        result = await manager.execute("Calculate 1+1")
        
        assert result is not None
        review = result.get("review_result", {})
        if isinstance(review, dict):
            score = review.get("score", 0)
        else:
            score = getattr(review, "score", 0)
        assert 0 <= score <= 10
        print(f"✓ Reviewer score: {score}/10")
    
    @pytest.mark.asyncio
    async def test_code_executor(self):
        """Test code executor runs Python code safely"""
        executor = CodeExecutor(timeout=5)
        
        code = "print('Hello from test!')"
        result = await executor.execute(code)
        
        assert result["success"] is True
        assert "Hello from test!" in result["output"]
        assert result["error"] is None
        print(f"✓ Executor output: {result['output'].strip()}")
    
    @pytest.mark.asyncio
    async def test_code_executor_timeout(self):
        """Test code executor handles timeout - SKIPPED (requires Docker)"""
        pytest.skip("Timeout test requires Docker sandbox for reliable testing")


class TestWorkflow:
    """Test integrated workflow"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete planner→coder→executor→reviewer flow"""
        from app.workflow import WorkflowManager
        
        manager = WorkflowManager()
        task_description = "Print the numbers 1 to 3"
        
        result = await manager.execute(task_description)
        
        assert result is not None
        assert result.get("status") == "completed"
        assert result.get("plan") is not None
        assert result.get("code") is not None
        assert result.get("execution_result") is not None
        assert result.get("review_result") is not None
        print(f"✓ End-to-end workflow completed successfully")
        print(f"  - Plan steps: {len(result['plan'].get('steps', []))}")
        print(f"  - Code length: {len(result['code'])} chars")
        exec_result = result['execution_result']
        print(f"  - Execution: {'Success' if exec_result.get('success') else 'Failed'}")
        review = result['review_result']
        print(f"  - Review score: {review.get('score', 0)}/10")


class TestAPI:
    """Test REST API endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self):
        """Test health check endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health/")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            print("✓ Health endpoint OK")
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "version" in data or "message" in data or "status" in data
            print(f"✓ Root endpoint OK: {data}")
    
    @pytest.mark.asyncio
    async def test_execute_task_endpoint(self):
        """Test task execution endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Use correct schema matching CreateTaskRequest
            payload = {
                "title": "Test Task",
                "description": "Say hi",
                "priority": 5,
                "tags": ["test"]
            }
            response = await ac.post("/api/v1/tasks/execute", json=payload)
            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()
            assert "id" in data or "task_id" in data
            assert data["status"] == "pending"
            task_id = data.get("id") or data.get("task_id")
            print(f"✓ Task execution endpoint OK (task_id: {task_id[:8]}...)")
    
    @pytest.mark.asyncio
    async def test_get_tasks_endpoint(self):
        """Test get tasks list endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/tasks/")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✓ Get tasks endpoint OK ({len(data)} tasks)")
    
    @pytest.mark.asyncio
    async def test_files_list_endpoint(self):
        """Test files list endpoint"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/files/")
            assert response.status_code == 200
            data = response.json()
            # Response can be dict with 'files' key or direct list
            assert isinstance(data, (list, dict))
            if isinstance(data, dict):
                assert "files" in data
            print(f"✓ Files list endpoint OK")


class TestDatabase:
    """Test database operations"""
    
    @pytest.mark.asyncio
    async def test_task_persistence(self):
        """Test tasks are persisted to database"""
        from app.db.task_manager import DatabaseTaskManager
        from app.schemas import TaskStatus
        from app.db.database import SessionLocal
        
        # Create a database session
        db = SessionLocal()
        try:
            db_manager = DatabaseTaskManager(db)
            
            # Create task (using actual API signature - synchronous method)
            task = db_manager.create_task(
                title="Test Task",
                description="Test persistence",
                priority="medium"
            )
            
            assert task.uuid is not None
            assert task.description == "Test persistence"
            
            # Retrieve task
            retrieved = db_manager.get_task(str(task.uuid))
            assert retrieved is not None
            assert retrieved.uuid == task.uuid
            
            # Update task status
            updated = db_manager.update_task_status(
                str(task.uuid), 
                TaskStatus.COMPLETED
            )
            assert updated.status == TaskStatus.COMPLETED.value
            
            # List tasks
            tasks = db_manager.list_tasks(limit=10)
            assert len(tasks) > 0
            
            print(f"✓ Database persistence OK (task_id: {task.uuid})")
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
