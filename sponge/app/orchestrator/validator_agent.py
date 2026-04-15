"""
Validator Agent - Pure adversarial validator that only finds problems

This implements the "Agent as Denier" pattern from the architecture refactor:
- Validator ONLY finds issues, never continues work
- Returns problems to orchestrator, not to "next" agent
- No role boundaries - can find any type of issue (architecture, code, tests)
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from ..agents.base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class ValidatorAgent(BaseAgent):
    """
    Adversarial validator agent that exclusively finds problems.
    
    Unlike the old ReviewerAgent:
    - Does NOT pass work forward to "next" agents
    - Does NOT attempt to fix issues
    - ONLY identifies and documents problems
    - Returns findings to orchestrator for decision-making
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        name: str = "Validator",
        task_progress: Optional[TaskProgress] = None,
        validation_type: str = "comprehensive",
    ):
        """
        Initialize validator
        
        Args:
            llm: Language model instance
            name: Agent name
            task_progress: Task progress manager
            validation_type: Type of validation (comprehensive/code/architecture/tests)
        """
        super().__init__(
            llm=llm,
            name=name,
            role="validator",
        )
        self.task_progress = task_progress
        self.validation_type = validation_type
    
    def _default_system_prompt(self) -> str:
        return """You are an adversarial validator agent. Your SOLE purpose is to find problems.

Critical Principles:
1. You do NOT fix issues - you only identify them
2. You do NOT pass work to other agents - you report to the orchestrator
3. You have NO role boundaries - find ANY type of problem (logic, security, performance, style)
4. Be thorough and skeptical - assume there are hidden issues
5. Prioritize issues by severity and impact

Your Job:
- Scrutinize the provided work with fresh eyes
- Identify logical errors, edge cases, and assumptions
- Check alignment with original task goals
- Find security vulnerabilities, performance issues, and maintainability problems
- Document each issue clearly with evidence and severity

Output Format:
Return JSON with:
- passed: Boolean (true ONLY if zero issues found)
- issues: List of issues, each with:
  - title: Brief issue title
  - description: Detailed explanation
  - severity: critical/high/medium/low
  - location: Where the issue occurs (file, line, component)
  - evidence: Specific code/text that demonstrates the issue
  - recommendation: How to fix it (but YOU won't fix it)
- summary: Overall assessment
- confidence: Your confidence in this validation (low/medium/high)

Remember: Finding no issues is extremely rare. If passed=true, double-check your work.
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute validation
        
        Args:
            input_data: Dictionary containing:
                - artifact: The work product to validate (code, design, etc.)
                - task_goal: Original task objective
                - completed_steps: What was done
                - validation_focus: Optional focus areas
                
        Returns:
            Dictionary containing validation results (issues, not fixes)
        """
        artifact = input_data.get("artifact", "")
        task_goal = input_data.get("task_goal", "")
        completed_steps = input_data.get("completed_steps", [])
        validation_focus = input_data.get("validation_focus", [])
        
        if not artifact:
            raise ValueError("Artifact to validate is required")
        
        # Build comprehensive context
        context_parts = []
        
        # Include full task history if available
        if self.task_progress:
            context_parts.append(self.task_progress.get_full_context_for_agent())
            context_parts.append("\n" + "=" * 60)
            context_parts.append("ARTIFACT FOR VALIDATION")
            context_parts.append("=" * 60 + "\n")
        
        context_parts.append(f"Artifact:\n{artifact}")
        
        if task_goal:
            context_parts.append(f"\n\nOriginal Task Goal: {task_goal}")
        
        if completed_steps:
            context_parts.append("\n\nCompleted Steps:")
            for step in completed_steps:
                context_parts.append(f"  - {step}")
        
        if validation_focus:
            context_parts.append(f"\n\nValidation Focus Areas: {', '.join(validation_focus)}")
        
        messages = self._build_messages(
            user_input="\n".join(context_parts),
            context={"Validation Type": self.validation_type},
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse response
        result = self._parse_response(response)
        
        # Record issues in task progress (critical for avoiding repeat mistakes)
        if self.task_progress and result.get("issues"):
            for issue in result["issues"]:
                self.task_progress.add_known_issue(
                    issue=issue.get("description", "Unknown issue"),
                    workaround=issue.get("recommendation", ""),
                    severity=issue.get("severity", "medium"),
                    discovered_at_step=len(self.task_progress.get_completed_steps()),
                )
            
            # Update status
            issue_count = len(result["issues"])
            critical_count = sum(1 for i in result["issues"] if i.get("severity") == "critical")
            
            self.task_progress.update_current_status(
                current_step=f"Validation found {issue_count} issues ({critical_count} critical)",
                status="needs_revision" if not result.get("passed", False) else "validated",
                details={
                    "total_issues": issue_count,
                    "critical_issues": critical_count,
                    "passed": result.get("passed", False),
                },
                last_updated_by="validator",
            )
        
        logger.info(
            f"[Validator] Validation complete: {'PASSED' if result.get('passed') else 'FAILED'} "
            f"with {len(result.get('issues', []))} issues"
        )
        
        return result
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse validation response"""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # Ensure required fields
                if "passed" not in result:
                    result["passed"] = len(result.get("issues", [])) == 0
                if "issues" not in result:
                    result["issues"] = []
                if "summary" not in result:
                    result["summary"] = "Validation completed"
                if "confidence" not in result:
                    result["confidence"] = "medium"
                
                # Validate issue structure
                for issue in result["issues"]:
                    for field in ["title", "description", "severity"]:
                        if field not in issue:
                            issue[field] = "Unspecified" if field != "severity" else "medium"
                
                return result
            else:
                return self._create_fallback_result(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse validator JSON: {e}")
            return self._create_fallback_result(response)
    
    def _create_fallback_result(self, response: str) -> Dict[str, Any]:
        """Create fallback result when JSON parsing fails"""
        # Conservative: assume there are issues if we can't parse
        return {
            "passed": False,
            "issues": [
                {
                    "title": "Unable to parse validation result",
                    "description": f"Validator output could not be parsed: {response[:200]}",
                    "severity": "high",
                    "location": "validation_process",
                    "evidence": response[:500],
                    "recommendation": "Re-run validation",
                }
            ],
            "summary": "Validation failed due to parsing error",
            "confidence": "low",
        }


def create_validator(
    llm: BaseLanguageModel,
    task_progress: Optional[TaskProgress] = None,
    validation_type: str = "comprehensive",
) -> ValidatorAgent:
    """Factory function to create a validator agent"""
    return ValidatorAgent(
        llm=llm,
        task_progress=task_progress,
        validation_type=validation_type,
    )
