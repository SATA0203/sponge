"""
Task Progress Manager - External state management for multi-agent workflows

This module implements the external state system as described in the architecture refactor plan.
It replaces the in-memory WorkflowState with persistent markdown files that maintain:
1. Task Goal (immutable, prevents drift)
2. Completed Steps (append-only history)
3. Current Status (overwrite, reflects latest progress)
4. Known Issues (append-only, avoids repeating mistakes)

Key principles:
- Information is accumulated, not compressed and passed
- Same role reads and writes state (different points in time)
- Reasoning chain continuity via external files, not model memory
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger


class TaskProgress:
    """
    Manages persistent task state using external markdown files.
    
    This class implements the "external state" pattern from Anthropic/OpenAI/Google,
    where reasoning chain continuity is maintained through files rather than model context.
    """
    
    def __init__(self, task_id: str, workspace_root: Optional[str] = None):
        """
        Initialize task progress manager
        
        Args:
            task_id: Unique task identifier
            workspace_root: Root directory for state files (default: ./task_states/{task_id})
        """
        self.task_id = task_id
        self.workspace_root = Path(workspace_root) if workspace_root else Path(f"./task_states/{task_id}")
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # File paths for different state components
        self.spec_file = self.workspace_root / "spec.md"
        self.progress_file = self.workspace_root / "task_progress.md"
        self.history_file = self.workspace_root / "history.jsonl"  # Append-only event log
        self.checkpoints_dir = self.workspace_root / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
        
        logger.info(f"TaskProgress initialized for task {task_id} at {self.workspace_root}")
    
    # ========== Task Goal (Immutable) ==========
    
    def write_spec(self, goal: str, constraints: Optional[List[str]] = None, metadata: Optional[Dict] = None):
        """
        Write the immutable task specification
        
        Args:
            goal: Primary task objective
            constraints: List of constraints or requirements
            metadata: Additional metadata (language, dependencies, etc.)
        """
        content = f"""# Task Specification

## Goal
{goal}

## Constraints
"""
        if constraints:
            for constraint in constraints:
                content += f"- {constraint}\n"
        else:
            content += "- None specified\n"
        
        if metadata:
            content += "\n## Metadata\n"
            for key, value in metadata.items():
                content += f"- **{key}**: {value}\n"
        
        content += f"\n---\n*Created: {datetime.utcnow().isoformat()}*\n"
        content += "*This file should NOT be modified during task execution*\n"
        
        self.spec_file.write_text(content)
        logger.info(f"Wrote task spec to {self.spec_file}")
    
    def read_spec(self) -> Optional[Dict[str, Any]]:
        """Read the task specification"""
        if not self.spec_file.exists():
            return None
        
        content = self.spec_file.read_text()
        # Simple parsing - could be enhanced with proper markdown parser
        lines = content.split('\n')
        result = {"raw_content": content}
        
        current_section = None
        for line in lines:
            if line.startswith("## Goal"):
                current_section = "goal"
            elif line.startswith("## Constraints"):
                current_section = "constraints"
                result["constraints"] = []
            elif line.startswith("## Metadata"):
                current_section = "metadata"
                result["metadata"] = {}
            elif current_section == "goal" and line.strip() and not line.startswith("#"):
                result["goal"] = line.strip()
            elif current_section == "constraints" and line.startswith("- "):
                result["constraints"].append(line[2:])
            elif current_section == "metadata" and line.startswith("- **"):
                parts = line.replace("- **", "").split("**: ")
                if len(parts) == 2:
                    result["metadata"][parts[0]] = parts[1]
        
        return result
    
    # ========== Completed Steps (Append-only) ==========
    
    def add_completed_step(
        self,
        step_number: int,
        description: str,
        outcome: str,
        artifacts: Optional[Dict[str, str]] = None,
        reasoning: Optional[str] = None,
    ):
        """
        Add a completed step to the append-only history
        
        Args:
            step_number: Sequential step number
            description: What was done
            outcome: Result of the step
            artifacts: Paths to generated files or outputs
            reasoning: Key reasoning decisions (critical for continuity!)
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "step_number": step_number,
            "description": description,
            "outcome": outcome,
            "artifacts": artifacts or {},
            "reasoning": reasoning or "",
        }
        
        # Append to JSONL history file
        with open(self.history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        # Also update the markdown progress file
        self._update_progress_markdown()
        
        logger.info(f"Added completed step {step_number}: {description[:50]}...")
    
    def get_completed_steps(self) -> List[Dict[str, Any]]:
        """Get all completed steps from history"""
        if not self.history_file.exists():
            return []
        
        steps = []
        with open(self.history_file, "r") as f:
            for line in f:
                if line.strip():
                    steps.append(json.loads(line))
        
        return sorted(steps, key=lambda x: x.get("step_number", 0))
    
    # ========== Current Status (Overwrite) ==========
    
    def update_current_status(
        self,
        current_step: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        last_updated_by: Optional[str] = None,
    ):
        """
        Update the current status (overwrites previous status)
        
        Args:
            current_step: Name/description of current step
            status: Status string (e.g., "in_progress", "blocked", "complete")
            details: Additional status details
            last_updated_by: Which agent/component updated this
        """
        status_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "current_step": current_step,
            "status": status,
            "details": details or {},
            "last_updated_by": last_updated_by or "unknown",
        }
        
        # Save as JSON for easy parsing
        status_file = self.workspace_root / "current_status.json"
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)
        
        # Also update markdown view
        self._update_progress_markdown()
        
        logger.debug(f"Updated current status: {status} at {current_step}")
    
    def get_current_status(self) -> Optional[Dict[str, Any]]:
        """Get current status"""
        status_file = self.workspace_root / "current_status.json"
        if not status_file.exists():
            return None
        
        with open(status_file, "r") as f:
            return json.load(f)
    
    # ========== Known Issues (Append-only) ==========
    
    def add_known_issue(
        self,
        issue: str,
        workaround: Optional[str] = None,
        severity: str = "medium",
        discovered_at_step: Optional[int] = None,
    ):
        """
        Add a known issue to avoid repeating mistakes
        
        Args:
            issue: Description of the problem
            workaround: How to work around it (if known)
            severity: low/medium/high/critical
            discovered_at_step: Step number where issue was found
        """
        issues_file = self.workspace_root / "known_issues.json"
        
        issues = []
        if issues_file.exists():
            with open(issues_file, "r") as f:
                issues = json.load(f)
        
        new_issue = {
            "timestamp": datetime.utcnow().isoformat(),
            "issue": issue,
            "workaround": workaround,
            "severity": severity,
            "discovered_at_step": discovered_at_step,
            "status": "open" if not workaround else "resolved",
        }
        
        issues.append(new_issue)
        
        with open(issues_file, "w") as f:
            json.dump(issues, f, indent=2)
        
        self._update_progress_markdown()
        
        logger.warning(f"Added known issue: {issue[:50]}... (severity: {severity})")
    
    def get_known_issues(self) -> List[Dict[str, Any]]:
        """Get all known issues"""
        issues_file = self.workspace_root / "known_issues.json"
        if not issues_file.exists():
            return []
        
        with open(issues_file, "r") as f:
            return json.load(f)
    
    # ========== Checkpoint Management ==========
    
    def save_checkpoint(self, checkpoint_name: str, state_snapshot: Dict[str, Any]):
        """
        Save a complete state snapshot as a checkpoint
        
        Args:
            checkpoint_name: Name for this checkpoint
            state_snapshot: Complete state to save
        """
        checkpoint_file = self.checkpoints_dir / f"{checkpoint_name}.json"
        
        checkpoint_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "checkpoint_name": checkpoint_name,
            "state": state_snapshot,
        }
        
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2)
        
        logger.info(f"Saved checkpoint: {checkpoint_name}")
    
    def load_checkpoint(self, checkpoint_name: str) -> Optional[Dict[str, Any]]:
        """Load a checkpoint by name"""
        checkpoint_file = self.checkpoints_dir / f"{checkpoint_name}.json"
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file, "r") as f:
            data = json.load(f)
            return data.get("state")
    
    def list_checkpoints(self) -> List[str]:
        """List available checkpoint names"""
        if not self.checkpoints_dir.exists():
            return []
        
        return [f.stem for f in self.checkpoints_dir.glob("*.json")]
    
    # ========== Helper Methods ==========
    
    def _update_progress_markdown(self):
        """Update the human-readable progress markdown file"""
        spec = self.read_spec()
        steps = self.get_completed_steps()
        status = self.get_current_status()
        issues = self.get_known_issues()
        
        content = f"""# Task Progress: {self.task_id}

## Current Status
"""
        if status:
            content += f"- **Step**: {status.get('current_step', 'Unknown')}\n"
            content += f"- **Status**: {status.get('status', 'Unknown')}\n"
            content += f"- **Updated**: {status.get('timestamp', 'Unknown')}\n"
            if status.get('details'):
                content += f"- **Details**: {json.dumps(status['details'], indent=2)}\n"
        else:
            content += "- Not started\n"
        
        content += f"\n## Task Goal\n"
        if spec and spec.get('goal'):
            content += f"{spec['goal']}\n"
        else:
            content += "*No spec defined*\n"
        
        content += f"\n## Completed Steps ({len(steps)})\n"
        if steps:
            for step in steps:
                content += f"### Step {step.get('step_number', '?')}\n"
                content += f"- **Description**: {step.get('description', '')}\n"
                content += f"- **Outcome**: {step.get('outcome', '')}\n"
                content += f"- **Timestamp**: {step.get('timestamp', '')}\n"
                if step.get('reasoning'):
                    content += f"- **Reasoning**: {step.get('reasoning', '')}\n"
                if step.get('artifacts'):
                    content += f"- **Artifacts**: {json.dumps(step['artifacts'])}\n"
                content += "\n"
        else:
            content += "*No steps completed yet*\n"
        
        content += f"\n## Known Issues ({len(issues)})\n"
        if issues:
            for issue in issues:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    issue.get('severity', 'medium'), "⚪"
                )
                content += f"- {severity_icon} **{issue.get('issue', '')}**\n"
                if issue.get('workaround'):
                    content += f"  - Workaround: {issue['workaround']}\n"
                content += f"  - Status: {issue.get('status', 'open')}\n"
        else:
            content += "*No known issues*\n"
        
        content += f"\n---\n*Last updated: {datetime.utcnow().isoformat()}*\n"
        
        self.progress_file.write_text(content)
    
    def get_full_context_for_agent(self) -> str:
        """
        Get the complete context string to pass to an agent.
        
        This is the key method that replaces the old WorkflowState passing.
        Instead of compressing information into a dict, we provide the full
        reasoning history and current state.
        
        Returns:
            Formatted context string for agent prompts
        """
        spec = self.read_spec()
        steps = self.get_completed_steps()
        status = self.get_current_status()
        issues = self.get_known_issues()
        
        context_parts = []
        
        # 1. Task Goal (always first, anchors the agent)
        context_parts.append("=" * 60)
        context_parts.append("TASK SPECIFICATION (DO NOT DEVIATE)")
        context_parts.append("=" * 60)
        if spec:
            context_parts.append(f"Goal: {spec.get('goal', 'Not specified')}")
            if spec.get('constraints'):
                context_parts.append("\nConstraints:")
                for c in spec['constraints']:
                    context_parts.append(f"  - {c}")
            if spec.get('metadata'):
                context_parts.append("\nMetadata:")
                for k, v in spec['metadata'].items():
                    context_parts.append(f"  - {k}: {v}")
        else:
            context_parts.append("WARNING: No task specification found!")
        
        # 2. Execution History (preserves reasoning chain)
        context_parts.append("\n" + "=" * 60)
        context_parts.append("EXECUTION HISTORY (PREVIOUS WORK)")
        context_parts.append("=" * 60)
        if steps:
            for step in steps:
                context_parts.append(f"\n[Step {step.get('step_number', '?')}] {step.get('description', '')}")
                context_parts.append(f"  Outcome: {step.get('outcome', '')}")
                if step.get('reasoning'):
                    context_parts.append(f"  Key Reasoning: {step.get('reasoning', '')}")
                if step.get('artifacts'):
                    context_parts.append(f"  Artifacts: {step.get('artifacts')}")
        else:
            context_parts.append("No previous steps - this is the first step.")
        
        # 3. Known Issues (prevents repeating mistakes)
        context_parts.append("\n" + "=" * 60)
        context_parts.append("KNOWN ISSUES (AVOID THESE PROBLEMS)")
        context_parts.append("=" * 60)
        if issues:
            for issue in issues:
                severity = issue.get('severity', 'medium').upper()
                context_parts.append(f"\n[{severity}] {issue.get('issue', '')}")
                if issue.get('workaround'):
                    context_parts.append(f"  Workaround: {issue['workaround']}")
        else:
            context_parts.append("No known issues.")
        
        # 4. Current Status
        context_parts.append("\n" + "=" * 60)
        context_parts.append("CURRENT STATUS")
        context_parts.append("=" * 60)
        if status:
            context_parts.append(f"Current Step: {status.get('current_step', 'Unknown')}")
            context_parts.append(f"Status: {status.get('status', 'Unknown')}")
            if status.get('details'):
                context_parts.append(f"Details: {json.dumps(status['details'])}")
        else:
            context_parts.append("Status not set.")
        
        return "\n".join(context_parts)
    
    def cleanup(self):
        """Clean up temporary files (optional maintenance)"""
        # Keep spec and progress files, but can clean old checkpoints
        import shutil
        if self.checkpoints_dir.exists():
            # Remove checkpoints older than 7 days (example policy)
            cutoff = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)
            for checkpoint_file in self.checkpoints_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff:
                    checkpoint_file.unlink()
                    logger.debug(f"Removed old checkpoint: {checkpoint_file.name}")


# Factory function for easy creation
def create_task_progress(task_id: str, workspace_root: Optional[str] = None) -> TaskProgress:
    """Create a new TaskProgress instance"""
    return TaskProgress(task_id, workspace_root)
