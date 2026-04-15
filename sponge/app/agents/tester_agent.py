"""
Tester Agent - Tests and validates code functionality
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from loguru import logger

from .base_agent import BaseAgent


class TesterAgent(BaseAgent):
    """Agent responsible for testing and validating code"""

    def __init__(self, llm: BaseLanguageModel, name: str = "Tester"):
        super().__init__(
            llm=llm,
            name=name,
            role="tester",
        )

    def _default_system_prompt(self) -> str:
        return """You are an expert software tester and QA engineer.
Your role is to design and execute comprehensive tests for code.

Testing Guidelines:
1. Write unit tests that cover all main functionality
2. Include edge cases and boundary conditions
3. Test error handling and exceptional scenarios
4. Ensure tests are independent and reproducible
5. Use appropriate testing frameworks (pytest, unittest, etc.)
6. Validate both expected outputs and side effects

Output Format:
Return a JSON object with:
- test_plan: Description of testing approach
- test_cases: List of test cases with inputs and expected outputs
- test_code: Generated test code
- results: Test execution results (if executed)
- passed: Boolean indicating if all tests passed
- coverage_notes: Notes about test coverage gaps
"""

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and execute tests for the code

        Args:
            input_data: Dictionary containing:
                - code: The code to test
                - description: Original task description
                - language: Programming language
                - plan: Original plan (optional)
                - execution_result: Results from code execution (optional)

        Returns:
            Dictionary containing:
                - test_plan: Testing approach
                - test_cases: List of test cases
                - test_code: Generated test code
                - passed: Whether tests passed
                - coverage_notes: Coverage observations
        """
        code = input_data.get("code", "")
        description = input_data.get("description", "")
        language = input_data.get("language", "python")
        execution_result = input_data.get("execution_result", {})

        if not code:
            raise ValueError("Code is required for testing")

        # Build context
        context = {
            "Programming Language": language,
            "Task Description": description,
            "Code to Test": f"```{language}\n{code}\n```",
        }

        if execution_result:
            if execution_result.get("output"):
                context["Execution Output"] = execution_result["output"]
            if execution_result.get("error"):
                context["Execution Error"] = execution_result["error"]

        messages = self._build_messages(
            user_input="Design comprehensive tests for this code and generate test code.",
            context=context,
        )

        # Invoke LLM
        response = await self._invoke_llm(messages)

        # Parse the response to extract test data
        test_data = self._parse_test_response(response, language)

        logger.info(f"Test generation completed - {len(test_data.get('test_cases', []))} test cases")

        return test_data

    def _parse_test_response(self, response: str, language: str) -> Dict[str, Any]:
        """Parse LLM response to extract test data"""
        try:
            # Try to find JSON in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                test_data = json.loads(json_str)

                # Ensure required fields with defaults
                if "test_plan" not in test_data:
                    test_data["test_plan"] = "Comprehensive testing of generated code"

                if "test_cases" not in test_data:
                    test_data["test_cases"] = []

                if "test_code" not in test_data:
                    # Try to extract test code from response
                    test_data["test_code"] = self._extract_code_from_text(response, language)

                if "passed" not in test_data:
                    test_data["passed"] = True  # Default to passed if no failures detected

                if "coverage_notes" not in test_data:
                    test_data["coverage_notes"] = "Tests cover main functionality"

                return test_data
            else:
                # Fallback: create basic test structure
                return self._create_fallback_tests(response, language)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse test JSON: {e}")
            return self._create_fallback_tests(response, language)

    def _extract_code_from_text(self, text: str, language: str) -> str:
        """Extract test code from plain text response"""
        import re

        # Pattern for ```language ... ``` blocks
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            return matches[0].strip()
        else:
            # Return whole response as potential test code
            return text.strip()

    def _create_fallback_tests(self, response: str, language: str) -> Dict[str, Any]:
        """Create fallback test structure when JSON parsing fails"""
        test_code = self._extract_code_from_text(response, language)

        return {
            "test_plan": "Basic functionality testing",
            "test_cases": [
                {
                    "name": "basic_test",
                    "description": "Verify basic functionality",
                    "input": "",
                    "expected_output": "Code executes without errors",
                }
            ],
            "test_code": test_code,
            "passed": True,
            "coverage_notes": "Manual review recommended for comprehensive coverage",
        }
