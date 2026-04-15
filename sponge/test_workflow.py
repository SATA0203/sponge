#!/usr/bin/env python3
"""Test workflow execution end-to-end"""

import asyncio
from app.workflow import get_workflow_manager


async def test_workflow():
    """Test the workflow with a simple task"""
    print("Initializing workflow manager...")
    wm = get_workflow_manager()
    
    print("\nExecuting workflow for task: 'Print hello world'")
    result = await wm.execute(
        description="Print hello world",
        language="python",
        max_iterations=1,
    )
    
    print(f"\nWorkflow completed with status: {result.get('status')}")
    print(f"Iterations: {result.get('iterations', 0)}")
    
    if result.get("error"):
        print(f"Error: {result['error']}")
    
    if result.get("plan"):
        print(f"\nPlan summary: {result['plan'].get('summary', '')}")
    
    if result.get("code"):
        code_data = result["code"]
        print(f"\nGenerated code ({len(code_data.get('code', ''))} chars):")
        print("-" * 40)
        print(code_data.get("code", "")[:500])
        print("-" * 40)
    
    if result.get("execution_result"):
        exec_result = result["execution_result"]
        print(f"\nExecution result:")
        print(f"  Success: {exec_result.get('success', False)}")
        if exec_result.get("output"):
            print(f"  Output: {exec_result['output'][:200]}")
        if exec_result.get("error"):
            print(f"  Error: {exec_result['error'][:200]}")
    
    if result.get("review_result"):
        review = result["review_result"]
        print(f"\nReview result:")
        print(f"  Passed: {review.get('passed', False)}")
        print(f"  Score: {review.get('score', 0)}/10")
    
    return result


if __name__ == "__main__":
    asyncio.run(test_workflow())
