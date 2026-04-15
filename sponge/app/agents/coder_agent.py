"""
Coder Agent - Generates code based on plans and requirements

REFACTORED: Now follows Orchestrator-Worker pattern
- No fixed "coder" boundaries - can reason about architecture, testing, etc.
- Reads from external state (spec.md, history.jsonl)
- Outputs reasoning chain for continuity
- Does not pass work to next agent (Orchestrator coordinates)
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class CoderAgent(BaseAgent):
    """Agent responsible for generating code based on plans
    
    REFACTORED: This agent now:
    - Is a general-purpose worker, not limited to "coding"
    - Reads task spec and history from external state
    - Appends reasoning to history, not just code conclusions
    - Does not pass work to reviewer (Orchestrator coordinates validation)
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Worker", task_progress: Optional[TaskProgress] = None):
        super().__init__(
            llm=llm,
            name=name,
            role="worker",  # Changed from "coder" - this is a general worker
        )
        self.task_progress = task_progress
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software engineer performing implementation work.

IMPORTANT: You are NOT limited to just "writing code". You can:
- Reason about architecture and design decisions
- Identify potential issues in the plan
- Suggest improvements to requirements
- Think about testing and edge cases
- Question assumptions if something seems wrong

Your task is to write clean, efficient, and well-documented code.

Guidelines:
1. Write clean, readable, and maintainable code
2. Follow best practices and design patterns
3. Include appropriate error handling
4. Add clear comments and docstrings
5. Write modular and testable code
6. Consider edge cases and input validation
7. EXPLICITLY STATE YOUR REASONING for implementation decisions (critical!)

Output Format:
Return a JSON object with:
- code: The generated code as a string
- language: Programming language used
- explanation: Brief explanation of the implementation
- reasoning: KEY IMPLEMENTATION DECISIONS AND WHY (REQUIRED)
- dependencies: List of required dependencies (if any)
- potential_issues: Any concerns or edge cases you identified

Note: Do NOT assume your output goes to a "reviewer". The Orchestrator will coordinate validation.
"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code based on the plan
        
        Args:
            input_data: Dictionary containing:
                - description: Task description
                - plan: The planning steps
                - language: Target programming language
                - current_step: Current step being executed
                
        Returns:
            Dictionary containing:
                - code: Generated code
                - language: Programming language
                - explanation: Code explanation
                - dependencies: Required dependencies
        """
        description = input_data.get("description", "")
        plan = input_data.get("plan", {})
        language = input_data.get("language", "python")
        current_step = input_data.get("current_step", "")
        
        if not description:
            raise ValueError("Task description is required")
        
        # Build context
        context = {
            "Task Description": description,
            "Programming Language": language,
        }
        
        if plan:
            plan_summary = plan.get("summary", "")
            steps = plan.get("steps", [])
            if steps:
                steps_str = "\n".join([f"{i+1}. {s.get('description', '')}" for i, s in enumerate(steps)])
                context["Plan Steps"] = steps_str
            if plan_summary:
                context["Plan Summary"] = plan_summary
        
        if current_step:
            context["Current Step"] = current_step
        
        messages = self._build_messages(
            user_input="Generate clean, production-ready code to accomplish this task.",
            context=context,
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse the response to extract code
        code_data = self._parse_code_response(response, language)
        
        logger.info(f"Generated {language} code ({len(code_data.get('code', ''))} chars)")
        
        return code_data
    
    def _parse_code_response(self, response: str, default_language: str) -> Dict[str, Any]:
        """Parse LLM response to extract code"""
        try:
            # Try to find JSON in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                code_data = json.loads(json_str)
                
                # Validate structure
                if "code" not in code_data:
                    # Maybe it's just code without JSON wrapper
                    code_data = self._extract_code_from_text(response, default_language)
                else:
                    # Ensure required fields
                    if "language" not in code_data:
                        code_data["language"] = default_language
                    if "explanation" not in code_data:
                        code_data["explanation"] = "Code generated by Coder agent"
                    if "dependencies" not in code_data:
                        code_data["dependencies"] = []
                
                return code_data
            else:
                # Response is likely plain code
                return self._extract_code_from_text(response, default_language)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse code JSON: {e}")
            return self._extract_code_from_text(response, default_language)
    
    def _extract_code_from_text(self, text: str, language: str) -> Dict[str, Any]:
        """Extract code from plain text response"""
        # Look for markdown code blocks
        import re
        
        # Pattern for ```language ... ``` blocks
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            code = matches[0].strip()
        else:
            # Use the whole response if no code blocks found
            code = text.strip()
        
        return {
            "code": code,
            "language": language,
            "explanation": "Code extracted from response",
            "dependencies": [],
        }
