"""
Workflow Graph - LangGraph-based multi-agent workflow orchestration
"""

import uuid
from typing import Any, Dict, Optional, Literal
from datetime import datetime
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .nodes import (
    WorkflowState,
    planner_node,
    coder_node,
    executor_node,
    reviewer_node,
)


class WorkflowManager:
    """Manages the multi-agent workflow execution"""
    
    def __init__(self):
        """Initialize workflow manager with compiled graph"""
        self.graph = self._build_graph()
        logger.info("WorkflowManager initialized")
    
    def _build_graph(self) -> StateGraph:
        """Build and compile the LangGraph workflow"""
        
        # Create state graph
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("planner", planner_node)
        workflow.add_node("coder", coder_node)
        workflow.add_node("executor", executor_node)
        workflow.add_node("reviewer", reviewer_node)
        
        # Define edges
        workflow.set_entry_point("planner")
        
        # Planner -> Coder
        workflow.add_edge("planner", "coder")
        
        # Coder -> Executor
        workflow.add_edge("coder", "executor")
        
        # Executor -> Reviewer
        workflow.add_edge("executor", "reviewer")
        
        # Reviewer -> conditional edge
        workflow.add_conditional_edges(
            "reviewer",
            self._should_continue,
            {
                "continue": "coder",  # Loop back to coder for improvements
                "end": END,  # End workflow
            },
        )
        
        # Compile with memory saver for checkpointing
        memory = MemorySaver()
        compiled = workflow.compile(checkpointer=memory)
        
        logger.info("Workflow graph compiled successfully")
        return compiled
    
    def _should_continue(self, state: WorkflowState) -> Literal["continue", "end"]:
        """
        Determine if workflow should continue or end
        
        Args:
            state: Current workflow state
            
        Returns:
            'continue' to loop back, 'end' to finish
        """
        iterations = state.get("iterations", 0)
        max_iterations = state.get("max_iterations", 3)
        error = state.get("error", "")
        
        # Check for errors
        if error:
            logger.warning(f"Workflow stopping due to error: {error}")
            return "end"
        
        # Check review result
        review_result = state.get("review_result", {})
        passed = review_result.get("passed", False)
        
        if passed:
            logger.info("Code passed review, ending workflow")
            return "end"
        
        # Check iteration limit
        if iterations >= max_iterations:
            logger.warning(f"Max iterations ({max_iterations}) reached, ending workflow")
            return "end"
        
        # Continue to improve code
        logger.info(f"Code needs improvement (iteration {iterations + 1}/{max_iterations})")
        return "continue"
    
    async def execute(
        self,
        description: str,
        language: str = "python",
        task_id: Optional[str] = None,
        max_iterations: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute the workflow for a given task
        
        Args:
            description: Task description
            language: Programming language
            task_id: Optional task ID (generated if not provided)
            max_iterations: Maximum refinement iterations
            
        Returns:
            Final workflow state
        """
        if not task_id:
            task_id = str(uuid.uuid4())
        
        # Initialize state
        initial_state: WorkflowState = {
            "task_id": task_id,
            "description": description,
            "language": language,
            "plan": {},
            "code": {},
            "execution_result": {},
            "review_result": {},
            "iterations": 0,
            "max_iterations": max_iterations,
            "error": "",
            "status": "started",
        }
        
        logger.info(f"Starting workflow for task {task_id}: {description[:50]}...")
        
        try:
            # Run the workflow
            config = {"configurable": {"thread_id": task_id}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Update status based on results
            if final_state.get("error"):
                final_state["status"] = "failed"
            elif final_state.get("review_result", {}).get("passed", False):
                final_state["status"] = "completed"
            else:
                final_state["status"] = "completed_with_warnings"
            
            logger.info(f"Workflow completed for task {task_id} with status: {final_state['status']}")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                **initial_state,
                "error": str(e),
                "status": "failed",
            }


# Singleton instance
_workflow_manager: Optional[WorkflowManager] = None


def get_workflow_manager() -> WorkflowManager:
    """Get or create workflow manager singleton"""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager


def create_workflow() -> WorkflowManager:
    """Create a new workflow manager instance"""
    return WorkflowManager()
