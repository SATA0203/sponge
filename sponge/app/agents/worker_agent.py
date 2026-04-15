"""
Worker Agent - Generic execution agent for sub-tasks

This is a generic worker that executes specific sub-tasks assigned by the Orchestrator.
Unlike the old role-based agents (Coder, Tester, etc.), this worker:
- Has no fixed role identity
- Executes whatever task type it's assigned
- Returns results to Orchestrator (doesn't pass to next agent)
- Focuses on depth within its assigned sub-task
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from .base_agent import BaseAgent


class WorkerAgent(BaseAgent):
    """
    Generic worker agent for executing sub-tasks.
    
    This replaces multiple role-specific agents (Coder, Tester, Planner, etc.)
    with a single flexible worker that adapts to the task type.
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        task_type: str = "general",
        name: str = "Worker",
    ):
        super().__init__(
            llm=llm,
            name=name,
            role=f"worker:{task_type}",
        )
        self.task_type = task_type
    
    def _default_system_prompt(self) -> str:
        """Generate system prompt based on task type"""
        
        prompts = {
            "research": """You are a research specialist worker agent.

Your task is to:
1. Investigate topics thoroughly
2. Gather accurate information from available context
3. Document findings clearly and comprehensively
4. Identify gaps in knowledge or conflicting information
5. Present information in organized, actionable format

Focus on completeness and accuracy. Cite sources when available.""",

            "implementation": """You are an implementation specialist worker agent.

Your task is to:
1. Write clean, correct, and efficient code
2. Follow best practices for the target language/framework
3. Include appropriate error handling
4. Add clear comments and documentation
5. Ensure code is testable and maintainable

Focus on correctness first, then optimization.""",

            "validation": """You are a validation specialist worker agent.

Your task is to:
1. Verify artifacts against requirements
2. Test edge cases and error conditions
3. Identify any discrepancies or issues
4. Document validation results clearly
5. Provide concrete evidence for any problems found

Be thorough and systematic. Your job is to find problems.""",

            "testing": """You are a testing specialist worker agent.

Your task is to:
1. Create comprehensive test cases
2. Cover normal paths, edge cases, and error conditions
3. Execute tests and record results
4. Document any failures with reproduction steps
5. Suggest additional test scenarios if gaps are found

Focus on breaking the code - find what doesn't work.""",

            "documentation": """You are a documentation specialist worker agent.

Your task is to:
1. Create clear, comprehensive documentation
2. Explain concepts at appropriate technical level
3. Include examples and usage instructions
4. Organize information logically
5. Identify any unclear areas that need clarification

Focus on clarity and usability for the target audience.""",

            "general": """You are a general-purpose worker agent.

Your task is to:
1. Execute the assigned sub-task with focus and precision
2. Work within the context provided by the Orchestrator
3. Produce high-quality output appropriate to the task type
4. Document your reasoning and approach
5. Return complete results for synthesis

Adapt your approach based on the specific task requirements.""",
        }
        
        base_prompt = prompts.get(self.task_type, prompts["general"])
        
        return f"""{base_prompt}

IMPORTANT WORKING PRINCIPLES:
- You are executing a SUB-TASK within a larger workflow
- The Orchestrator holds complete task context and ownership
- Your results will be synthesized with other sub-task results
- Work independently but within the provided context
- Document your reasoning for continuity"""

    async def execute(
        self,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the assigned sub-task
        
        Args:
            input_data: Dictionary containing:
                - task_description: What needs to be done
                - context: Full context from Orchestrator
                - constraints: Any specific constraints
                - expected_output: Description of expected output format
                
        Returns:
            Dictionary containing:
                - outcome: Description of what was accomplished
                - artifacts: Generated files/outputs
                - reasoning: Key decisions made during execution
                - issues_encountered: Any problems or blockers
        """
        task_description = input_data.get("task_description", "")
        context = input_data.get("context", "")
        constraints = input_data.get("constraints", [])
        expected_output = input_data.get("expected_output", "")
        
        if not task_description:
            raise ValueError("Task description is required")
        
        logger.info(f"[Worker:{self.task_type}] Executing: {task_description[:100]}...")
        
        # Build messages
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=self._build_task_prompt(
                task_description=task_description,
                context=context,
                constraints=constraints,
                expected_output=expected_output,
            )),
        ]
        
        # Execute
        response = await self._invoke_llm(messages)
        
        # Parse result
        result = self._parse_result(response, expected_output)
        
        logger.info(f"[Worker:{self.task_type}] Completed - Outcome: {result.get('outcome', 'Unknown')[:100]}...")
        
        return result

    def _build_task_prompt(
        self,
        task_description: str,
        context: str,
        constraints: List[str],
        expected_output: str,
    ) -> str:
        """Build the complete task prompt"""
        
        prompt_parts = []
        
        # Add context from Orchestrator
        if context:
            prompt_parts.append(f"CONTEXT FROM ORCHESTRATOR:\n{context}\n")
        
        # Add task description
        prompt_parts.append(f"YOUR TASK:\n{task_description}\n")
        
        # Add constraints
        if constraints:
            prompt_parts.append("\nCONSTRAINTS:")
            for constraint in constraints:
                prompt_parts.append(f"- {constraint}")
        
        # Add expected output format
        if expected_output:
            prompt_parts.append(f"\nEXPECTED OUTPUT FORMAT:\n{expected_output}")
        
        # Add instruction
        prompt_parts.append("""\n
Execute this task thoroughly. 
Document your reasoning as you work.
Return results in structured JSON format with:
- outcome: What you accomplished
- artifacts: Files/outputs generated (as key-value pairs)
- reasoning: Key decisions and why you made them
- issues_encountered: Any problems or limitations""")
        
        return "\n".join(prompt_parts)

    def _parse_result(self, response: str, expected_output: str) -> Dict[str, Any]:
        """Parse worker response into structured result"""
        try:
            # Try to extract JSON
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Ensure required fields
                return {
                    "outcome": data.get("outcome", "Task executed"),
                    "artifacts": data.get("artifacts", {}),
                    "reasoning": data.get("reasoning", ""),
                    "issues_encountered": data.get("issues_encountered", []),
                    "raw_response": response,
                }
            else:
                # Fallback: treat entire response as outcome
                return {
                    "outcome": response[:2000],  # Truncate long responses
                    "artifacts": {"response_text": response},
                    "reasoning": "Response was not structured JSON",
                    "issues_encountered": [],
                    "raw_response": response,
                }
                
        except json.JSONDecodeError:
            return {
                "outcome": response[:2000],
                "artifacts": {"response_text": response},
                "reasoning": "JSON parsing failed",
                "issues_encountered": ["Response format error"],
                "raw_response": response,
            }
