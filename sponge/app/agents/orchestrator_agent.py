"""
Orchestrator Agent - Main coordinator for multi-agent workflows

This agent implements the "orchestrator-worker" pattern from Anthropic/Google/OpenAI.
It holds the complete task intent, decomposes tasks, coordinates workers, and synthesizes results.

Key principles:
- Single source of truth for task intent
- Dynamic task decomposition (not fixed roles)
- Results flow back to orchestrator (not passed to next agent)
- Uses external state files for continuity across sessions
"""

from typing import Any, Dict, List, Optional
import json
from datetime import datetime
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from .base_agent import BaseAgent
from ..core.task_progress import TaskProgress


class OrchestratorAgent(BaseAgent):
    """
    Main orchestrator agent that coordinates all sub-tasks.
    
    This replaces the old "Planner" role but with key differences:
    - Maintains continuous ownership of the task (doesn't hand off)
    - Reads/writes external state files for continuity
    - Dynamically creates worker tasks based on current needs
    - Synthesizes all results back into unified context
    """
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        task_id: str,
        name: str = "Orchestrator",
        workspace_root: Optional[str] = None,
    ):
        super().__init__(
            llm=llm,
            name=name,
            role="orchestrator",
        )
        
        self.task_id = task_id
        self.task_progress = TaskProgress(task_id, workspace_root)
        
        logger.info(f"Orchestrator initialized for task {task_id}")
    
    def _default_system_prompt(self) -> str:
        return """You are an expert software engineering orchestrator agent.

Your role is to:
1. Hold complete understanding of the task goal and constraints
2. Break down complex tasks into independent sub-tasks that can be executed in parallel
3. Coordinate worker agents to execute sub-tasks
4. Synthesize results from all workers back into a coherent solution
5. Continuously monitor progress and adapt the plan as needed

Critical Principles:
- NEVER delegate task ownership - you remain responsible for the final outcome
- Sub-tasks should be INDEPENDENT when possible (enables parallel execution)
- Always read the task specification before making decisions
- Record reasoning for key decisions in the task progress log
- When receiving results from workers, integrate them into the full context
- If issues are found, create new sub-tasks to fix them (don't pass to another agent)

You have access to:
- Task specification (immutable goal)
- Execution history (all completed steps with reasoning)
- Current status (latest progress)
- Known issues (problems to avoid)

Output your decisions as JSON with clear structure."""

    async def initialize_task(
        self,
        description: str,
        language: str = "python",
        constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a new task with specification
        
        This is called once at the beginning to set up the external state files.
        """
        logger.info(f"[Orchestrator] Initializing task: {description[:100]}...")
        
        # Write immutable task spec
        self.task_progress.write_spec(
            goal=description,
            constraints=constraints or [],
            metadata={
                "language": language,
                "created_at": datetime.utcnow().isoformat(),
                **(metadata or {}),
            },
        )
        
        # Record initialization step
        self.task_progress.add_completed_step(
            step_number=0,
            description="Task initialized by Orchestrator",
            outcome="Task specification written to external state",
            reasoning=f"Initial approach: Analyze requirements and create execution strategy for {language} implementation",
        )
        
        # Update current status
        self.task_progress.update_current_status(
            current_step="initialization",
            status="complete",
            details={"next_action": "analyze_and_decompose"},
            last_updated_by=self.name,
        )
        
        return {
            "status": "initialized",
            "task_id": self.task_id,
            "goal": description,
            "language": language,
        }

    async def analyze_and_decompose(self) -> Dict[str, Any]:
        """
        Analyze the task and decompose into sub-tasks
        
        Returns a list of independent sub-tasks that can be executed by workers.
        """
        # Read current state
        spec = self.task_progress.read_spec()
        if not spec:
            raise ValueError("Task specification not found - call initialize_task first")
        
        # Build context for analysis
        context = self._build_full_context()
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""{context}

TASK: Analyze the above task and decompose it into independent sub-tasks.

For each sub-task, specify:
- subtask_id: Unique identifier
- description: Clear description of what needs to be done
- type: One of [research, implementation, validation, testing, documentation]
- dependencies: List of subtask_ids this depends on (empty if independent)
- estimated_complexity: low/medium/high
- can_parallelize: Boolean indicating if this can run in parallel with others

Return ONLY valid JSON with this structure:
{{
    "analysis_summary": "Brief analysis of the task",
    "subtasks": [
        {{
            "subtask_id": "ST-001",
            "description": "...",
            "type": "...",
            "dependencies": [],
            "estimated_complexity": "...",
            "can_parallelize": true
        }}
    ],
    "execution_order": ["ST-001", "ST-002"],
    "parallel_groups": [["ST-001", "ST-003"], ["ST-002"]]
}}"""),
        ]
        
        response = await self._invoke_llm(messages)
        
        # Parse response
        subtasks_data = self._parse_json_response(response)
        
        # Record this planning step
        self.task_progress.add_completed_step(
            step_number=len(self.task_progress.get_completed_steps()),
            description="Task decomposition completed",
            outcome=f"Created {len(subtasks_data.get('subtasks', []))} sub-tasks",
            reasoning=subtasks_data.get('analysis_summary', ''),
            artifacts={"subtasks": json.dumps(subtasks_data)},
        )
        
        return subtasks_data

    async def execute_subtask(
        self,
        subtask_id: str,
        subtask_description: str,
        subtask_type: str,
    ) -> Dict[str, Any]:
        """
        Execute a single sub-task using a worker agent
        
        The worker is generic - it's defined by the task, not by a fixed role.
        """
        logger.info(f"[Orchestrator] Executing sub-task {subtask_id}: {subtask_description[:50]}...")
        
        # Update status
        self.task_progress.update_current_status(
            current_step=subtask_id,
            status="in_progress",
            details={"subtask_type": subtask_type},
            last_updated_by=self.name,
        )
        
        # Get full context including known issues
        context = self._build_full_context()
        
        # Create worker prompt based on subtask type
        worker_prompt = self._create_worker_prompt(subtask_type, subtask_description, context)
        
        messages = [
            SystemMessage(content=worker_prompt),
            HumanMessage(content=f"Execute this sub-task: {subtask_description}"),
        ]
        
        response = await self._invoke_llm(messages)
        
        # Parse result
        result = self._parse_worker_result(response, subtask_type)
        
        # Record completion
        self.task_progress.add_completed_step(
            step_number=len(self.task_progress.get_completed_steps()),
            description=f"Completed sub-task {subtask_id}",
            outcome=result.get('outcome', 'Sub-task executed'),
            reasoning=result.get('reasoning', ''),
            artifacts=result.get('artifacts', {}),
        )
        
        # Update status
        self.task_progress.update_current_status(
            current_step=subtask_id,
            status="complete",
            details={"result_summary": result.get('outcome', '')},
            last_updated_by=self.name,
        )
        
        return result

    async def synthesize_results(self) -> Dict[str, Any]:
        """
        Synthesize all completed sub-task results into final solution
        
        This is where the orchestrator combines all worker outputs.
        """
        logger.info("[Orchestrator] Synthesizing final results...")
        
        context = self._build_full_context()
        
        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"""{context}

TASK: Synthesize all completed work into a final solution.

Provide:
1. Final solution summary
2. Key files/artifacts produced
3. Verification that all requirements are met
4. Any remaining issues or future improvements

Return JSON with:
{{
    "solution_summary": "...",
    "artifacts": [...],
    "requirements_met": true/false,
    "remaining_issues": [...],
    "final_code": "..." (if applicable)
}}"""),
        ]
        
        response = await self._invoke_llm(messages)
        synthesis = self._parse_json_response(response)
        
        # Mark task as complete
        self.task_progress.update_current_status(
            current_step="synthesis",
            status="complete",
            details={"final_summary": synthesis.get('solution_summary', '')},
            last_updated_by=self.name,
        )
        
        return synthesis

    async def handle_validation_feedback(
        self,
        validation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle feedback from validator agent
        
        Unlike the old Reviewer that would "pass along" work,
        the orchestrator receives validation feedback and decides
        whether to create new sub-tasks for fixes.
        """
        if validation_result.get('passed', True):
            logger.info("[Orchestrator] Validation passed, continuing...")
            return {"action": "continue", "issues": []}
        
        # Validation found issues - create fix sub-tasks
        issues = validation_result.get('issues', [])
        critical_issues = validation_result.get('critical_issues', [])
        
        logger.warning(f"[Orchestrator] Validation found {len(issues)} issues, {len(critical_issues)} critical")
        
        # Record known issues
        for issue in critical_issues:
            self.task_progress.add_known_issue(
                issue=issue.get('description', 'Unknown issue'),
                workaround=issue.get('suggested_fix'),
                severity="critical",
                discovered_at_step=len(self.task_progress.get_completed_steps()),
            )
        
        # Return action plan
        return {
            "action": "fix_required",
            "issues": issues,
            "critical_count": len(critical_issues),
            "suggested_fixes": [i.get('suggested_fix') for i in critical_issues],
        }

    def _build_full_context(self) -> str:
        """Build complete context string from external state files"""
        return self.task_progress.get_full_context_for_agent()

    def _create_worker_prompt(self, subtask_type: str, description: str, context: str) -> str:
        """Create specialized prompt for different sub-task types"""
        
        base_prompts = {
            "research": """You are a research specialist. Your task is to investigate and gather information.
Focus on thorough exploration and accurate documentation of findings.""",
            
            "implementation": """You are an implementation specialist. Your task is to write high-quality code.
Focus on correctness, readability, and following best practices.""",
            
            "validation": """You are a validation specialist. Your task is to verify correctness.
Focus on identifying any issues, gaps, or problems.""",
            
            "testing": """You are a testing specialist. Your task is to create and execute tests.
Focus on edge cases, error handling, and comprehensive coverage.""",
            
            "documentation": """You are a documentation specialist. Your task is to create clear documentation.
Focus on clarity, completeness, and usability.""",
        }
        
        base = base_prompts.get(subtask_type, """You are a specialized worker agent.""")
        
        return f"""{base}

IMPORTANT CONTEXT FROM ORCHESTRATOR:
{context}

Your specific task: {description}

Work within this context and produce results that will be synthesized by the orchestrator."""

    def _parse_worker_result(self, response: str, subtask_type: str) -> Dict[str, Any]:
        """Parse worker agent response"""
        try:
            data = self._parse_json_response(response)
            return {
                "outcome": data.get('outcome', 'Completed'),
                "reasoning": data.get('reasoning', ''),
                "artifacts": data.get('artifacts', {}),
                "raw_response": response,
            }
        except Exception:
            return {
                "outcome": "Completed with text response",
                "reasoning": "Response was not structured JSON",
                "artifacts": {"response": response[:1000]},
                "raw_response": response,
            }

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response"""
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {"raw_text": response}
        except json.JSONDecodeError:
            return {"raw_text": response}

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the orchestrator's main workflow
        
        This method satisfies the BaseAgent abstract method requirement.
        It delegates to the appropriate orchestrator method based on input.
        
        Args:
            input_data: Dictionary containing:
                - action: The action to perform (initialize, decompose, execute_subtask, synthesize)
                - Other parameters depending on the action
                
        Returns:
            Dictionary containing execution results
        """
        action = input_data.get("action", "decompose")
        
        if action == "initialize":
            return await self.initialize_task(
                description=input_data.get("description", ""),
                language=input_data.get("language", "python"),
                constraints=input_data.get("constraints"),
                metadata=input_data.get("metadata"),
            )
        elif action == "decompose":
            return await self.analyze_and_decompose()
        elif action == "execute_subtask":
            return await self.execute_subtask(
                subtask_id=input_data.get("subtask_id", ""),
                subtask_description=input_data.get("subtask_description", ""),
                subtask_type=input_data.get("subtask_type", "general"),
            )
        elif action == "synthesize":
            return await self.synthesize_results()
        elif action == "handle_validation":
            return await self.handle_validation_feedback(
                validation_result=input_data.get("validation_result", {}),
            )
        else:
            # Default: analyze and decompose
            return await self.analyze_and_decompose()
