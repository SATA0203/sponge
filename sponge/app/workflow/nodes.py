"""
Workflow Nodes - Individual agent nodes for the LangGraph workflow
"""

from typing import Any, Dict, TypedDict
from loguru import logger

from app.agents import PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent
from app.tools.code_executor import CodeExecutor
from app.core.llm_service import get_llm


# Type definition for workflow state
class WorkflowState(TypedDict):
    """Workflow state type"""
    task_id: str
    description: str
    language: str
    plan: Dict[str, Any]
    code: Dict[str, Any]
    execution_result: Dict[str, Any]
    review_result: Dict[str, Any]
    test_result: Dict[str, Any]
    iterations: int
    max_iterations: int
    error: str
    status: str


# Initialize agents (lazy initialization)
_planner_agent = None
_coder_agent = None
_reviewer_agent = None
_tester_agent = None
_code_executor = None


def _get_planner_agent():
    global _planner_agent
    if _planner_agent is None:
        llm = get_llm()
        _planner_agent = PlannerAgent(llm)
    return _planner_agent


def _get_coder_agent():
    global _coder_agent
    if _coder_agent is None:
        llm = get_llm()
        _coder_agent = CoderAgent(llm)
    return _coder_agent


def _get_reviewer_agent():
    global _reviewer_agent
    if _reviewer_agent is None:
        llm = get_llm()
        _reviewer_agent = ReviewerAgent(llm)
    return _reviewer_agent


def _get_tester_agent():
    global _tester_agent
    if _tester_agent is None:
        llm = get_llm()
        _tester_agent = TesterAgent(llm)
    return _tester_agent


def _get_code_executor():
    global _code_executor
    if _code_executor is None:
        _code_executor = CodeExecutor()
    return _code_executor


async def planner_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Planner node - Creates a plan for the task
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with plan
    """
    logger.info(f"[Planner] Creating plan for task: {state['task_id']}")
    
    try:
        agent = _get_planner_agent()
        result = await agent.execute({
            "description": state["description"],
            "language": state["language"],
        })
        
        logger.info(f"[Planner] Plan created: {result.get('summary', '')}")
        
        return {
            "plan": result.get("plan", {}),
            "status": "planning_complete",
        }
        
    except Exception as e:
        logger.error(f"[Planner] Error: {e}")
        return {
            "error": str(e),
            "status": "failed",
        }


async def coder_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Coder node - Generates code based on the plan
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with generated code
    """
    logger.info(f"[Coder] Generating code for task: {state['task_id']}")
    
    try:
        agent = _get_coder_agent()
        result = await agent.execute({
            "description": state["description"],
            "language": state["language"],
            "plan": state.get("plan", {}),
        })
        
        logger.info(f"[Coder] Code generated ({len(result.get('code', ''))} chars)")
        
        return {
            "code": result,
            "status": "coding_complete",
        }
        
    except Exception as e:
        logger.error(f"[Coder] Error: {e}")
        return {
            "error": str(e),
            "status": "failed",
        }


async def executor_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Executor node - Executes the generated code
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with execution results
    """
    logger.info(f"[Executor] Executing code for task: {state['task_id']}")
    
    try:
        executor = _get_code_executor()
        code_data = state.get("code", {})
        code = code_data.get("code", "")
        language = code_data.get("language", state["language"])
        
        result = await executor.execute(
            code=code,
            language=language,
        )
        
        if result["success"]:
            logger.info(f"[Executor] Execution successful in {result.get('execution_time', 0):.2f}s")
        else:
            logger.warning(f"[Executor] Execution failed: {result.get('error', '')}")
        
        return {
            "execution_result": result,
            "status": "execution_complete",
        }
        
    except Exception as e:
        logger.error(f"[Executor] Error: {e}")
        return {
            "error": str(e),
            "status": "failed",
        }


async def reviewer_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Reviewer node - Reviews the generated and executed code
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with review results
    """
    logger.info(f"[Reviewer] Reviewing code for task: {state['task_id']}")
    
    try:
        agent = _get_reviewer_agent()
        code_data = state.get("code", {})
        code = code_data.get("code", "")
        
        result = await agent.execute({
            "code": code,
            "description": state["description"],
            "language": state["language"],
            "execution_result": state.get("execution_result", {}),
        })
        
        passed = result.get("passed", False)
        score = result.get("score", 0)
        
        if passed:
            logger.info(f"[Reviewer] Code passed review (score: {score}/10)")
        else:
            logger.warning(f"[Reviewer] Code failed review (score: {score}/10)")
        
        return {
            "review_result": result,
            "status": "review_complete",
        }
        
    except Exception as e:
        logger.error(f"[Reviewer] Error: {e}")
        return {
            "error": str(e),
            "status": "failed",
        }


async def tester_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Tester node - Tests the generated code

    Args:
        state: Current workflow state

    Returns:
        Updated state with test results
    """
    logger.info(f"[Tester] Testing code for task: {state['task_id']}")

    try:
        agent = _get_tester_agent()
        code_data = state.get("code", {})
        code = code_data.get("code", "")

        result = await agent.execute({
            "code": code,
            "description": state["description"],
            "language": state["language"],
            "execution_result": state.get("execution_result", {}),
        })

        passed = result.get("passed", False)
        test_cases = len(result.get("test_cases", []))

        if passed:
            logger.info(f"[Tester] All {test_cases} test cases passed")
        else:
            logger.warning(f"[Tester] Some tests failed ({test_cases} test cases)")

        return {
            "test_result": result,
            "status": "testing_complete",
        }

    except Exception as e:
        logger.error(f"[Tester] Error: {e}")
        return {
            "error": str(e),
            "status": "failed",
        }
