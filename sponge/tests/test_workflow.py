"""
Unit tests for OrchestratorWorkflow with retry mechanism
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.workflow.orchestrator_workflow import (
    OrchestratorWorkflow,
    WorkflowExecutionError,
    create_retry_decorator,
)


class TestRetryDecorator:
    """Tests for the retry decorator utility"""
    
    def test_create_retry_decorator(self):
        """Test creating a retry decorator"""
        decorator = create_retry_decorator(
            max_attempts=3,
            min_wait=0.1,
            max_wait=1.0,
        )
        assert decorator is not None
    
    @pytest.mark.asyncio
    async def test_retry_on_success(self):
        """Test that successful operations don't retry"""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, min_wait=0.01, max_wait=0.1)
        async def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_operation()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_then_success(self):
        """Test retry succeeds after initial failures"""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, min_wait=0.01, max_wait=0.1)
        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = await flaky_operation()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test that all retries are exhausted on persistent failure"""
        call_count = 0
        
        @create_retry_decorator(max_attempts=3, min_wait=0.01, max_wait=0.1)
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError):
            await failing_operation()
        
        assert call_count == 3


class TestOrchestratorWorkflow:
    """Tests for OrchestratorWorkflow class"""
    
    def test_init(self):
        """Test workflow initialization"""
        workflow = OrchestratorWorkflow(
            task_id="test-123",
            language="python",
            max_iterations=5,
        )
        
        assert workflow.task_id == "test-123"
        assert workflow.language == "python"
        assert workflow.max_iterations == 5
        assert workflow.current_iteration == 0
        assert workflow.subtasks == []
        assert workflow.completed_subtasks == []
    
    def test_get_result(self):
        """Test getting workflow state"""
        workflow = OrchestratorWorkflow(task_id="test-456")
        
        result = workflow.get_result()
        
        assert result["task_id"] == "test-456"
        assert result["status"] == "running"
        assert result["completed_subtasks"] == 0
        assert result["total_subtasks"] == 0
    
    @pytest.mark.asyncio
    async def test_retry_operation_success(self):
        """Test _retry_operation with immediate success"""
        workflow = OrchestratorWorkflow(task_id="test-789")
        
        async def successful_op():
            return {"status": "ok"}
        
        result = await workflow._retry_operation(
            successful_op,
            operation_name="test_op",
            max_attempts=3,
        )
        
        assert result["status"] == "ok"
    
    @pytest.mark.asyncio
    async def test_retry_operation_with_retries(self):
        """Test _retry_operation succeeds after retries"""
        workflow = OrchestratorWorkflow(task_id="test-retry")
        
        call_count = 0
        
        async def flaky_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Temporary timeout")
            return {"status": "ok"}
        
        result = await workflow._retry_operation(
            flaky_op,
            operation_name="flaky_test",
            max_attempts=3,
            min_wait=0.01,
            max_wait=0.1,
        )
        
        assert result["status"] == "ok"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_operation_exhausted(self):
        """Test _retry_operation raises after exhausting retries"""
        workflow = OrchestratorWorkflow(task_id="test-fail")
        
        async def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(WorkflowExecutionError):
            await workflow._retry_operation(
                always_fails,
                operation_name="failing_test",
                max_attempts=3,
                min_wait=0.01,
                max_wait=0.1,
            )
    
    @pytest.mark.asyncio
    async def test_extract_current_artifact_empty(self):
        """Test artifact extraction with no completed subtasks"""
        workflow = OrchestratorWorkflow(task_id="test-artifact")
        
        artifact = workflow._extract_current_artifact()
        assert artifact == ""
    
    @pytest.mark.asyncio
    async def test_extract_current_artifact_with_results(self):
        """Test artifact extraction with completed subtasks"""
        workflow = OrchestratorWorkflow(task_id="test-artifact")
        
        # Add mock completed subtasks
        workflow.completed_subtasks = [
            {
                'subtask_id': 'task-1',
                'result': {
                    'artifacts': {
                        'main.py': 'print("hello")',
                        'utils.py': 'def helper(): pass',
                    }
                }
            }
        ]
        
        artifact = workflow._extract_current_artifact()
        
        assert '# main.py' in artifact
        assert 'print("hello")' in artifact
        assert '# utils.py' in artifact
        assert 'def helper(): pass' in artifact
    
    @pytest.mark.asyncio
    async def test_extract_requirements_from_spec(self):
        """Test requirements extraction from task spec"""
        workflow = OrchestratorWorkflow(task_id="test-req")
        
        # Mock the orchestrator's task_progress
        mock_spec = {
            'goal': 'Build a calculator',
            'constraints': ['Use Python', 'No external libraries'],
        }
        
        with patch.object(
            workflow.orchestrator.task_progress,
            'read_spec',
            return_value=mock_spec
        ):
            requirements = workflow._extract_requirements()
            
            assert 'Build a calculator' in requirements
            assert 'Use Python' in requirements
            assert 'No external libraries' in requirements


class TestWorkflowExecutionError:
    """Tests for WorkflowExecutionError exception"""
    
    def test_exception_creation(self):
        """Test creating WorkflowExecutionError"""
        error = WorkflowExecutionError("Test error message")
        assert str(error) == "Test error message"
    
    def test_exception_with_cause(self):
        """Test WorkflowExecutionError with underlying cause"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise WorkflowExecutionError("Workflow failed") from e
        except WorkflowExecutionError as e:
            assert str(e) == "Workflow failed"
            assert isinstance(e.__cause__, ValueError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
