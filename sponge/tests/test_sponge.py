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
        """Test planner generates valid plan"""
        llm = MockLLM()
        planner = PlannerAgent(llm)
        
        task = "Print hello world"
        plan = await planner.plan(task)
        
        assert plan is not None
        assert len(plan.steps) > 0
        assert all(hasattr(step, 'description') for step in plan.steps)
        print(f"✓ Planner generated {len(plan.steps)} steps")
    
    @pytest.mark.asyncio
    async def test_coder_agent(self):
        """Test coder generates executable code"""
        llm = MockLLM()
        coder = CoderAgent(llm)
        
        task = "Calculate 2 + 2"
        result = await coder.generate_code(task, context="")
        
        assert result is not None
        assert result.code is not None
        assert len(result.code) > 0
        print(f"✓ Coder generated code: {result.code[:50]}...")
    
    @pytest.mark.asyncio
    async def test_reviewer_agent(self):
        """Test reviewer evaluates code correctly"""
        llm = MockLLM()
        reviewer = ReviewerAgent(llm)
        
        code = "print('hello')"
        review = await reviewer.review(code, "Print hello")
        
        assert review is not None
        assert 0 <= review.score <= 10
        print(f"✓ Reviewer score: {review.score}/10")
    
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
        """Test code executor handles timeout"""
        executor = CodeExecutor(timeout=2)
        
        # Sleep longer than timeout
        code = "import time; time.sleep(10)"
        result = await executor.execute(code)
        
        assert result["success"] is False
        assert result["error"] is not None
        print(f"✓ Timeout handled correctly: {result['error']}")


class TestWorkflow:
    """Test integrated workflow"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Test complete planner→coder→executor→reviewer flow"""
        from app.workflow.manager import WorkflowManager
        
        manager = WorkflowManager()
        task_description = "Print the numbers 1 to 3"
        
        result = await manager.execute(task_description)
        
        assert result is not None
        assert result.status == "completed"
        assert result.plan is not None
        assert result.code is not None
        assert result.execution_result is not None
        assert result.review is not None
        print(f"✓ End-to-end workflow completed successfully")
        print(f"  - Plan steps: {len(result.plan.steps)}")
        print(f"  - Code length: {len(result.code)} chars")
        print(f"  - Execution: {'Success' if result.execution_result.success else 'Failed'}")
        print(f"  - Review score: {result.review.score}/10")


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
            payload = {"task": "Say hi", "mode": "sync"}
            response = await ac.post("/api/v1/tasks/execute", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "task_id" in data
            assert data["status"] in ["created", "completed"]
            print(f"✓ Task execution endpoint OK (task_id: {data['task_id'][:8]}...)")
    
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
        from app.models import TaskStatus
        
        db_manager = DatabaseTaskManager()
        
        # Create task
        task = await db_manager.create_task(
            description="Test persistence",
            status=TaskStatus.PENDING
        )
        
        assert task.id is not None
        assert task.description == "Test persistence"
        assert task.status == TaskStatus.PENDING
        
        # Retrieve task
        retrieved = await db_manager.get_task(task.id)
        assert retrieved is not None
        assert retrieved.id == task.id
        
        # Update task
        updated = await db_manager.update_task_status(
            task.id, 
            TaskStatus.COMPLETED
        )
        assert updated.status == TaskStatus.COMPLETED
        
        # List tasks
        tasks = await db_manager.list_tasks(limit=10)
        assert len(tasks) > 0
        
        print(f"✓ Database persistence OK (task_id: {task.id})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
