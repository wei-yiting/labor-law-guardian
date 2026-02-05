"""Unit tests for PromptTemplateRegistry."""

import pytest
from pathlib import Path

from app.prompt_manager import PromptTemplateRegistry


class TestPromptRegistry:
    """Test suite for PromptTemplateRegistry."""

    def test_registry_initialization(self):
        """Test registry can load manifest."""
        registry = PromptTemplateRegistry(app_env="dev")
        assert registry._app_env == "dev"

    def test_registry_initialization_default_env(self):
        """Test registry defaults to prod environment."""
        registry = PromptTemplateRegistry()
        assert registry._app_env in ["dev", "prod"]  # Depends on APP_ENV or defaults to prod

    def test_load_prompt_l3_generation(self):
        """Test loading Level 3 generation prompt template."""
        registry = PromptTemplateRegistry(app_env="dev")
        prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")

        assert prompt is not None
        # Test invocation
        result = prompt.invoke({
            "questions_count": 5,
            "context_law_chunks": "Test context",
            "user_instructions": "Test instructions"
        })
        assert len(result.messages) > 0

    def test_load_prompt_l3_judge(self):
        """Test loading Level 3 judge prompt template."""
        registry = PromptTemplateRegistry(app_env="dev")
        prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_judge_rerank")

        assert prompt is not None
        # Test invocation
        result = prompt.invoke({
            "final_question_count": 10,
            "candidate_questions": '[]',
            "context_law_chunks": "Test context",
            "user_instructions": "Test instructions"
        })
        assert len(result.messages) > 0

    def test_cache_mechanism(self):
        """Test prompt caching works."""
        registry = PromptTemplateRegistry()
        p1 = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
        p2 = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
        assert p1 is p2  # Same object reference

    def test_clear_cache(self):
        """Test cache clearing."""
        registry = PromptTemplateRegistry()
        p1 = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
        registry.clear_cache()
        p2 = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
        # After cache clear, should load new instance
        assert p1 is not p2

    def test_invalid_task_name(self):
        """Test error handling for unknown tasks."""
        registry = PromptTemplateRegistry()
        with pytest.raises(ValueError, match="Unknown task"):
            registry.get_prompt_template("nonexistent_task")

    def test_list_tasks(self):
        """Test listing all available tasks."""
        registry = PromptTemplateRegistry()
        tasks = registry.list_tasks()
        assert "retrieval_eval_dataset_l3_candidate_gen" in tasks
        assert "retrieval_eval_dataset_l3_judge_rerank" in tasks
        assert "retrieval_eval_dataset_l1_candidate_gen" in tasks
        assert len(tasks) == 3

    def test_get_task_info(self):
        """Test retrieving task metadata."""
        registry = PromptTemplateRegistry()
        info = registry.get_task_info("retrieval_eval_dataset_l3_candidate_gen")
        assert info["description"] == "Level 3 Multi-Hop question generation"
        assert info["category"] == "eval_generation"
        assert "dev" in info

    def test_get_task_info_invalid(self):
        """Test error handling for invalid task info request."""
        registry = PromptTemplateRegistry()
        with pytest.raises(ValueError, match="Unknown task"):
            registry.get_task_info("nonexistent_task")

    def test_manifest_validation(self):
        """Test manifest schema validation."""
        registry = PromptTemplateRegistry()
        manifest = registry._load_manifest()
        assert "prompts" in manifest
        assert len(manifest["prompts"]) == 3

    def test_prompt_path_resolution_dev(self):
        """Test prompt path resolution in dev mode."""
        registry = PromptTemplateRegistry(app_env="dev")
        path = registry._resolve_prompt_path("retrieval_eval_dataset_l3_candidate_gen")
        assert path.exists()
        assert path.suffix == ".prompty"

    def test_prompt_path_resolution_prod(self):
        """Test prompt path resolution in prod mode."""
        registry = PromptTemplateRegistry(app_env="prod")
        path = registry._resolve_prompt_path("retrieval_eval_dataset_l3_candidate_gen")
        assert path.exists()
        assert path.suffix == ".prompty"

    def test_multiple_prompts_loading(self):
        """Test loading multiple prompts in sequence."""
        registry = PromptTemplateRegistry()
        tasks = ["retrieval_eval_dataset_l3_candidate_gen", "retrieval_eval_dataset_l3_judge_rerank"]

        for task in tasks:
            prompt = registry.get_prompt_template(task)
            assert prompt is not None

    def test_prompt_invocation_with_variables(self):
        """Test prompt invocation with actual variables."""
        registry = PromptTemplateRegistry()
        prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")

        result = prompt.invoke({
            "questions_count": 15,
            "context_law_chunks": "勞動基準法第32條規定...",
            "user_instructions": "請特別注意違法與罰則的關聯"
        })

        assert result is not None
        assert len(result.messages) == 2  # system + user
        # Check that variables were substituted
        system_msg = str(result.messages[0].content)
        assert "15" in system_msg  # questions_count substituted
        assert "勞動基準法" in system_msg  # context substituted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
