# Celery Tasks for Sponge

"""
Celery tasks for asynchronous workflow execution
"""

from typing import Dict, Any, Optional
from loguru import logger

from app.celery_app import celery_app
from app.workflow import create_workflow
from app.db.task_manager import DatabaseTaskManager
from app.db.models import TaskStatusEnum


@celery_app.task(bind=True, max_retries=3)
def execute_workflow_task(
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
    enable_testing: bool = True,
) -> Dict[str, Any]:
    """
    Execute a multi-agent workflow as a Celery task

    Args:
        task_id: Unique task identifier
        description: Task description
        language: Programming language
        max_iterations: Maximum refinement iterations
        enable_testing: Whether to include testing node

    Returns:
        Workflow execution results
    """
    db_manager = DatabaseTaskManager()
    
    try:
        # Update task status to planning
        db_manager.update_status(task_id, TaskStatusEnum.PLANNING)
        logger.info(f"[Celery] Starting workflow for task {task_id}")

        # Create and execute workflow
        workflow = create_workflow(enable_testing=enable_testing)
        result = workflow.execute(
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

        # Update task with results
        if result.get("status") == "failed":
            db_manager.update_status(task_id, TaskStatusEnum.FAILED)
            db_manager.add_error(task_id, result.get("error", "Unknown error"))
        else:
            db_manager.update_status(task_id, TaskStatusEnum.COMPLETED)
            db_manager.save_result(task_id, {
                "plan": result.get("plan", {}),
                "code": result.get("code", {}),
                "execution_result": result.get("execution_result", {}),
                "review_result": result.get("review_result", {}),
                "test_result": result.get("test_result", {}),
                "iterations": result.get("iterations", 0),
            })

        logger.info(f"[Celery] Workflow completed for task {task_id}: {result.get('status')}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Workflow failed for task {task_id}: {e}")
        db_manager.update_status(task_id, TaskStatusEnum.FAILED)
        db_manager.add_error(task_id, str(e))
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def execute_planner_task(
    self,
    task_id: str,
    description: str,
    language: str = "python",
) -> Dict[str, Any]:
    """
    Execute only the planner agent as a Celery task

    Args:
        task_id: Unique task identifier
        description: Task description
        language: Programming language

    Returns:
        Planning results
    """
    from app.agents import PlannerAgent
    from app.core.llm_service import get_llm
    
    db_manager = DatabaseTaskManager()
    
    try:
        db_manager.update_status(task_id, TaskStatusEnum.PLANNING)
        logger.info(f"[Celery] Running planner for task {task_id}")

        llm = get_llm()
        agent = PlannerAgent(llm)
        result = agent.execute({
            "description": description,
            "language": language,
        })

        db_manager.save_plan(task_id, result.get("plan", {}))
        logger.info(f"[Celery] Planning completed for task {task_id}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Planning failed for task {task_id}: {e}")
        db_manager.add_error(task_id, str(e))
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def execute_coder_task(
    self,
    task_id: str,
    description: str,
    plan: Dict[str, Any],
    language: str = "python",
) -> Dict[str, Any]:
    """
    Execute only the coder agent as a Celery task

    Args:
        task_id: Unique task identifier
        description: Task description
        plan: Planning results
        language: Programming language

    Returns:
        Code generation results
    """
    from app.agents import CoderAgent
    from app.core.llm_service import get_llm
    
    db_manager = DatabaseTaskManager()
    
    try:
        logger.info(f"[Celery] Running coder for task {task_id}")

        llm = get_llm()
        agent = CoderAgent(llm)
        result = agent.execute({
            "description": description,
            "language": language,
            "plan": plan,
        })

        db_manager.save_code(task_id, result.get("code", ""))
        logger.info(f"[Celery] Coding completed for task {task_id}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Coding failed for task {task_id}: {e}")
        db_manager.add_error(task_id, str(e))
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def execute_reviewer_task(
    self,
    task_id: str,
    code: str,
    description: str,
    execution_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute only the reviewer agent as a Celery task

    Args:
        task_id: Unique task identifier
        code: Generated code
        description: Task description
        execution_result: Code execution results

    Returns:
        Review results
    """
    from app.agents import ReviewerAgent
    from app.core.llm_service import get_llm
    
    db_manager = DatabaseTaskManager()
    
    try:
        logger.info(f"[Celery] Running reviewer for task {task_id}")

        llm = get_llm()
        agent = ReviewerAgent(llm)
        result = agent.execute({
            "code": code,
            "description": description,
            "language": "python",
            "execution_result": execution_result or {},
        })

        db_manager.save_review(task_id, result)
        logger.info(f"[Celery] Review completed for task {task_id}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Review failed for task {task_id}: {e}")
        db_manager.add_error(task_id, str(e))
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task(bind=True, max_retries=3)
def execute_tester_task(
    self,
    task_id: str,
    code: str,
    description: str,
    execution_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute only the tester agent as a Celery task

    Args:
        task_id: Unique task identifier
        code: Generated code
        description: Task description
        execution_result: Code execution results

    Returns:
        Test results
    """
    from app.agents import TesterAgent
    from app.core.llm_service import get_llm
    
    db_manager = DatabaseTaskManager()
    
    try:
        logger.info(f"[Celery] Running tester for task {task_id}")

        llm = get_llm()
        agent = TesterAgent(llm)
        result = agent.execute({
            "code": code,
            "description": description,
            "language": "python",
            "execution_result": execution_result or {},
        })

        db_manager.save_test_result(task_id, result)
        logger.info(f"[Celery] Testing completed for task {task_id}")
        return result

    except Exception as e:
        logger.error(f"[Celery] Testing failed for task {task_id}: {e}")
        db_manager.add_error(task_id, str(e))
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def cleanup_old_tasks(days: int = 7):
    """
    Cleanup old completed/failed tasks from database

    Args:
        days: Number of days to keep tasks
    """
    from datetime import datetime, timedelta
    from app.db.database import get_db_session
    from app.db.models import TaskModel
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        session = get_db_session()
        deleted_count = session.query(TaskModel).filter(
            TaskModel.updated_at < cutoff_date
        ).delete()
        session.commit()
        session.close()
        
        logger.info(f"[Celery] Cleaned up {deleted_count} tasks older than {days} days")
        return {"deleted_count": deleted_count}
    
    except Exception as e:
        logger.error(f"[Celery] Cleanup failed: {e}")
        
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
