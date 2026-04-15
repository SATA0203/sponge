"""
Orchestrator-based Workflow Engine

This module implements the new workflow engine based on the orchestrator-worker pattern,
replacing the old流水线 (assembly line) approach.

Key features:
- Single OrchestratorAgent maintains complete task intent
- WorkerAgents execute sub-tasks in parallel when possible
- ValidatorAgent provides adversarial validation (problems only)
- TaskProgress maintains external state for reasoning continuity
- No role-based handoffs - all results flow back to orchestrator
"""

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.core.llm_service import get_llm
from app.core.task_progress import TaskProgress
from app.orchestrator.orchestrator_agent import OrchestratorAgent, WorkerAgent
from app.orchestrator.validator_agent import ValidatorAgent


class OrchestratorWorkflow:
    """
    New workflow engine using orchestrator-worker pattern.
    
    This replaces the old WorkflowManager with a fundamentally different approach:
    - Old: Planner -> Coder -> Executor -> Reviewer -> Tester (流水线)
    - New: Orchestrator holds intent, delegates to workers, synthesizes results
    """
    
    def __init__(self, enable_validation: bool = True):
        """
        Initialize orchestrator workflow
        
        Args:
            enable_validation: Whether to include adversarial validation
        """
        self.enable_validation = enable_validation
        self.llm = get_llm()
        self.orchestrator: Optional[OrchestratorAgent] = None
        self.task_progress: Optional[TaskProgress] = None
        logger.info(f"OrchestratorWorkflow initialized (validation={'enabled' if enable_validation else 'disabled'})")
    
    async def execute(
        self,
        goal: str,
        constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute a task using orchestrator-worker pattern
        
        Args:
            goal: Primary task objective
            constraints: Optional constraints
            metadata: Optional metadata (language, dependencies, etc.)
            task_id: Optional task ID (generated if not provided)
            max_iterations: Maximum refinement iterations
            
        Returns:
            Final result with full context
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # Initialize task progress (external state)
        self.task_progress = TaskProgress(task_id)
        self.task_progress.write_spec(
            goal=goal,
            constraints=constraints or [],
            metadata=metadata or {},
        )
        
        # Initialize orchestrator with task progress
        self.orchestrator = OrchestratorAgent(
            llm=self.llm,
            task_progress=self.task_progress,
        )
        
        logger.info(f"Starting orchestrator workflow for task {task_id}: {goal[:50]}...")
        
        try:
            # Phase 1: Planning
            logger.info("[Phase 1] Planning")
            self.task_progress.update_current_status(
                current_step="Planning",
                status="in_progress",
                details={"phase": 1},
                last_updated_by="orchestrator_workflow",
            )
            
            plan_result = await self.orchestrator.execute({
                "task_id": task_id,
                "goal": goal,
                "constraints": constraints or [],
                "metadata": metadata or {},
                "current_phase": "planning",
            })
            
            # Extract subtasks from plan
            subtasks = plan_result.get("subtasks", [])
            
            # Phase 2: Delegate and Execute (parallel when possible)
            logger.info(f"[Phase 2] Executing {len(subtasks)} subtasks")
            self.task_progress.update_current_status(
                current_step="Executing subtasks",
                status="in_progress",
                details={"phase": 2, "subtask_count": len(subtasks)},
                last_updated_by="orchestrator_workflow",
            )
            
            worker_results = {}
            for subtask in subtasks:
                subtask_name = subtask.get("name", f"subtask_{len(worker_results)}")
                subtask_desc = subtask.get("description", "")
                
                # Create worker for this subtask
                worker = WorkerAgent(
                    llm=self.llm,
                    name=subtask_name,
                    task_progress=self.task_progress,
                )
                
                # Execute with full context
                result = await worker.execute({
                    "task_description": subtask_desc,
                    "parent_context": {"plan": plan_result},
                    "full_task_context": self.task_progress.get_full_context_for_agent(),
                })
                
                worker_results[subtask_name] = result
            
            # Phase 3: Synthesis
            logger.info("[Phase 3] Synthesizing results")
            self.task_progress.update_current_status(
                current_step="Synthesizing",
                status="in_progress",
                details={"phase": 3},
                last_updated_by="orchestrator_workflow",
            )
            
            synthesis_result = await self.orchestrator.synthesize_results(worker_results)
            
            # Phase 4: Validation (if enabled)
            if self.enable_validation:
                logger.info("[Phase 4] Validating")
                self.task_progress.update_current_status(
                    current_step="Validating",
                    status="in_progress",
                    details={"phase": 4},
                    last_updated_by="orchestrator_workflow",
                )
                
                validator = ValidatorAgent(
                    llm=self.llm,
                    task_progress=self.task_progress,
                )
                
                # Get artifact to validate (from synthesis or worker results)
                artifact = synthesis_result.get("synthesis", str(worker_results))
                
                validation_result = await validator.execute({
                    "artifact": artifact,
                    "task_goal": goal,
                    "completed_steps": [s.get("description") for s in self.task_progress.get_completed_steps()],
                })
                
                # If validation failed and we have iterations left, loop back
                if not validation_result.get("passed", False):
                    iteration = 0
                    while (
                        not validation_result.get("passed", False) 
                        and iteration < max_iterations
                    ):
                        iteration += 1
                        logger.info(f"[Iteration {iteration}] Addressing validation issues")
                        
                        self.task_progress.update_current_status(
                            current_step=f"Iteration {iteration}: Addressing issues",
                            status="in_progress",
                            details={"iteration": iteration},
                            last_updated_by="orchestrator_workflow",
                        )
                        
                        # Ask orchestrator to address issues
                        improvement_result = await self.orchestrator.execute({
                            "task_id": task_id,
                            "goal": goal,
                            "current_phase": "executing",
                            "worker_results": {"validation": validation_result},
                        })
                        
                        # Re-validate
                        new_artifact = improvement_result.get("synthesis", str(improvement_result))
                        validation_result = await validator.execute({
                            "artifact": new_artifact,
                            "task_goal": goal,
                            "completed_steps": [s.get("description") for s in self.task_progress.get_completed_steps()],
                        })
            
            # Final status
            final_result = {
                "task_id": task_id,
                "status": "completed",
                "goal": goal,
                "plan": plan_result,
                "worker_results": worker_results,
                "synthesis": synthesis_result,
                "validation": validation_result if self.enable_validation else None,
                "iterations": max_iterations,
                "state_files": {
                    "spec": str(self.task_progress.spec_file),
                    "progress": str(self.task_progress.progress_file),
                    "history": str(self.task_progress.history_file),
                },
            }
            
            self.task_progress.update_current_status(
                current_step="Complete",
                status="completed",
                details={"result": "success"},
                last_updated_by="orchestrator_workflow",
            )
            
            logger.info(f"Orchestrator workflow completed for task {task_id}")
            return final_result
            
        except Exception as e:
            logger.error(f"Orchestrator workflow failed: {e}")
            
            if self.task_progress:
                self.task_progress.add_known_issue(
                    issue=f"Workflow failed: {str(e)}",
                    severity="critical",
                )
                self.task_progress.update_current_status(
                    current_step="Failed",
                    status="failed",
                    details={"error": str(e)},
                    last_updated_by="orchestrator_workflow",
                )
            
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(e),
                "goal": goal,
            }
    
    def get_task_progress(self) -> Optional[TaskProgress]:
        """Get the task progress manager"""
        return self.task_progress
    
    def get_full_context(self) -> str:
        """Get the full task context string"""
        if not self.task_progress:
            return "No task in progress"
        return self.task_progress.get_full_context_for_agent()


# Factory functions
def create_orchestrator_workflow(enable_validation: bool = True) -> OrchestratorWorkflow:
    """Create a new orchestrator workflow instance"""
    return OrchestratorWorkflow(enable_validation=enable_validation)


# Singleton (optional, for backward compatibility)
_workflow_instance: Optional[OrchestratorWorkflow] = None

def get_orchestrator_workflow(enable_validation: bool = True) -> OrchestratorWorkflow:
    """Get or create orchestrator workflow singleton"""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = OrchestratorWorkflow(enable_validation=enable_validation)
    return _workflow_instance
