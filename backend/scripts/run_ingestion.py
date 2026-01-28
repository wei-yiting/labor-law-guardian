import sys
import argparse
from pathlib import Path

# Adjust sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.app.rag.config import RAG_VERSIONS, LATEST_RAG_VERSION
from backend.app.rag.factory import get_ingestion_strategy


def main():
    parser = argparse.ArgumentParser(
        description="Run RAG Ingestion Pipeline (Refactored)"
    )
    parser.add_argument(
        "--rag-version",
        type=str,
        help=f"Choose RAG Version. Options: {list(RAG_VERSIONS.keys())}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ingestion (Skip Qdrant upsert, but generate intermediate files)",
    )

    args = parser.parse_args()

    version = args.rag_version if args.rag_version else LATEST_RAG_VERSION

    print(f"Initializing Ingestion for Version: {version}")

    try:
        strategy = get_ingestion_strategy(version)
        print(f"Strategy loaded: {type(strategy).__name__}")
        print("Starting ingestion...")

        # New Interface: run(documents, **kwargs)
        # We don't implement dry_run explicitly in the strategies yet, but we pass kwargs just in case.
        strategy.run(dry_run=args.dry_run)

        print("Ingestion Complete.")

    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except NotImplementedError as e:
        print(f"Not Implemented: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
