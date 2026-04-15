"""
Celery Tasks for Sponge Agents
"""

from typing import Any, Dict
from loguru import logger
from app.celery_app import celery_app
from app.agents import PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent
from app.core.llm_service import get_llm


@celery_app.task(
    bind=True,
    name="app.agents.tasks.planner_task",
    track_started=True,
)
async def planner_task(
    self,
    task_id: str,
    description: str,
    language: str,
) -> Dict[str, Any]:
    """
    Execute planner agent as a Celery task
    
    Args:
        task_id: Unique task identifier
        description: Task description
        language: Programming language
        
    Returns:
        Planning results
    """
    try:
        logger.info(f"[Planner] Starting planning for task {task_id}")
        
        llm = get_llm()
        agent = PlannerAgent(llm)
        
        result = await agent.execute({
            "description": description,
            "language": language,
        })
        
        logger.info(f"[Planner] Planning completed for task {task_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"[Planner] Task {task_id} failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="app.agents.tasks.coder_task",
    track_started=True,
)
async def coder_task(
    self,
    task_id: str,
    description: str,
    language: str,
    plan: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute coder agent as a Celery task
    
    Args:
        task_id: Unique task identifier
        description: Task description
        language: Programming language
        plan: Planning results from planner agent
        
    Returns:
        Code generation results
    """
    try:
        logger.info(f"[Coder] Starting coding for task {task_id}")
        
        llm = get_llm()
        agent = CoderAgent(llm)
        
        result = await agent.execute({
            "description": description,
            "language": language,
            "plan": plan,
        })
        
        logger.info(f"[Coder] Coding completed for task {task_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"[Coder] Task {task_id} failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="app.agents.tasks.reviewer_task",
    track_started=True,
)
async def reviewer_task(
    self,
    task_id: str,
    code: str,
    description: str,
    language: str,
    execution_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Execute reviewer agent as a Celery task
    
    Args:
        task_id: Unique task identifier
        code: Generated code to review
        description: Task description
        language: Programming language
        execution_result: Results from code execution
        
    Returns:
        Review results
    """
    try:
        logger.info(f"[Reviewer] Starting review for task {task_id}")
        
        llm = get_llm()
        agent = ReviewerAgent(llm)
        
        result = await agent.execute({
            "code": code,
            "description": description,
            "language": language,
            "execution_result": execution_result or {},
        })
        
        logger.info(f"[Reviewer] Review completed for task {task_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"[Reviewer] Task {task_id} failed: {e}")
        raise


@celery_app.task(
    bind=True,
    name="app.agents.tasks.tester_task",
    track_started=True,
)
async def tester_task(
    self,
    task_id: str,
    code: str,
    description: str,
    language: str,
    execution_result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Execute tester agent as a Celery task
    
    Args:
        task_id: Unique task identifier
        code: Generated code to test
        description: Task description
        language: Programming language
        execution_result: Results from code execution
        
    Returns:
        Test results
    """
    try:
        logger.info(f"[Tester] Starting testing for task {task_id}")
        
        llm = get_llm()
        agent = TesterAgent(llm)
        
        result = await agent.execute({
            "code": code,
            "description": description,
            "language": language,
            "execution_result": execution_result or {},
        })
        
        logger.info(f"[Tester] Testing completed for task {task_id}")
        
        return {
            "status": "success",
            "task_id": task_id,
            "result": result,
        }
        
    except Exception as e:
        logger.error(f"[Tester] Task {task_id} failed: {e}")
        raise
