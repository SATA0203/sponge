"""
Planner Agent - Creates detailed plans for coding tasks
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent


class PlannerAgent(BaseAgent):
    """Agent responsible for analyzing requirements and creating execution plans"""
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Planner"):
        super().__init__(
            llm=llm,
            name=name,
            role="planner",
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software architect and planning agent.
Your role is to analyze coding requirements and create detailed, actionable plans.

Guidelines:
1. Break down complex tasks into clear, sequential steps
2. Identify potential challenges and edge cases
3. Specify the programming language and key dependencies
4. Estimate complexity for each step
5. Ensure plans are testable and verifiable

Output Format:
Return a JSON object with:
- summary: Brief overview of the approach
- steps: List of steps, each with:
  - step_number: Integer step number
  - description: Clear description of what to do
  - agent: Which agent should execute (coder, reviewer, executor)
  - estimated_complexity: low/medium/high
"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a plan for the given task
        
        Args:
            input_data: Dictionary containing:
                - description: Task description
                - requirements: Optional additional requirements
                - language: Target programming language
                
        Returns:
            Dictionary containing:
                - plan: The generated plan with steps
                - summary: Plan summary
        """
        description = input_data.get("description", "")
        requirements = input_data.get("requirements", "")
        language = input_data.get("language", "python")
        
        if not description:
            raise ValueError("Task description is required")
        
        # Build the prompt
        context = {
            "Task Description": description,
            "Programming Language": language,
        }
        if requirements:
            context["Additional Requirements"] = requirements
        
        messages = self._build_messages(
            user_input="Create a detailed plan to accomplish this task.",
            context=context,
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse the response to extract JSON
        plan_data = self._parse_plan_response(response)
        
        logger.info(f"Generated plan with {len(plan_data.get('steps', []))} steps")
        
        return {
            "plan": plan_data,
            "summary": plan_data.get("summary", ""),
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
