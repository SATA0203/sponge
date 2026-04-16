"""
Validator Agent - Pure adversarial verifier (does NOT take ownership)

This agent implements the "validator as negator" pattern from the architecture refactor.
Key difference from old Reviewer:
- ONLY finds problems, never suggests fixes directly
- NEVER takes ownership of the task
- Reports back to Orchestrator who decides next actions
- Purely adversarial role - its job is to break things
"""

from typing import Any, Dict, List, Optional
import json
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from .base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    """
    Pure adversarial validator agent.
    
    This replaces the old ReviewerAgent with a fundamentally different role:
    - Old Reviewer: Reviews code, suggests fixes, passes work along pipeline
    - New Validator: Finds problems ONLY, reports to Orchestrator, never takes ownership
    
    The Validator's success metric is finding issues, not helping fix them.
    """
    
    def __init__(self, llm: BaseLanguageModel, name: str = "Validator"):
        super().__init__(
            llm=llm,
            name=name,
            role="validator",
        )
    
    def _default_system_prompt(self) -> str:
        return """You are an adversarial validation agent. Your SOLE purpose is to find problems.

CRITICAL PRINCIPLES:
1. You do NOT fix problems - you only identify them
2. You do NOT take ownership of the task
3. You do NOT suggest complete solutions (only describe what's wrong)
4. Your success is measured by how thoroughly you break things
5. You report findings to the Orchestrator, who decides what to do

VALIDATION FOCUS AREAS:
- Correctness: Does it actually work? Find edge cases that break it
- Completeness: Are there missing pieces? What wasn't implemented?
- Consistency: Does it match the original requirements exactly?
- Robustness: What inputs would cause failures?
- Security: Are there vulnerabilities? Injection points? Data leaks?
- Performance: Are there obvious inefficiencies or bottlenecks?
- Error Handling: What happens when things go wrong?

YOUR OUTPUT:
Return a structured report with:
- passed: Boolean (true ONLY if you find ZERO issues)
- issues: List of ALL problems found (even minor ones)
- critical_issues: Subset of issues that would cause complete failure
- evidence: For each issue, provide concrete evidence (failing cases, problematic code, etc.)

Remember: The Orchestrator will use your findings to create fix tasks.
Your job is to be thorough, not helpful."""

    async def validate(
        self,
        artifact: str,
        artifact_type: str,
        requirements: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Validate an artifact against requirements
        
        Args:
            artifact: The thing to validate (code, document, plan, etc.)
            artifact_type: Type of artifact (code/design/test/etc.)
            requirements: Original requirements to validate against
            context: Additional context (previous issues, known problems, etc.)
            
        Returns:
            Validation report with issues found
        """
        logger.info(f"[Validator] Starting validation of {artifact_type}")
        
        # Build validation context
        context_str = ""
        if context:
            if context.get('known_issues'):
                context_str += f"\nKnown Issues to Re-check:\n{json.dumps(context['known_issues'], indent=2)}\n"
            if context.get('previous_failures'):
                context_str += f"\nPrevious Failures:\n{json.dumps(context['previous_failures'], indent=2)}\n"
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""{context_str}

ARTIFACT TYPE: {artifact_type}

REQUIREMENTS:
{requirements}

ARTIFACT TO VALIDATE:
{artifact}

TASK: Perform adversarial validation. Find EVERY problem you can.
Be ruthless - your job is to break this, not help it succeed.

Return JSON with this exact structure:
{{
    "passed": false,
    "issues": [
        {{
            "id": "ISSUE-001",
            "severity": "critical|high|medium|low",
            "category": "correctness|completeness|consistency|robustness|security|performance|error_handling",
            "description": "Clear description of the problem",
            "evidence": "Concrete evidence (failing input, problematic code section, etc.)",
            "impact": "What breaks because of this?"
        }}
    ],
    "critical_issues": [...],  // Subset of issues with severity=critical
    "summary": "Brief summary of validation findings",
    "confidence": 0.0-1.0  // How confident are you in this validation?
}}"""),
        ]
        
        response = await self._invoke_llm(messages)
        
        # Parse validation result
        result = self._parse_validation_response(response)
        
        # Log findings
        issue_count = len(result.get('issues', []))
        critical_count = len(result.get('critical_issues', []))
        
        if result.get('passed', False):
            logger.info(f"[Validator] Validation PASSED - no issues found")
        else:
            logger.warning(
                f"[Validator] Validation FAILED - found {issue_count} issues "
                f"({critical_count} critical)"
            )
        
        return result

    async def validate_execution(
        self,
        code: str,
        execution_result: Dict[str, Any],
        expected_behavior: str,
    ) -> Dict[str, Any]:
        """
        Validate actual execution results against expected behavior
        
        This is specifically for checking if running the code produces correct results.
        """
        logger.info("[Validator] Validating execution results...")
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""CODE:
```python
{code}
```

EXECUTION RESULT:
{json.dumps(execution_result, indent=2)}

EXPECTED BEHAVIOR:
{expected_behavior}

TASK: Compare actual execution vs expected behavior.
Find any discrepancies, errors, or unexpected outcomes.

Return JSON validation report."""),
        ]
        
        response = await self._invoke_llm(messages)
        return self._parse_validation_response(response)

    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into validation report"""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                
                # Ensure required fields
                if 'passed' not in data:
                    data['passed'] = len(data.get('issues', [])) == 0
                
                if 'issues' not in data:
                    data['issues'] = []
                
                if 'critical_issues' not in data:
                    # Auto-extract critical issues
                    data['critical_issues'] = [
                        i for i in data.get('issues', [])
                        if i.get('severity') == 'critical'
                    ]
                
                if 'confidence' not in data:
                    data['confidence'] = 0.8  # Default confidence
                
                return data
            else:
                return self._create_fallback_validation(response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse validation JSON: {e}")
            return self._create_fallback_validation(response)

    def _create_fallback_validation(self, response: str) -> Dict[str, Any]:
        """Create fallback validation when JSON parsing fails"""
        # Check for negative indicators
        negative_indicators = [
            'error', 'bug', 'issue', 'problem', 'fail', 'wrong',
            'incorrect', 'missing', 'broken', 'vulnerability'
        ]
        
        has_issues = any(
            indicator in response.lower()
            for indicator in negative_indicators
        )
        
        return {
            'passed': not has_issues,
            'issues': [{
                'id': 'ISSUE-001',
                'severity': 'medium',
                'category': 'general',
                'description': response[:500],
                'evidence': 'Text analysis detected potential issues',
                'impact': 'Requires manual review',
            }] if has_issues else [],
            'critical_issues': [],
            'summary': 'Validation completed with text-based analysis',
            'confidence': 0.5,
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the validator's main validation workflow
        
        This method satisfies the BaseAgent abstract method requirement.
        It delegates to the appropriate validator method based on input.
        
        Args:
            input_data: Dictionary containing:
                - action: The action to perform (validate, validate_execution)
                - artifact: The artifact to validate (for validate action)
                - artifact_type: Type of artifact (for validate action)
                - requirements: Requirements to validate against (for validate action)
                - code: Code to validate (for validate_execution action)
                - execution_result: Execution results (for validate_execution action)
                - expected_behavior: Expected behavior (for validate_execution action)
                
        Returns:
            Dictionary containing validation results
        """
        action = input_data.get("action", "validate")
        
        if action == "validate":
            return await self.validate(
                artifact=input_data.get("artifact", ""),
                artifact_type=input_data.get("artifact_type", "code"),
                requirements=input_data.get("requirements", ""),
                context=input_data.get("context"),
            )
        elif action == "validate_execution":
            return await self.validate_execution(
                code=input_data.get("code", ""),
                execution_result=input_data.get("execution_result", {}),
                expected_behavior=input_data.get("expected_behavior", ""),
            )
        else:
            # Default: validate
            return await self.validate(
                artifact=input_data.get("artifact", ""),
                artifact_type=input_data.get("artifact_type", "code"),
                requirements=input_data.get("requirements", ""),
                context=input_data.get("context"),
            )
