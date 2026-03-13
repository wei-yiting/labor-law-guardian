---
trigger: always_on
---

# Python Environment & Dependency Management Rules

You must strictly adhere to the following rules for any Python-related tasks in this project:

## 1. Mandatory use of uv

- All Python execution and package management **MUST** use `uv`.
- Never use `pip`, `conda`, or `poetry` directly.
- Use `uv run` to execute scripts to ensure the virtual environment is utilized.

## 2. Prohibition of Global Installation

- **STRICTLY PROHIBIT** installing any packages to the global Python environment.
- All dependencies must reside within the project's local virtual environment (typically `.venv`) managed by `uv`.

## 3. Dependency Authorization Protocol

- **DO NOT** add, remove, or update dependencies automatically.
- Before running `uv add` or `uv remove`, you must:
  1. Explain **why** the dependency is needed.
  2. Explicitly **ask for user consent**.
  3. Wait for the user to say "Yes" or "Approved" before executing the command.

## 4. Execution Workflow

- If a package is missing, stop execution and trigger the **Dependency Authorization Protocol**.
- Once approved, only use `uv add <package_name>` to update `pyproject.toml` and `uv.lock`.
