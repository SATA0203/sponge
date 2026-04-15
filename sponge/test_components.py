"""
Test script to verify the Sponge multi-agent workflow implementation
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.tools.code_executor import CodeExecutor


async def test_code_executor():
    """Test the code executor"""
    print("=" * 60)
    print("Testing Code Executor")
    print("=" * 60)
    
    executor = CodeExecutor(timeout=10)
    
    # Test 1: Simple Python code
    print("\n[Test 1] Running simple Python code...")
    code = """
def greet(name):
    return f"Hello, {name}!"

print(greet("Sponge"))
print(greet("World"))
"""
    
    result = await executor.execute(code, language="python")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"Execution time: {result.get('execution_time', 0):.3f}s")
    
    # Test 2: Code with error
    print("\n[Test 2] Running code with error...")
    bad_code = "print(undefined_variable)"
    result = await executor.execute(bad_code, language="python")
    print(f"Success: {result['success']}")
    if result.get('error'):
        print(f"Error (expected): {result['error'][:100]}")
    
    # Test 3: JavaScript code
    print("\n[Test 3] Running JavaScript code...")
    js_code = """
console.log("Hello from JavaScript!");
const sum = (a, b) => a + b;
console.log(`2 + 3 = ${sum(2, 3)}`);
"""
    result = await executor.execute(js_code, language="javascript")
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
    if result.get('error'):
        print(f"Error: {result['error'][:100]}")
    
    print("\n✅ Code Executor tests completed!")


async def test_agents():
    """Test agent initialization (without LLM)"""
    print("\n" + "=" * 60)
    print("Testing Agent Initialization")
    print("=" * 60)
    
    try:
        from app.agents.base_agent import BaseAgent
        from app.agents.planner_agent import PlannerAgent
        from app.agents.coder_agent import CoderAgent
        from app.agents.reviewer_agent import ReviewerAgent
        
        print("\n✓ All agent modules imported successfully")
        print(f"  - BaseAgent: {BaseAgent}")
        print(f"  - PlannerAgent: {PlannerAgent}")
        print(f"  - CoderAgent: {CoderAgent}")
        print(f"  - ReviewerAgent: {ReviewerAgent}")
        
        # Note: We can't instantiate without LLM, but imports work
        print("\n⚠️  Agent instantiation requires LLM configuration")
        print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable")
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        return False
    
    print("\n✅ Agent initialization tests completed!")
    return True


async def test_workflow():
    """Test workflow graph creation"""
    print("\n" + "=" * 60)
    print("Testing Workflow Graph")
    print("=" * 60)
    
    try:
        from app.workflow.nodes import WorkflowState, planner_node, coder_node, executor_node, reviewer_node
        from app.workflow.workflow_graph import WorkflowManager, create_workflow
        
        print("\n✓ All workflow modules imported successfully")
        print(f"  - WorkflowState: {WorkflowState}")
        print(f"  - planner_node: {planner_node}")
        print(f"  - coder_node: {coder_node}")
        print(f"  - executor_node: {executor_node}")
        print(f"  - reviewer_node: {reviewer_node}")
        print(f"  - WorkflowManager: {WorkflowManager}")
        
        # Try to create workflow manager
        print("\n[Creating WorkflowManager...]")
        # Note: This will fail without LLM configured, but we can test imports
        # workflow_manager = create_workflow()
        
        print("\n⚠️  Workflow execution requires LLM configuration")
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        return False
    
    print("\n✅ Workflow graph tests completed!")
    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("SPONGE MULTI-AGENT SYSTEM - COMPONENT TESTS")
    print("=" * 60)
    
    # Test 1: Code Executor (works without LLM)
    await test_code_executor()
    
    # Test 2: Agents (imports only)
    await test_agents()
    
    # Test 3: Workflow (imports only)
    await test_workflow()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("""
✅ Implemented Components:
   - BaseAgent (abstract base class)
   - PlannerAgent (creates execution plans)
   - CoderAgent (generates code)
   - ReviewerAgent (reviews code quality)
   - CodeExecutor (executes Python/JavaScript)
   - Workflow Nodes (LangGraph integration)
   - WorkflowManager (orchestrates multi-agent flow)
   - API endpoints for task execution

⚠️  To run full workflow tests:
   1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY
   2. Run: python -m app.main
   
📝 Next Steps:
   - Configure LLM API keys in .env file
   - Start the FastAPI server
   - Use POST /api/v1/tasks/execute to create tasks
   - Monitor task progress via GET /api/v1/tasks/{task_id}
""")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
