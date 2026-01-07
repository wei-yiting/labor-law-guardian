# Labor Law Guardian

This repository is a staged build-out for a labor-law RAG system:

- **Week 1**: Scrape and clean labor law articles into a stable schema.
- **Week 2**: Build a graph representation (Neo4j) and retrieval evaluation.
- **Week 3+**: Tools (e.g., overtime calculator) and agent workflows.
- **Week 6-7**: API + Frontend.

### Architecture (high-level)

```mermaid
flowchart LR
  A[Scraper (requests + bs4)] --> B[Cleaner (regex)]
  B --> C[LawArticle schema (Pydantic)]
  C --> D[(Raw JSON)]
  C --> E[Graph Builder]
  E --> F[(Neo4j)]
  F --> G[Hybrid Retriever]
  G --> H[API (FastAPI)]
  H --> I[Frontend (Next.js)]
```

### Project layout

See the folder structure in the root of this repo; code lives under `backend/app/`.

### Folder purposes

- **`notebooks/`**: Experiment sandbox (prototype scraper, schema, evaluation). Notebooks are disposable; production code lives in `backend/app/`.
- **`backend/`**: Core Python domain where ingestion/RAG/agents/API will live.
  - **`backend/data/`**: Local data artifacts.
    - **`backend/data/raw/`**: Raw scraper outputs (e.g., `labor_laws.json`).
    - **`backend/data/cache/`**: Local cache (e.g., embedding cache) to avoid recomputation.
  - **`backend/app/`**: Python application source code.
    - **`backend/app/core/`**: Runtime configuration and shared clients (e.g., Neo4j driver).
    - **`backend/app/schemas/`**: Project-wide data contracts (Pydantic models).
    - **`backend/app/ingestion/`**: ETL modules (scraper + cleaner).
    - **`backend/app/rag/`**: Graph build + retrieval (hybrid search).
    - **`backend/app/tools/`**: Domain tools (Week 3+), e.g., overtime calculator.
    - **`backend/app/agents/`**: Agent orchestration (Week 4+), e.g., LangGraph workflows.
    - **`backend/app/api/`**: API layer (Week 6+), e.g., FastAPI routes.
- **`frontend/`**: Frontend battleground (Week 6-7), reserved for a Next.js app.

### Environment files

- **`env.example`**: Template for local environment variables. Copy to `.env` locally (do not commit `.env`).
