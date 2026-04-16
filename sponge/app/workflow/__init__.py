"""
Sponge Workflow Module - Orchestrator-Worker Architecture

This module implements the orchestrator-worker pattern for AI agent workflows,
following best practices from Anthropic, OpenAI, and Google.

ARCHITECTURE PRINCIPLES:
- Orchestrator holds complete task intent throughout execution
- Workers execute sub-tasks in parallel when possible
- Results flow back to orchestrator, not passed down a pipeline
- External state files (spec.md, history.jsonl) ensure continuity
- Validation is adversarial, finding problems without taking ownership

WORKFLOW STAGES:
1. Planning: Orchestrator decomposes task into sub-tasks
2. Delegating: Workers execute sub-tasks (can be parallel)
3. Synthesizing: Orchestrator combines results
4. Validating: Validator finds issues (doesn't fix)
"""

# Orchestrator-Worker workflow
from .orchestrator_workflow import OrchestratorWorkflow, run_workflow

__all__ = [
    "OrchestratorWorkflow",
    "run_workflow",
]
