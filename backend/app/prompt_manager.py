"""Prompt Management System using Microsoft Prompty format.

This module provides a Registry Pattern implementation for managing .prompty files
with environment-aware loading (dev/prod) and lazy caching.

Usage:
    from backend.app.prompt_manager import PromptTemplateRegistry

    registry = PromptTemplateRegistry()
    prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
    chain = prompt | model.with_structured_output(OutputSchema)
    result = chain.invoke({"questions_count": 15, ...})
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.runnables import Runnable
from langchain_prompty import create_chat_prompt


class PromptTemplateRegistry:
    """Registry for managing .prompty files with environment-aware loading.

    Features:
    - Loads prompts from manifest.json registry
    - Supports dev/prod environment switching via APP_ENV
    - Fresh loading on each call for iterative prompt development
    - Environment fallback: If requested env not configured, tries alternate env
    - Fallback auto-detection: In dev mode, searches for vN.prompty pattern as last resort

    Attributes:
        _prompts_dir: Path to prompts directory
        _manifest_path: Path to manifest.json
        _app_env: Current environment ("dev" or "prod")
        _manifest: Cached manifest dictionary
    """

    def __init__(
        self, manifest_path: Optional[str] = None, app_env: Optional[str] = None
    ):
        """Initialize the prompt registry.

        Args:
            manifest_path: Custom path to manifest.json (default: auto-detect)
            app_env: Environment override ("dev" or "prod", default: from APP_ENV or "prod")
        """
        # Auto-detect prompts directory (backend/prompts/)
        if manifest_path:
            self._manifest_path = Path(manifest_path)
            self._prompts_dir = self._manifest_path.parent
        else:
            # Assume this file is in backend/app/prompt_manager.py
            backend_dir = Path(__file__).parent.parent
            self._prompts_dir = backend_dir / "prompts"
            self._manifest_path = self._prompts_dir / "manifest.json"

        # Get environment (default to "dev" for iterative development, fall back to "prod" if env not available)
        self._app_env = app_env or os.getenv("APP_ENV", "dev")

        # Lazy-loaded attributes
        self._manifest: Optional[Dict[str, Any]] = None

    def _load_manifest(self) -> Dict[str, Any]:
        """Load and validate manifest.json (lazy loading).

        Returns:
            Manifest dictionary

        Raises:
            FileNotFoundError: If manifest.json not found
            ValueError: If manifest schema is invalid
        """
        if self._manifest is not None:
            return self._manifest

        if not self._manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest not found: {self._manifest_path}\n"
                f"Expected location: {self._prompts_dir}/manifest.json"
            )

        try:
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in manifest: {e}") from e

        if "prompts" not in manifest:
            raise ValueError("Manifest missing 'prompts' key")

        self._manifest = manifest
        return manifest

    def _resolve_prompt_path(self, task_name: str) -> Path:
        """Resolve prompt file path based on environment.

        Args:
            task_name: Task identifier from manifest (e.g., "retrieval_eval_dataset_l3_candidate_gen")

        Returns:
            Absolute path to .prompty file

        Raises:
            ValueError: If task_name not found in manifest
            FileNotFoundError: If resolved .prompty file doesn't exist
        """
        manifest = self._load_manifest()

        if task_name not in manifest["prompts"]:
            available = list(manifest["prompts"].keys())
            raise ValueError(
                f"Unknown task: '{task_name}'. Available tasks: {available}"
            )

        task_config = manifest["prompts"][task_name]

        # Priority 1: Use manifest-specified path (respects dev/prod environment and task-specific constraints)
        # Priority 2: If current env is not specified, fall back to the other env (dev→prod, prod→dev)
        # Priority 3: If manifest path doesn't exist, auto-detect latest version (vN.prompty) in dev mode
        # This ensures prompts configured only for specific environments are respected
        manifest_path = self._get_manifest_prompt_path(task_name, task_config, strict=False)
        if manifest_path:
            return manifest_path

        # Fallback: Auto-detect latest version (vN.prompty) in dev mode
        # This allows iterative prompt development without updating manifest.json on every change
        if self._app_env == "dev":
            versioned_path = self._try_get_latest_versioned_prompt(task_config)
            if versioned_path:
                return versioned_path

        # If we reach here, no prompt file was found
        raise FileNotFoundError(
            f"No prompt file found for task '{task_name}' in {self._app_env} mode. "
            f"Checked manifest and versioned files in task directory."
        )

    def _try_get_latest_versioned_prompt(
        self, task_config: Dict[str, Any]
    ) -> Optional[Path]:
        """Try to find the latest versioned prompt file (vN.prompty) in dev mode.

        Args:
            task_config: Task configuration from manifest

        Returns:
            Path to latest vN.prompty file, or None if not found
        """
        # Extract base directory from manifest path (either dev or prod)
        base_path = task_config.get("dev") or task_config.get("prod")
        if not base_path:
            return None

        # Get directory containing the prompt file
        # e.g., "retrieval_eval_gen/l3_candidate_generation.prompty" → "retrieval_eval_gen"
        task_dir = self._prompts_dir / Path(base_path).parent

        if not task_dir.exists():
            return None

        # Look for versioned files: v1.prompty, v2.prompty, etc.
        # Sort by version number (highest first) to get the latest
        version_files = sorted(
            task_dir.glob("v*.prompty"),
            key=lambda p: int(p.stem[1:]),  # Extract N from vN
            reverse=True,  # Highest version first
        )
        return version_files[0] if version_files else None

    def _get_manifest_prompt_path(
        self, task_name: str, task_config: Dict[str, Any], strict: bool = True
    ) -> Optional[Path]:
        """Resolve prompt path from manifest based on environment.

        Resolution order:
        1. Try current environment (dev/prod)
        2. Fall back to alternate environment (if dev not specified, try prod; vice versa)
        3. Return None (or raise error if strict=True)

        Args:
            task_name: Task identifier
            task_config: Task configuration from manifest
            strict: If True, raise errors when config/file missing. If False, return None.

        Returns:
            Absolute path to .prompty file, or None if strict=False and not found

        Raises:
            ValueError: If configuration is missing (only when strict=True)
            FileNotFoundError: If file doesn't exist (only when strict=True)
        """
        # Try current environment first, then fall back to alternate
        env_keys = [self._app_env]
        alternate_env = "prod" if self._app_env == "dev" else "dev"
        if alternate_env not in env_keys:
            env_keys.append(alternate_env)

        for env_key in env_keys:
            if env_key not in task_config:
                continue

            relative_path = task_config[env_key]
            prompt_path = self._prompts_dir / relative_path

            if prompt_path.exists():
                return prompt_path

        # No valid path found in either environment
        if strict:
            raise ValueError(
                f"Task '{task_name}' has no valid configuration. "
                f"Available keys: {list(task_config.keys())}"
            )
        return None

    def get_prompt_template(self, task_name: str) -> Runnable:
        """Load prompt template for a given task.

        This is the main API for accessing prompts. Returns a LangChain Runnable
        (wrapping ChatPromptTemplate) that can be used in LCEL chains.

        Args:
            task_name: Task identifier from manifest (e.g., "retrieval_eval_dataset_l3_candidate_gen")

        Returns:
            Runnable instance (compatible with LCEL chains)

        Raises:
            ValueError: If task not found or invalid
            FileNotFoundError: If .prompty file not found
            RuntimeError: If prompt loading fails

        Example:
            >>> registry = PromptTemplateRegistry()
            >>> prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")
            >>> chain = prompt | model.with_structured_output(Schema)
            >>> result = chain.invoke({"questions_count": 15, ...})
        """
        # Resolve path
        prompt_path = self._resolve_prompt_path(task_name)

        # Load .prompty file using langchain-prompty
        try:
            prompt = create_chat_prompt(str(prompt_path))
        except Exception as e:
            raise RuntimeError(
                f"Failed to load prompt from {prompt_path}: {e}"
            ) from e

        # Note: create_chat_prompt() returns a Runnable (RunnableLambda wrapping ChatPromptTemplate)
        # which is compatible with LCEL chains. No type validation needed.

        return prompt

    def list_tasks(self) -> List[str]:
        """List all available task names from manifest.

        Returns:
            List of task identifiers

        Example:
            >>> registry = PromptTemplateRegistry()
            >>> tasks = registry.list_tasks()
            >>> print(tasks)
            ['retrieval_eval_dataset_l3_candidate_gen', 'retrieval_eval_dataset_l3_judge_rerank', 'retrieval_eval_dataset_l1_candidate_gen']
        """
        manifest = self._load_manifest()
        return list(manifest["prompts"].keys())

    def get_task_info(self, task_name: str) -> Dict[str, Any]:
        """Get metadata about a task from manifest.

        Args:
            task_name: Task identifier

        Returns:
            Task configuration dictionary (description, category, paths)

        Raises:
            ValueError: If task not found
        """
        manifest = self._load_manifest()
        if task_name not in manifest["prompts"]:
            available = list(manifest["prompts"].keys())
            raise ValueError(
                f"Unknown task: '{task_name}'. Available: {available}"
            )
        return manifest["prompts"][task_name]
