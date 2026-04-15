"""
Planner Agent - Creates detailed plans for coding tasks

REFACTORED: Now follows Orchestrator-Worker pattern
- No fixed role boundaries
- Reads from external state (spec.md, history.jsonl)
- Outputs reasoning chain for continuity
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class PlannerAgent(BaseAgent):
    """Agent responsible for analyzing requirements and creating execution plans
    
    REFACTORED: This agent now:
    - Reads task spec from external state instead of input_data
    - Appends reasoning to history, not just conclusions
    - Does not pass work to next agent (Orchestrator coordinates)
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Planner", task_progress: Optional[TaskProgress] = None):
        super().__init__(
            llm=llm,
            name=name,
            role="planner",  # Kept for backward compat, but not used for boundaries
        )
        self.task_progress = task_progress
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software architect performing planning analysis.

IMPORTANT: You are NOT a "Planner" with fixed boundaries. You can reason about any aspect of the task.

Your task is to analyze requirements and create detailed, actionable plans.

Guidelines:
1. Break down complex tasks into clear, sequential steps
2. Identify potential challenges and edge cases
3. Specify the programming language and key dependencies
4. Estimate complexity for each step
5. Ensure plans are testable and verifiable
6. EXPLICITLY STATE YOUR REASONING for each decision (critical for continuity!)

Output Format:
Return a JSON object with:
- summary: Brief overview of the approach
- reasoning: Key architectural decisions and WHY you made them (REQUIRED)
- steps: List of steps, each with:
  - step_number: Integer step number
  - description: Clear description of what to do
  - estimated_complexity: low/medium/high
  - reasoning: Why this step is needed

Note: Do NOT assign steps to specific agents. The Orchestrator will coordinate execution.
"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a plan for the given task
        
        REFACTORED: Now reads from external state and writes reasoning to history
        
        Args:
            input_data: Dictionary containing:
                - task_id: Task ID to load spec from (preferred)
                - description: Task description (fallback if no task_id)
                - requirements: Optional additional requirements
                - language: Target programming language
                
        Returns:
            Dictionary containing:
                - plan: The generated plan with steps
                - summary: Plan summary
                - reasoning: Key architectural decisions (NEW)
        """
        # Try to load from external state first
        task_id = input_data.get("task_id")
        description = input_data.get("description", "")
        requirements = input_data.get("requirements", "")
        language = input_data.get("language", "python")
        
        # Load spec from external state if available
        if task_id and self.task_progress:
            spec = self.task_progress.read_spec()
            if spec:
                description = spec.get("goal", description)
                constraints = spec.get("constraints", [])
                if constraints:
                    requirements = "; ".join(constraints) + "; " + requirements
                metadata = spec.get("metadata", {})
                language = metadata.get("language", language)
                logger.info(f"Loaded spec from external state for task {task_id}")
        
        if not description:
            raise ValueError("Task description is required")
        
        # Build the prompt with explicit context about external state usage
        context = {
            "Task Description": description,
            "Programming Language": language,
        }
        if requirements:
            context["Additional Requirements"] = requirements
        
        # Add execution history if available (critical for continuity!)
        if self.task_progress:
            steps = self.task_progress.get_completed_steps()
            if steps:
                history_summary = "\\n".join([
                    f"- Step {s['step_number']}: {s['description']} (Outcome: {s['outcome']})"
                    for s in steps[-5:]  # Last 5 steps for context
                ])
                context["Recent Execution History"] = history_summary
            
            issues = self.task_progress.get_known_issues()
            if issues:
                issues_summary = "\\n".join([
                    f"- {i['issue']} (Workaround: {i.get('workaround', 'None')})"
                    for i in issues
                ])
                context["Known Issues to Avoid"] = issues_summary
        
        messages = self._build_messages(
            user_input="Create a detailed plan to accomplish this task. EXPLICITLY STATE YOUR REASONING for each decision.",
            context=context,
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse the response to extract JSON
        plan_data = self._parse_plan_response(response)
        
        # CRITICAL: Write reasoning to external state for continuity
        if self.task_progress and plan_data.get("reasoning"):
            self.task_progress.add_completed_step(
                step_number=0,  # Planning phase
                description="Created execution plan",
                outcome=f"Plan with {len(plan_data.get('steps', []))} steps",
                reasoning=plan_data["reasoning"],  # Preserve reasoning chain!
                artifacts={"plan_json": json.dumps(plan_data)}
            )
            logger.info("Wrote planning reasoning to external state")
        
        logger.info(f"Generated plan with {len(plan_data.get('steps', []))} steps")
        
        return {
            "plan": plan_data,
            "summary": plan_data.get("summary", ""),
            "reasoning": plan_data.get("reasoning", ""),  # NEW: Return reasoning
        }
    
    def _parse_plan_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract plan JSON"""
        try:
            # Try to find JSON in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                plan_data = json.loads(json_str)
                
                # Validate structure
                if "steps" not in plan_data:
                    plan_data["steps"] = []
                if "summary" not in plan_data:
                    plan_data["summary"] = "Auto-generated plan"
                
                # Ensure steps have required fields
                for i, step in enumerate(plan_data["steps"]):
                    if "step_number" not in step:
                        step["step_number"] = i + 1
                    if "agent" not in step:
                        step["agent"] = "coder"
                    if "status" not in step:
                        step["status"] = "pending"
                
                return plan_data
            else:
                # Fallback: create a simple plan
                return self._create_fallback_plan(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse plan JSON: {e}")
            return self._create_fallback_plan(response)
    
    def _create_fallback_plan(self, response: str) -> Dict[str, Any]:
        """Create a fallback plan when JSON parsing fails"""
        return {
            "summary": "Plan generated from task description",
            "steps": [
                {
                    "step_number": 1,
                    "description": f"Analyze requirements: {response[:200]}",
                    "agent": "coder",
                    "status": "pending",
                    "estimated_complexity": "medium",
                },
                {
                    "step_number": 2,
                    "description": "Implement the solution",
                    "agent": "coder",
                    "status": "pending",
                    "estimated_complexity": "medium",
                },
                {
                    "step_number": 3,
                    "description": "Review and test the code",
                    "agent": "reviewer",
                    "status": "pending",
                    "estimated_complexity": "low",
                },
            ],
        }
