# Prompts Directory

This directory contains prompt templates in Microsoft Prompty format (.prompty) for the Labor Law Guardian evaluation dataset generation pipeline.

## Structure

```
prompts/
├── manifest.json                         # Registry mapping task names to .prompty files
└── retrieval_eval_gen/                  # Retrieval evaluation dataset generation
    ├── l3_candidate_generation_v01.prompty    # Level 3 question generation
    ├── l3_judge_reranking_v01.prompty         # Level 3 question judging
    └── l1_candidate_generation_v01.prompty    # Level 1 question generation (placeholder)
```

## Usage

```python
from backend.app.prompt_manager import PromptTemplateRegistry

# Initialize registry (auto-detects APP_ENV)
registry = PromptTemplateRegistry()

# Load prompt
prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")

# Use in LangChain LCEL
chain = prompt | model | parser
result = chain.invoke({"questions_count": 15, ...})
```

## Environment Switching

Set `APP_ENV` environment variable:

```bash
export APP_ENV=dev   # Development mode (auto-detects latest vN.prompty)
export APP_ENV=prod  # Production mode (uses manifest.json "prod" entry)
```

### Development Mode

In dev mode, prompts are loaded fresh from disk on each call (no caching). The registry automatically selects the `dev` entry when `APP_ENV=dev`:

```json
{
  "prompts": {
    "retrieval_eval_dataset_l3_candidate_gen": {
      "dev": "retrieval_eval_gen/l3_candidate_generation_v01.prompty",
      "prod": "retrieval_eval_gen/l3_candidate_generation_v01.prompty"
    }
  }
}
```

For rapid iteration, you can edit the `.prompty` file directly and the changes will be picked up immediately on the next call to `get_prompt_template()`.

### Production Mode

In prod mode, the registry uses the exact file specified in manifest.json's `"prod"` entry.

## Adding New Prompts

1. **Create prompt file** in appropriate category directory (e.g., `retrieval_eval_gen/`)
2. **Use descriptive naming**: `<category>/<level>_<purpose>.prompty`
   - Example: `retrieval_eval_gen/l2_candidate_generation.prompty`
3. **Write YAML frontmatter + Jinja2 template**
4. **Register in `manifest.json`**:
   ```json
   {
     "prompts": {
       "<task_name>": {
         "description": "...",
         "category": "...",
         "dev": "<category>/<filename>.prompty",
         "prod": "<category>/<filename>.prompty"
       }
     }
   }
   ```

## Naming Conventions

### Categories

Group by functional domain:

- `retrieval_eval_gen` - Retrieval evaluation dataset generation
- `agent_prompts` - Agent system prompts
- `rag_prompts` - RAG pipeline prompts

### Filenames

Use semantic names describing the prompt's purpose:

- **Format**: `<level/tier>_<action>_<context>_v<N>.prompty`
- **Examples**:
  - `l3_candidate_generation_v01.prompty` (Level 3 question generation)
  - `l3_judge_reranking_v01.prompty` (Level 3 judging and reranking)
  - `l1_candidate_generation_v01.prompty` (Level 1 question generation)

## Prompty File Format

Microsoft Prompty format uses YAML frontmatter + Jinja2 templates:

```yaml
---
name: Prompt Name
description: Brief description
authors:
  - Author Name
model:
  api: chat
  configuration:
    model_name:
      - gpt-4o
      - claude-sonnet-4-0
      - gemini-2.5-pro
  parameters:
    max_tokens: 3000
    temperature: 0.7
inputs:
  variable1:
    type: string
    description: Description of the variable
  variable2:
    type: number
    description: Numeric variable
sample:
  variable1: "Sample value"
  variable2: 42
---
system:
{{variable1}} content here

{{variable2}} will be substituted

user:
User message template
```

## Jinja2 Template Variables

Use `{{variable}}` syntax (double braces) for template variables.

### JSON Examples in Prompts

For JSON examples in prompts, wrap with raw blocks to prevent parsing:

```jinja2
{% raw %}
{
  "key": "value"
}
{% endraw %}
```

### Variable Types

Supported types in `inputs` section:

- `string` - Text values
- `number` - Numeric values (integers or floats)
- `boolean` - True/False values
- `array` - List of values
- `object` - Structured data

**Note**: Use `number` instead of `integer` for numeric types (JSON Schema standard).

## Best Practices

### 1. Version Control

- Use Git to track prompt changes
- Write clear commit messages for prompt updates
- Tag stable versions for production use

### 2. Testing

- Test prompts with sample data before deployment
- Validate variable substitution
- Check output format matches expected schema

### 3. Documentation

- Include detailed descriptions in YAML frontmatter
- Document expected input/output formats
- Provide sample values in `sample` section

### 4. Maintenance

- Update manifest.json when adding/removing prompts
- Keep naming consistent across related prompts
- Edit `.prompty` files directly in dev mode for immediate feedback

## Troubleshooting

### Prompt Not Found

```
FileNotFoundError: Prompt file not found: ...
```

**Solution**: Check manifest.json path and verify .prompty file exists.

### Variable Substitution Error

```
Error in inputs: validation error for PropertySettings
```

**Solution**: Ensure `type` in inputs section uses valid JSON Schema types (`string`, `number`, `boolean`, `array`, `object`).

### Import Error

```
ModuleNotFoundError: No module named 'langchain_prompty'
```

**Solution**: Install dependencies with `uv add langchain-prompty`.

## Related Documentation

- [Microsoft Prompty Documentation](https://microsoft.github.io/promptflow/how-to-guides/develop-a-prompty/)
- [LangChain Prompty Integration](https://python.langchain.com/docs/integrations/prompts/prompty)
- [Project CLAUDE.md](../../CLAUDE.md)
- [Prompt Manager Source](../app/prompt_manager.py)

## Examples

### Loading Multiple Prompts

```python
from backend.app.prompt_manager import PromptTemplateRegistry

registry = PromptTemplateRegistry()

# Load generation prompt
gen_prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_candidate_gen")

# Load judge prompt
judge_prompt = registry.get_prompt_template("retrieval_eval_dataset_l3_judge_rerank")

# Use in parallel chains
from langchain_core.runnables import RunnableParallel

parallel_chain = RunnableParallel(
    generation=gen_prompt | gen_model,
    judging=judge_prompt | judge_model
)
```

### Listing Available Tasks

```python
registry = PromptTemplateRegistry()
tasks = registry.list_tasks()
print(f"Available prompts: {', '.join(tasks)}")
```

### Getting Task Metadata

```python
registry = PromptTemplateRegistry()
info = registry.get_task_info("retrieval_eval_dataset_l3_candidate_gen")
print(f"Description: {info['description']}")
print(f"Category: {info['category']}")
```

## Migration Notes

This prompt management system was introduced to replace hardcoded prompts in Python scripts. Key changes:

- **Before**: Prompts defined as multi-line strings in `generate_eval_dataset.py` (lines 76-245)
- **After**: Prompts externalized to `.prompty` files with registry-based loading
- **Benefits**:
  - Version control for prompts
  - Hot-reloading in dev mode
  - Environment-based switching (dev/prod)
  - Separation of concerns (prompt engineering vs. code logic)
