"""
Celery Tasks for Sponge Code Agent
"""

from typing import Any, Dict
from loguru import logger
from app.celery_app import celery_app
from app.workflow import get_workflow_manager


@celery_app.task(
    bind=True,
    name="app.workflow.tasks.execute_workflow_task",
    track_started=True,
    time_limit=3600,
    soft_time_limit=3300,
)
async def execute_workflow_task(
    self,
    task_id: str,
    description: str,
    language: str = "python",
    max_iterations: int = 3,
) -> Dict[str, Any]:
    """
    Execute the multi-agent workflow as a Celery task
    
    Args:
        task_id: Unique task identifier
        description: Task description
        language: Programming language (default: python)
        max_iterations: Maximum iteration count for improvements
        
    Returns:
        Workflow execution results
    """
    try:
        logger.info(f"[Celery] Starting workflow task {task_id}")
        
        # Update task state to STARTED
        self.update_state(state="STARTED", meta={"progress": 0})
        
        # Get workflow manager
        workflow_manager = get_workflow_manager()
        
        # Execute workflow
        result = await workflow_manager.execute(
            description=description,
            language=language,
            task_id=task_id,
            max_iterations=max_iterations,
        )
        
        # Update progress
        self.update_state(state="STARTED", meta={"progress": 100})
        
        logger.info(f"[Celery] Workflow task {task_id} completed")
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"[Celery] Workflow task {task_id} failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="app.workflow.tasks.cancel_workflow_task",
    time_limit=30,
)
def cancel_workflow_task(self, task_id: str) -> Dict[str, Any]:
    """
    Cancel a running workflow task
    
    Args:
        task_id: Task identifier to cancel
        
    Returns:
        Cancellation status
    """
    try:
        logger.info(f"[Celery] Cancelling workflow task {task_id}")
        
        # Revoke the task
        self.revoke(terminate=True, signal="SIGTERM")
        
        logger.info(f"[Celery] Workflow task {task_id} cancelled")
        
        return {
            "status": "cancelled",
            "task_id": task_id,
        }
        
    except Exception as e:
        logger.error(f"[Celery] Failed to cancel task {task_id}: {e}")
        raise
