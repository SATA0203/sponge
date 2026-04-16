"""
Orchestrator-Worker Workflow Engine with Retry Mechanism

This module implements the new workflow engine based on the orchestrator-worker pattern.
It replaces the old linear pipeline (Planner -> Coder -> Reviewer -> Tester) with:
- Orchestrator holds complete task intent
- Workers execute independent sub-tasks in parallel when possible
- Validator provides adversarial feedback
- All state is externalized for continuity
- Automatic retry mechanism for transient failures

Key differences from old workflow:
1. No fixed role pipeline - dynamic task decomposition
2. Results flow back to Orchestrator, not to next agent
3. External state files maintain continuity across sessions
4. Validator only finds problems, doesn't take ownership
5. Automatic retries with exponential backoff for transient errors
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from datetime import datetime
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)

from app.core.llm_service import get_llm
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.worker_agent import WorkerAgent
from app.agents.validator_agent import ValidatorAgent

# Type variable for generic retry decorator
T = TypeVar('T')


def create_retry_decorator(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 60.0,
    exceptions: tuple = (Exception,),
):
    """
    Create a retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        exceptions: Tuple of exception types to retry on
    
    Returns:
        A retry decorator
    """
    import logging
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
        reraise=True,
    )


class WorkflowExecutionError(Exception):
    """Custom exception for workflow execution failures"""
    pass


class OrchestratorWorkflow:
    """
    Main workflow engine implementing orchestrator-worker pattern.
    
    Usage:
        workflow = OrchestratorWorkflow(task_id="task-123")
        await workflow.initialize(description="Build a calculator app")
        await workflow.run()
        result = workflow.get_result()
    """
    
    def __init__(
        self,
        task_id: str,
        language: str = "python",
        workspace_root: Optional[str] = None,
        max_iterations: int = 5,
    ):
        self.task_id = task_id
        self.language = language
        self.workspace_root = workspace_root
        self.max_iterations = max_iterations
        
        # Initialize agents
        llm = get_llm()
        self.orchestrator = OrchestratorAgent(
            llm=llm,
            task_id=task_id,
            workspace_root=workspace_root,
        )
        self.validator = ValidatorAgent(llm=llm)
        
        # Track execution state
        self.current_iteration = 0
        self.subtasks: List[Dict[str, Any]] = []
        self.completed_subtasks: List[Dict[str, Any]] = []
        self.validation_issues: List[Dict[str, Any]] = []
        
        logger.info(f"[Workflow] Initialized OrchestratorWorkflow for task {task_id}")

    async def initialize(
        self,
        description: str,
        constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initialize the workflow with task specification"""
        logger.info(f"[Workflow] Initializing task: {description[:100]}...")
        
        result = await self.orchestrator.initialize_task(
            description=description,
            language=self.language,
            constraints=constraints,
            metadata=metadata,
        )
        
        logger.info("[Workflow] Task initialized successfully")
        return result

    async def run(self) -> Dict[str, Any]:
        """
        Execute the complete workflow with retry mechanism.
        
        Returns final synthesized result.
        """
        logger.info(f"[Workflow] Starting execution (max iterations: {self.max_iterations})")
        
        try:
            # Phase 1: Analyze and decompose (with retry)
            logger.info("[Workflow] Phase 1: Analysis and decomposition")
            decomposition = await self._retry_operation(
                self.orchestrator.analyze_and_decompose,
                operation_name="analyze_and_decompose",
                max_attempts=3,
            )
            
            self.subtasks = decomposition.get('subtasks', [])
            if not self.subtasks:
                logger.warning("[Workflow] No subtasks generated - attempting synthesis anyway")
                return await self._synthesize_final_result()
            
            logger.info(f"[Workflow] Decomposed into {len(self.subtasks)} subtasks")
            
            # Phase 2: Execute subtasks (with parallelization where possible)
            logger.info("[Workflow] Phase 2: Executing subtasks")
            await self._execute_subtasks(decomposition)
            
            # Phase 3: Validate results (with retry)
            logger.info("[Workflow] Phase 3: Validation")
            validation_result = await self._retry_operation(
                self._validate_results,
                operation_name="validate_results",
                max_attempts=2,
            )
            
            if not validation_result.get('passed', False):
                logger.warning("[Workflow] Validation failed - entering fix loop")
                
                # Phase 4: Fix iteration loop
                await self._fix_iteration_loop(validation_result)
            
            # Phase 5: Synthesize final result (with retry)
            logger.info("[Workflow] Phase 4: Synthesis")
            return await self._retry_operation(
                self._synthesize_final_result,
                operation_name="synthesize_final_result",
                max_attempts=2,
            )
            
        except Exception as e:
            logger.error(f"[Workflow] Execution failed after retries: {e}")
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e
    
    async def _retry_operation(
        self,
        operation: Callable,
        operation_name: str,
        max_attempts: int = 3,
        min_wait: float = 1.0,
        max_wait: float = 30.0,
    ) -> Any:
        """
        Execute an operation with automatic retry on transient failures.
        
        Args:
            operation: Async callable to execute
            operation_name: Name of the operation for logging
            max_attempts: Maximum number of retry attempts
            min_wait: Minimum wait time between retries (seconds)
            max_wait: Maximum wait time between retries (seconds)
        
        Returns:
            Result of the operation
        
        Raises:
            WorkflowExecutionError: If all retry attempts fail
        """
        last_exception: Optional[Exception] = None
        
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"[Workflow] Executing {operation_name} (attempt {attempt}/{max_attempts})")
                
                if asyncio.iscoroutinefunction(operation):
                    result = await operation()
                else:
                    result = operation()
                
                logger.info(f"[Workflow] {operation_name} completed successfully")
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(
                    f"[Workflow] {operation_name} timed out (attempt {attempt}/{max_attempts}): {e}"
                )
                if attempt < max_attempts:
                    wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                    logger.info(f"[Workflow] Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"[Workflow] {operation_name} failed (attempt {attempt}/{max_attempts}): {e}"
                )
                if attempt < max_attempts:
                    wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                    logger.info(f"[Workflow] Retrying in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    break
        
        error_msg = f"{operation_name} failed after {max_attempts} attempts"
        logger.error(f"[Workflow] {error_msg}: {last_exception}")
        raise WorkflowExecutionError(error_msg) from last_exception

    async def _execute_subtasks(self, decomposition: Dict[str, Any]):
        """Execute all subtasks with parallelization where possible"""
        
        parallel_groups = decomposition.get('parallel_groups', [])
        execution_order = decomposition.get('execution_order', [])
        
        if parallel_groups:
            # Execute parallel groups
            for group_idx, group in enumerate(parallel_groups):
                logger.info(f"[Workflow] Executing parallel group {group_idx + 1}/{len(parallel_groups)}")
                await self._execute_parallel_group(group)
        elif execution_order:
            # Execute sequentially
            for subtask_id in execution_order:
                subtask = next((st for st in self.subtasks if st.get('subtask_id') == subtask_id), None)
                if subtask:
                    await self._execute_single_subtask(subtask)
        else:
            # Fallback: execute all sequentially
            for subtask in self.subtasks:
                await self._execute_single_subtask(subtask)

    async def _execute_parallel_group(self, subtask_ids: List[str]):
        """Execute a group of subtasks in parallel"""
        logger.info(f"[Workflow] Executing parallel group with {len(subtask_ids)} subtasks")
        
        # Get subtask objects
        subtasks = [
            st for st in self.subtasks
            if st.get('subtask_id') in subtask_ids
        ]
        
        # Execute in parallel
        tasks = [
            self._execute_single_subtask(subtask)
            for subtask in subtasks
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for subtask, result in zip(subtasks, results):
            if isinstance(result, Exception):
                logger.error(f"[Workflow] Subtask {subtask.get('subtask_id')} failed: {result}")
                self.completed_subtasks.append({
                    **subtask,
                    'status': 'failed',
                    'error': str(result),
                })
            else:
                self.completed_subtasks.append({
                    **subtask,
                    'status': 'completed',
                    'result': result,
                })

    async def _execute_single_subtask(self, subtask: Dict[str, Any]):
        """Execute a single subtask"""
        subtask_id = subtask.get('subtask_id', 'unknown')
        description = subtask.get('description', '')
        subtask_type = subtask.get('type', 'general')
        
        logger.info(f"[Workflow] Executing subtask {subtask_id}: {description[:50]}...")
        
        # Create worker for this subtask type
        worker = WorkerAgent(
            llm=get_llm(),
            task_type=subtask_type,
            name=f"Worker-{subtask_id}",
        )
        
        # Build context from current state
        context = self.orchestrator._build_full_context()
        
        # Execute
        result = await worker.execute({
            "task_description": description,
            "context": context,
            "constraints": subtask.get('constraints', []),
            "expected_output": f"Complete implementation for: {description}",
        })
        
        # Record completion
        self.completed_subtasks.append({
            **subtask,
            'status': 'completed',
            'result': result,
        })
        
        logger.info(f"[Workflow] Subtask {subtask_id} completed")
        return result

    async def _validate_results(self) -> Dict[str, Any]:
        """Validate all completed work"""
        logger.info("[Workflow] Validating completed work...")
        
        # Get full context
        context = self.orchestrator._build_full_context()
        
        # Extract current artifact (code or other output)
        # This is simplified - in practice would extract from completed subtasks
        current_artifact = self._extract_current_artifact()
        requirements = self._extract_requirements()
        
        if not current_artifact:
            logger.warning("[Workflow] No artifact found to validate")
            return {"passed": True, "issues": []}
        
        # Run validation
        validation_result = await self.validator.validate(
            artifact=current_artifact,
            artifact_type="code",
            requirements=requirements,
            context={
                "known_issues": self.orchestrator.task_progress.get_known_issues(),
            },
        )
        
        if not validation_result.get('passed', False):
            self.validation_issues.extend(validation_result.get('issues', []))
        
        return validation_result

    async def _fix_iteration_loop(self, initial_validation: Dict[str, Any]):
        """Iterative fix loop based on validation feedback"""
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            
            logger.info(f"[Workflow] Fix iteration {self.current_iteration}/{self.max_iterations}")
            
            # Handle validation feedback
            action_plan = await self.orchestrator.handle_validation_feedback(initial_validation)
            
            if action_plan.get('action') != 'fix_required':
                logger.info("[Workflow] No fixes required - exiting loop")
                break
            
            # Create fix subtasks
            critical_count = action_plan.get('critical_count', 0)
            if critical_count == 0:
                logger.info("[Workflow] No critical issues - proceeding")
                break
            
            # Execute fixes
            suggested_fixes = action_plan.get('suggested_fixes', [])
            for idx, fix_description in enumerate(suggested_fixes[:3]):  # Limit fixes per iteration
                fix_subtask = {
                    'subtask_id': f'FIX-{self.current_iteration}-{idx}',
                    'description': fix_description,
                    'type': 'implementation',
                    'dependencies': [],
                }
                await self._execute_single_subtask(fix_subtask)
            
            # Re-validate
            initial_validation = await self._validate_results()
            
            if initial_validation.get('passed', False):
                logger.info("[Workflow] Validation passed after fixes")
                break
        
        if self.current_iteration >= self.max_iterations:
            logger.warning(f"[Workflow] Reached max iterations ({self.max_iterations})")

    async def _synthesize_final_result(self) -> Dict[str, Any]:
        """Synthesize all work into final result"""
        logger.info("[Workflow] Synthesizing final result...")
        
        synthesis = await self.orchestrator.synthesize_results()
        
        logger.info("[Workflow] Synthesis complete")
        return {
            "status": "complete",
            "task_id": self.task_id,
            "synthesis": synthesis,
            "completed_subtasks": len(self.completed_subtasks),
            "validation_issues": len(self.validation_issues),
            "iterations": self.current_iteration,
        }

    def _extract_current_artifact(self) -> str:
        """Extract current code/artifact from completed subtasks"""
        # Simplified extraction - would be more sophisticated in production
        artifacts = []
        for subtask in self.completed_subtasks:
            result = subtask.get('result', {})
            if isinstance(result, dict):
                artifact_list = result.get('artifacts', {})
                for key, value in artifact_list.items():
                    artifacts.append(f"# {key}\n{value}")
        
        return "\n\n".join(artifacts) if artifacts else ""

    def _extract_requirements(self) -> str:
        """Extract requirements from task spec"""
        spec = self.orchestrator.task_progress.read_spec()
        if spec:
            goal = spec.get('goal', '')
            constraints = spec.get('constraints', [])
            return f"{goal}\n\nConstraints:\n" + "\n".join(f"- {c}" for c in constraints)
        return ""

    def get_result(self) -> Dict[str, Any]:
        """Get current workflow result"""
        return {
            "task_id": self.task_id,
            "status": "running" if self.current_iteration < self.max_iterations else "complete",
            "completed_subtasks": len(self.completed_subtasks),
            "total_subtasks": len(self.subtasks),
            "validation_issues": len(self.validation_issues),
            "iterations": self.current_iteration,
        }

    def get_state_file_path(self) -> str:
        """Get path to external state files"""
        return str(self.orchestrator.task_progress.workspace_root)


async def run_workflow(
    task_id: str,
    description: str,
    language: str = "python",
    constraints: Optional[List[str]] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to run a complete workflow
    
    Args:
        task_id: Unique task identifier
        description: Task description
        language: Target programming language
        constraints: Optional constraints
        workspace_root: Root directory for state files
        
    Returns:
        Final workflow result
    """
    workflow = OrchestratorWorkflow(
        task_id=task_id,
        language=language,
        workspace_root=workspace_root,
    )
    
    await workflow.initialize(
        description=description,
        constraints=constraints,
    )
    
    return await workflow.run()
