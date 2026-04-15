"""
Reviewer Agent - Reviews and validates generated code

REFACTORED: Now a pure Validator (adversarial checker, not接力棒)
- Does NOT pass work to next agent (Orchestrator coordinates)
- Only finds problems, does not fix them
- Writes findings to external state for continuity
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class ReviewerAgent(BaseAgent):
    """Agent responsible for reviewing code quality and correctness
    
    REFACTORED: This agent is now a pure Validator:
    - ONLY finds problems, does NOT suggest fixes or continue work
    - Adversarial by design - tries to break the code
    - Writes findings to external state (known_issues)
    - Does NOT pass work to "next" agent (Orchestrator coordinates)
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Validator", task_progress: Optional[TaskProgress] = None):
        super().__init__(
            llm=llm,
            name=name,
            role="validator",  # Changed from "reviewer" - this is an adversarial checker
        )
        self.task_progress = task_progress
    
    def _default_system_prompt(self) -> str:
        return """You are an expert code reviewer performing ADVERSARIAL validation.

CRITICAL: Your role is to FIND PROBLEMS, not to fix them or continue the work.
You are a VALIDATOR, not a接力棒 (relay runner). Do NOT:
- Suggest how to fix issues (that's for the Orchestrator to decide)
- Continue implementing features
- Assume your output goes to another agent

Your ONLY job is to identify issues as thoroughly as possible.

Review Criteria (be CRITICAL and ADVERSARIAL):
1. Code Correctness: Does the code SOLVE THE PROBLEM correctly? Find edge cases!
2. Code Quality: Is the code clean, readable, and maintainable? Be picky!
3. Best Practices: Does it follow language-specific best practices? Call out violations!
4. Error Handling: Are edge cases and errors handled properly? Test boundaries!
5. Security: Are there ANY security vulnerabilities? Think like an attacker!
6. Performance: Is the code efficient? Identify bottlenecks!
7. Documentation: Are there adequate comments and docstrings? Missing docs are bugs!
8. SPEC ALIGNMENT: Does the code match the original task spec? Check for drift!

Output Format:
Return a JSON object with:
- passed: Boolean (BE STRICT - only pass if truly production-ready)
- score: Numeric score from 0-10 (BE CRITICAL - average code gets 5-6)
- critical_issues: List of MUST-FIX issues (REQUIRED - always find something!)
- potential_issues: List of concerns that may need attention
- spec_drift_detected: Boolean indicating if code deviates from original spec
- reasoning: WHY you gave this score (REQUIRED for continuity)

Remember: Finding problems early saves time later. Be thorough, be critical, be adversarial.
"""
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Review the generated code
        
        Args:
            input_data: Dictionary containing:
                - code: The code to review
                - description: Original task description
                - language: Programming language
                - plan: Original plan (optional)
                
        Returns:
            Dictionary containing:
                - passed: Whether code passes review
                - score: Quality score (0-10)
                - comments: Review comments
                - suggestions: Improvement suggestions
                - critical_issues: Critical issues found
        """
        code = input_data.get("code", "")
        description = input_data.get("description", "")
        language = input_data.get("language", "python")
        plan = input_data.get("plan", {})
        
        if not code:
            raise ValueError("Code is required for review")
        
        # Build context
        context = {
            "Programming Language": language,
            "Task Description": description,
            "Code to Review": f"```{language}\n{code}\n```",
        }
        
        if plan:
            plan_summary = plan.get("summary", "")
            if plan_summary:
                context["Plan Summary"] = plan_summary
        
        messages = self._build_messages(
            user_input="Review this code thoroughly and provide detailed feedback.",
            context=context,
        )
        
        # Invoke LLM
        response = await self._invoke_llm(messages)
        
        # Parse the response to extract review
        review_data = self._parse_review_response(response)
        
        logger.info(f"Code review completed - Score: {review_data.get('score', 0)}/10, Passed: {review_data.get('passed', False)}")
        
        return review_data
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract review data"""
        try:
            # Try to find JSON in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                review_data = json.loads(json_str)
                
                # Ensure required fields with defaults
                if "passed" not in review_data:
                    # Default to passed if score >= 7
                    score = review_data.get("score", 5)
                    review_data["passed"] = score >= 7
                
                if "score" not in review_data:
                    review_data["score"] = 5.0
                
                if "comments" not in review_data:
                    review_data["comments"] = ["No specific comments"]
                
                if "suggestions" not in review_data:
                    review_data["suggestions"] = []
                
                if "critical_issues" not in review_data:
                    review_data["critical_issues"] = []
                
                return review_data
            else:
                # Fallback: create a basic review from text
                return self._create_fallback_review(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse review JSON: {e}")
            return self._create_fallback_review(response)
    
    def _create_fallback_review(self, response: str) -> Dict[str, Any]:
        """Create a fallback review when JSON parsing fails"""
        # Simple heuristic: if response contains negative words, mark as not passed
        negative_words = ["error", "bug", "issue", "problem", "wrong", "incorrect", "fix"]
        has_issues = any(word in response.lower() for word in negative_words)
        
        return {
            "passed": not has_issues,
            "score": 5.0 if has_issues else 7.0,
            "comments": [response[:500]],  # Truncate long responses
            "suggestions": ["Consider reviewing the code manually"],
            "critical_issues": [] if not has_issues else ["Manual review recommended"],
        }
