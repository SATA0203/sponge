"""
Orchestrator Agent - Main agent that holds complete task intent and coordinates workers

This implements the Anthropic-style orchestrator-worker pattern where:
- A single lead agent maintains the full task context
- Worker agents are called for parallel exploration of sub-problems
- Results flow back to orchestrator for synthesis (not passed to next agent)
- No role-based handoffs, only functional delegation
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from ..agents.base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class OrchestratorAgent(BaseAgent):
    """
    Lead agent that maintains complete task intent and coordinates worker agents.
    
    Unlike the old PlannerAgent, this agent:
    - Never hands off tasks to "next" agents
    - Delegates sub-tasks to workers and synthesizes results
    - Maintains continuous reasoning chain via TaskProgress
    - Makes all architectural decisions
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        name: str = "Orchestrator",
        task_progress: Optional[TaskProgress] = None,
    ):
        super().__init__(
            llm=llm,
            name=name,
            role="orchestrator",
        )
        self.task_progress = task_progress
        self.worker_results: Dict[str, Any] = {}
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software architect and orchestration agent.
Your role is to maintain complete understanding of a coding task and coordinate execution.

Key Principles:
1. You hold the COMPLETE task intent - never delegate overall responsibility
2. Break complex problems into independent sub-tasks for parallel exploration
3. Synthesize all worker results yourself - do not pass work to "next" agents
4. Maintain reasoning continuity through external state (TaskProgress)
5. Make architectural decisions based on full context, not compressed summaries

Your Capabilities:
- Analyze requirements and create execution strategies
- Decompose problems into independent, parallelizable sub-problems
- Evaluate worker outputs and integrate them coherently
- Identify when additional exploration is needed
- Detect and resolve conflicts between different approaches

Output Format:
Return JSON with:
- strategy: Overall approach description
- subtasks: List of sub-tasks to delegate (if any)
- synthesis: Integration of all results (when workers complete)
- next_action: What should happen next (delegate/execute/complete)
- reasoning: Key decision factors (critical for state persistence)
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute orchestration logic
        
        Args:
            input_data: Dictionary containing:
                - task_id: Task identifier
                - goal: Primary task objective
                - constraints: Optional constraints
                - current_phase: Phase of execution (planning/delegating/synthesizing)
                - worker_results: Optional results from completed workers
                
        Returns:
            Dictionary containing orchestration decisions and synthesized results
        """
        task_id = input_data.get("task_id")
        goal = input_data.get("goal", "")
        constraints = input_data.get("constraints", [])
        metadata = input_data.get("metadata", {})
        current_phase = input_data.get("current_phase", "planning")
        worker_results = input_data.get("worker_results", {})
        
        if not goal:
            raise ValueError("Task goal is required")
        
        # Initialize or load task progress
        if not self.task_progress and task_id:
            self.task_progress = TaskProgress(task_id)
            # Write spec if this is the first run
            if not self.task_progress.read_spec():
                self.task_progress.write_spec(
                    goal=goal,
                    constraints=constraints,
                    metadata=metadata,
                )
        
        # Build context from TaskProgress (full reasoning chain, not compressed)
        if self.task_progress:
            full_context = self.task_progress.get_full_context_for_agent()
        else:
            full_context = f"Goal: {goal}\nConstraints: {constraints}"
        
        # Add worker results to context if available
        if worker_results:
            worker_context = "\n\nWORKER RESULTS TO SYNTHESIZE:\n"
            for worker_name, result in worker_results.items():
                worker_context += f"\n=== {worker_name} ===\n"
                worker_context += json.dumps(result, indent=2)
            full_context += worker_context
        
        # Determine phase-specific prompt
        phase_prompts = {
            "planning": "Create a comprehensive strategy. Identify which sub-problems can be explored in parallel.",
            "delegating": "Review worker assignments and determine if more delegation is needed.",
            "synthesizing": "Synthesize all worker results into a coherent solution. Resolve any conflicts.",
            "executing": "Create final implementation plan based on synthesized understanding.",
            "validating": "Review the complete solution. Identify any gaps or issues.",
        }
        
        phase_instruction = phase_prompts.get(current_phase, "Proceed with the task.")
        
        messages = self._build_messages(
            user_input=f"{phase_instruction}\n\n{full_context}",
            context={"Current Phase": current_phase},
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse response
        result = self._parse_response(response, current_phase)
        
        # Update task progress
        if self.task_progress:
            self._update_progress(result, current_phase, worker_results)
        
        logger.info(f"[Orchestrator] Phase: {current_phase}, Next action: {result.get('next_action', 'unknown')}")
        
        return result
    
    def _parse_response(self, response: str, phase: str) -> Dict[str, Any]:
        """Parse LLM response into structured output"""
        try:
            # Try to extract JSON
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Ensure required fields
                if "next_action" not in result:
                    result["next_action"] = "continue"
                if "reasoning" not in result:
                    result["reasoning"] = "No reasoning provided"
                
                return result
            else:
                return self._create_fallback_result(phase, response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse orchestrator JSON: {e}")
            return self._create_fallback_result(phase, response)
    
    def _create_fallback_result(self, phase: str, response: str) -> Dict[str, Any]:
        """Create fallback result when JSON parsing fails"""
        return {
            "strategy": response[:500],
            "subtasks": [],
            "synthesis": "",
            "next_action": "continue",
            "reasoning": "Fallback result due to parsing error",
        }
    
    def _update_progress(
        self,
        result: Dict[str, Any],
        phase: str,
        worker_results: Dict[str, Any],
    ):
        """Update task progress based on orchestration result"""
        if not self.task_progress:
            return
        
        # Record completed step if we have worker results (phase completed)
        if worker_results and phase != "planning":
            self.task_progress.add_completed_step(
                step_number=len(self.task_progress.get_completed_steps()) + 1,
                description=f"Completed {phase} phase with {len(worker_results)} worker(s)",
                outcome=result.get("synthesis", result.get("strategy", "Phase completed")),
                reasoning=result.get("reasoning", ""),
                artifacts={"result": json.dumps(result)},
            )
        
        # Update current status
        next_action = result.get("next_action", "unknown")
        self.task_progress.update_current_status(
            current_step=f"{phase} -> {next_action}",
            status="in_progress" if next_action != "complete" else "complete",
            details={
                "phase": phase,
                "next_action": next_action,
                "worker_count": len(worker_results),
            },
            last_updated_by="orchestrator",
        )
    
    async def delegate_subtask(
        self,
        subtask_name: str,
        subtask_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Delegate a subtask to a worker agent.
        
        This method creates a WorkerAgent instance and executes the subtask.
        The result will be synthesized by the orchestrator, not passed on.
        
        Args:
            subtask_name: Name for this subtask (for tracking)
            subtask_description: What the worker should do
            context: Additional context for the worker
            
        Returns:
            Worker's result for synthesis
        """
        logger.info(f"[Orchestrator] Delegating subtask: {subtask_name}")
        
        worker = WorkerAgent(
            llm=self.llm,
            name=subtask_name,
            task_progress=self.task_progress,
        )
        
        # Build worker input with full context
        worker_input = {
            "task_description": subtask_description,
            "parent_context": context or {},
        }
        
        if self.task_progress:
            worker_input["full_task_context"] = self.task_progress.get_full_context_for_agent()
        
        result = await worker.execute(worker_input)
        
        # Store result for later synthesis
        self.worker_results[subtask_name] = result
        
        logger.info(f"[Orchestrator] Subtask {subtask_name} completed")
        
        return result
    
    async def synthesize_results(self, worker_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Synthesize results from multiple workers.
        
        Args:
            worker_results: Optional override for stored results
            
        Returns:
            Synthesized result combining all worker outputs
        """
        results_to_synthesize = worker_results or self.worker_results
        
        if not results_to_synthesize:
            return {
                "synthesis": "No results to synthesize",
                "next_action": "complete",
            }
        
        # Call self with synthesizing phase
        return await self.execute({
            "task_id": self.task_progress.task_id if self.task_progress else None,
            "goal": self.task_progress.read_spec().get("goal") if self.task_progress else "",
            "current_phase": "synthesizing",
            "worker_results": results_to_synthesize,
        })


class WorkerAgent(BaseAgent):
    """
    Generic worker agent that executes specific sub-tasks.
    
    Workers:
    - Have no fixed role (not "coder", "reviewer", etc.)
    - Execute whatever sub-task the orchestrator assigns
    - Return results to orchestrator for synthesis
    - Do NOT pass work to other agents
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        name: str,
        task_progress: Optional[TaskProgress] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(
            llm=llm,
            name=name,
            role="worker",
            system_prompt=system_prompt,
        )
        self.task_progress = task_progress
    
    def _default_system_prompt(self) -> str:
        return """You are a specialized worker agent executing a specific sub-task.

Your Role:
1. Focus deeply on the assigned sub-task
2. Use your full capabilities - you are not limited by "role" boundaries
3. Provide comprehensive results for the orchestrator to synthesize
4. Include your reasoning process (critical for continuity)
5. Flag any issues or concerns you discover

Important:
- You do NOT pass work to other agents
- You do NOT make architectural decisions
- You DO provide detailed output for synthesis
- You DO identify potential problems for the orchestrator to address

Output Format:
Return JSON with:
- result: Your main output
- reasoning: How you arrived at this result
- confidence: Your confidence level (low/medium/high)
- issues: Any problems or concerns discovered
- suggestions: Recommendations for the orchestrator
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the assigned sub-task
        
        Args:
            input_data: Dictionary containing:
                - task_description: What to do
                - parent_context: Context from orchestrator
                - full_task_context: Complete task history (optional)
                
        Returns:
            Dictionary containing worker's results
        """
        task_description = input_data.get("task_description", "")
        parent_context = input_data.get("parent_context", {})
        full_task_context = input_data.get("full_task_context", "")
        
        if not task_description:
            raise ValueError("Task description is required")
        
        # Build comprehensive context
        context_parts = []
        
        if full_task_context:
            context_parts.append(full_task_context)
            context_parts.append("\n" + "=" * 60)
            context_parts.append("YOUR ASSIGNED SUB-TASK")
            context_parts.append("=" * 60 + "\n")
        
        context_parts.append(f"Task: {task_description}")
        
        if parent_context:
            context_parts.append("\nAdditional Context:")
            for k, v in parent_context.items():
                context_parts.append(f"  - {k}: {v}")
        
        messages = self._build_messages(
            user_input="\n".join(context_parts),
            context={"Worker": self.name},
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse response
        result = self._parse_response(response)
        
        # Update progress if available
        if self.task_progress:
            self.task_progress.update_current_status(
                current_step=f"Worker '{self.name}' executing",
                status="in_progress",
                details={"worker": self.name, "task": task_description[:100]},
                last_updated_by=self.name,
            )
        
        logger.info(f"[Worker:{self.name}] Task completed, confidence: {result.get('confidence', 'unknown')}")
        
        return result
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse worker response"""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Ensure required fields
                for field in ["result", "reasoning", "confidence"]:
                    if field not in result:
                        result[field] = "" if field == "reasoning" else ("result" if field == "result" else "medium")
                if "issues" not in result:
                    result["issues"] = []
                if "suggestions" not in result:
                    result["suggestions"] = []
                
                return result
            else:
                return {
                    "result": response,
                    "reasoning": "No explicit reasoning provided",
                    "confidence": "medium",
                    "issues": [],
                    "suggestions": [],
                }
                
        except json.JSONDecodeError:
            return {
                "result": response,
                "reasoning": "Fallback due to parsing error",
                "confidence": "low",
                "issues": ["Failed to parse structured output"],
                "suggestions": [],
            }
