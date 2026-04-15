"""
Reviewer Agent - Reviews and validates generated code
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent


class ReviewerAgent(BaseAgent):
    """Agent responsible for reviewing code quality and correctness"""
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Reviewer"):
        super().__init__(
            llm=llm,
            name=name,
            role="reviewer",
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an expert code reviewer and quality assurance engineer.
Your role is to thoroughly review code for quality, correctness, and best practices.

Review Criteria:
1. Code Correctness: Does the code solve the problem correctly?
2. Code Quality: Is the code clean, readable, and maintainable?
3. Best Practices: Does it follow language-specific best practices?
4. Error Handling: Are edge cases and errors handled properly?
5. Security: Are there any security vulnerabilities?
6. Performance: Is the code efficient?
7. Documentation: Are there adequate comments and docstrings?

Output Format:
Return a JSON object with:
- passed: Boolean indicating if code passes review
- score: Numeric score from 0-10
- comments: List of specific comments about the code
- suggestions: List of improvement suggestions (if any)
- critical_issues: List of critical issues that must be fixed
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
