"""Test script to verify prompt registry integration."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.prompt_manager import PromptTemplateRegistry

def test_prompt_loading():
    """Test that prompts can be loaded successfully."""
    print("=" * 60)
    print("Testing Prompt Registry Integration")
    print("=" * 60)

    # Initialize registry
    print("\n1. Initializing PromptTemplateRegistry...")
    registry = PromptTemplateRegistry()
    print("✓ Registry initialized")

    # List available tasks
    print("\n2. Listing available tasks...")
    tasks = registry.list_tasks()
    print(f"✓ Found {len(tasks)} tasks:")
    for task in tasks:
        print(f"   - {task}")

    # Test loading each prompt
    print("\n3. Loading prompt templates...")
    for task in ["retrieval_eval_dataset_l3_candidate_gen", "retrieval_eval_dataset_l3_judge_rerank"]:
        try:
            prompt = registry.get_prompt_template(task)
            print(f"✓ Loaded '{task}' (type: {type(prompt).__name__})")

            # Test invocation
            if task == "retrieval_eval_dataset_l3_candidate_gen":
                result = prompt.invoke({
                    "questions_count": 5,
                    "context_law_chunks": "Test context",
                    "user_instructions": "No specific instructions"
                })
                print(f"  └─ Invocation successful, generated {len(result.messages)} messages")

        except Exception as e:
            print(f"✗ Failed to load '{task}': {e}")
            return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_prompt_loading()
    sys.exit(0 if success else 1)
