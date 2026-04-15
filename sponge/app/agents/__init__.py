"""
Sponge Agents Module - Refactored for Orchestrator-Worker Architecture

This module now exports both legacy agents (for backward compatibility)
and new orchestrator-worker architecture components.

NEW ARCHITECTURE:
- OrchestratorAgent: Main coordinator holding complete task intent
- WorkerAgent: Generic executor for sub-tasks (replaces role-specific agents)
- ValidatorAgent: Pure adversarial verifier (finds problems only)
- TaskProgress: External state management for continuity

LEGACY AGENTS (deprecated, kept for migration):
- PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent
"""

from .base_agent import BaseAgent
from .planner_agent import PlannerAgent
from .coder_agent import CoderAgent
from .reviewer_agent import ReviewerAgent
from .tester_agent import TesterAgent

# New architecture components
from .orchestrator_agent import OrchestratorAgent
from .worker_agent import WorkerAgent
from .validator_agent import ValidatorAgent

__all__ = [
    # Base
    "BaseAgent",
    
    # Legacy agents (deprecated)
    "PlannerAgent",
    "CoderAgent",
    "ReviewerAgent",
    "TesterAgent",
    
    # New architecture
    "OrchestratorAgent",
    "WorkerAgent",
    "ValidatorAgent",
]