---
name: coding-master-prompt-architect
description: Analyzes requirements and codebase to construct a comprehensive 'Master Prompt' for AI coding agents. Use this when planning complex development tasks, refactoring, or feature implementation.
---

# Coding Master Prompt Architect

This skill transforms vague feature requests into precise, context-rich "Master Prompts" optimized for AI Coding Agents. It acts as a bridge between human intent and machine execution.

## When to use this skill

- **Complex Feature Requests**: When the user asks for a new feature but hasn't specified all edge cases or file locations.
- **Codebase Exploration**: When the user provides a high-level goal, and you need to identify which files are relevant before work begins.
- **Requirement Validation**: To ensure all constraints are understood _before_ any code is written.

## Critical Protocol: The "Stop & Ask" Rule

**Do not generate the Master Prompt if requirements are ambiguous.** If the user's request lacks specific details (e.g., "fix the bug" without a stack trace, or "add a button" without design specs), you must:

1.  Pause the generation process.
2.  List the specific missing pieces of information.
3.  Ask the user for clarification.

## How to use this skill

Follow this four-step sequence strictly:

### Step 1: Context & Asset Discovery

Before writing the prompt, you must understand the current state of the codebase.

1.  **Analyze the Request**: Identify the core objective (e.g., "Add authentication," "Refactor the sidebar").
2.  **Locate Assets**: Use tools (like `ls`, `find`, or `grep`) to identify relevant files.
    - _Goal_: Find not just the file to be changed, but also its dependencies, tests, and related configurations.
3.  **Read Context**: Read the content of these key files to understand existing patterns and structures.

### Step 2: Gap Analysis (Validation)

Compare the user's request against the found context. Ask yourself:

- Do I know _exactly_ where this code goes?
- Do I know the expected output format?
- Are there conflicting files?
- Is the visual style or logic defined?

_If any answer is "No", trigger the **Critical Protocol** defined above._

### Step 3: Master Prompt Construction

Once requirements are clear, generate the Master Prompt. The output must be a Markdown code block containing the following sections:

1.  **ROLE & OBJECTIVE**: Define who the coding agent is and what success looks like.
2.  **CONTEXT & FILES**:
    - List the specific file paths involved.
    - (Optional) If the files are small, include snippets. If large, instruct the coding agent to read them.
3.  **TASK SPECIFICATION**: Step-by-step instructions on what to implement.
    - Be atomic (Break down complex logic).
    - Reference specific function names or variable names found in Step 1.
4.  **CONSTRAINTS & PATTERNS**:
    - "Do not break existing tests."
    - "Follow the style guide found in `X` file."
    - "Use the library `Y` for this feature."
5.  **ACCEPTANCE CRITERIA**: How to verify the task is done.

### Step 4: Output Delivery

- Present the Master Prompt in a copy-pasteable code block.
- **DO NOT** write or modify any actual code in the project files. Your job is only to generate the _prompt_.

## Example Output Structure

Here is the template you should fill out for the user:

```markdown
# Master Prompt: [Task Name]

## 1. Context

You are an expert software engineer. We are working on [Project Description].
The goal is to [Specific Goal].

## 2. Relevant Files

Please read and analyze the following files to understand the context:

- `src/components/Button.tsx` (Target for modification)
- `src/styles/theme.ts` (Style definitions)

## 3. Instructions

1. Import `X` from `library`.
2. Modify the `Button` component to accept a new prop `isLoading`.
3. If `isLoading` is true, render the `Spinner` component.

## 4. Constraints

- Use TypeScript interfaces.
- Do not modify `App.tsx`.
- Ensure strict type checking.
```

## Constraints

- **No Code Execution**: Do not attempt to implement the feature. Only output the text prompt.
- **File System Safety**: You may read files to understand context, but do not write to them.
