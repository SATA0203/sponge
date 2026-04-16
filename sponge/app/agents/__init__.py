"""
Sponge Agents Module - Orchestrator-Worker Architecture

This module implements the orchestrator-worker pattern for AI agent systems,
following best practices from Anthropic, OpenAI, and Google.

ARCHITECTURE PRINCIPLES:
- OrchestratorAgent: Main coordinator holding complete task intent
- WorkerAgent: Generic executor for sub-tasks (no fixed roles)
- ValidatorAgent: Pure adversarial verifier (finds problems only, doesn't fix)
- TaskProgress: External state management for continuity across sessions

KEY DIFFERENCES FROM ROLE-BASED ARCHITECTURE:
- No "PM/Dev/QA" role labels that create artificial boundaries
- Information flows back to orchestrator, not passed down a pipeline
- State is persisted externally (spec.md, history.jsonl), not in memory
- Validation is adversarial, not a handoff to the next stage
"""

from .base_agent import BaseAgent

# New architecture components
from .orchestrator_agent import OrchestratorAgent
from .worker_agent import WorkerAgent
from .validator_agent import ValidatorAgent

__all__ = [
    # Base
    "BaseAgent",

    # Orchestrator-Worker Architecture
    "OrchestratorAgent",
    "WorkerAgent",
    "ValidatorAgent",
]
