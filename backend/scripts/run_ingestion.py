import sys
import argparse
import logging
from pathlib import Path

# Adjust sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)

# Suppress verbose httpx HTTP request logs
logging.getLogger("httpx").setLevel(logging.WARNING)

from backend.app.rag.config import LATEST_RAG_VERSION
from backend.app.rag.types import RagVersion
from backend.app.rag.version_utils import get_strategy_display_name
from backend.app.rag.factory import get_ingestion_strategy


def main():
    parser = argparse.ArgumentParser(
        description="Run RAG Ingestion Pipeline (Refactored)"
    )
    parser.add_argument(
        "--rag-version",
        type=str,
        help=f"Choose RAG Version. Options: {[v.value for v in RagVersion]}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ingestion (Skip Qdrant upsert, but generate intermediate files)",
    )

    args = parser.parse_args()

    version = args.rag_version if args.rag_version else LATEST_RAG_VERSION

    logger.info(f"Initializing Ingestion for Version: {version}")

    try:
        rag_version = RagVersion(version)
        strategy_name = get_strategy_display_name(rag_version)
        logger.info(f"Strategy: {strategy_name}")

        strategy = get_ingestion_strategy(version)
        logger.info("Starting ingestion...")

        # New Interface: run(documents, **kwargs)
        # We don't implement dry_run explicitly in the strategies yet, but we pass kwargs just in case.
        strategy.run(dry_run=args.dry_run)

        logger.info("Ingestion Complete.")

    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        sys.exit(1)
    except NotImplementedError as e:
        logger.error(f"Not Implemented: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
