"""
Orchestrator Module - New architecture for multi-agent coordination

This module implements the Anthropic-style orchestrator-worker pattern:
- OrchestratorAgent: Holds complete task intent, coordinates workers
- WorkerAgent: Generic executor for sub-tasks (no fixed roles)
- ValidatorAgent: Pure adversarial validator (finds problems only)

Key differences from old workflow:
- No流水线 (assembly line) handoffs
- Results flow back to orchestrator, not to "next" agent
- External state (TaskProgress) maintains reasoning continuity
- Parallel exploration instead of sequential分工
"""

from .orchestrator_agent import OrchestratorAgent, WorkerAgent
from .validator_agent import ValidatorAgent

__all__ = [
    "OrchestratorAgent",
    "WorkerAgent", 
    "ValidatorAgent",
]
