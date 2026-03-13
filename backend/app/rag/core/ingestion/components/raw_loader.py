import json
import logging
from pathlib import Path
from typing import List
from llama_index.core import Document
from backend.app.rag.config import LAW_DATA_DIR, LAW_FILES

logger = logging.getLogger(__name__)


def load_raw_law_documents() -> List[Document]:
    """
    Load raw law data from JSON files defined in config and convert them into LlamaIndex Documents.
    This is primarily for Naive RAG which indexes documents directly without complex chunking.

    Returns:
        List of Document objects ready for indexing.
    """
    documents = []

    for relative_path in LAW_FILES:
        full_path = Path(LAW_DATA_DIR) / relative_path

        if not full_path.exists():
            logger.warning(f"File not found: {full_path}")
            continue

        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        law_title = data.get("title", "Unknown Law")
        articles = data.get("articles", [])

        for article in articles:
            # Construct text content
            content_parts = [f"法規名稱：{law_title}"]

            chapter_name = article.get("chapter_name")
            if chapter_name and chapter_name.strip():
                content_parts.append(f"章節：{chapter_name}")

            article_no = article.get("article_no", "").strip()
            content_parts.append(f"條號：第 {article_no} 條")

            content = article.get("content", "").strip()
            content_parts.append(f"條文內容：{content}")

            text_content = "\n".join(content_parts)

            # Construct Metadata
            # We preserve standard metadata keys.
            metadata = {
                "law_title": law_title,
                "article_no": article_no,
                "article_id": article.get("id", ""),
                "chapter_no": article.get("chapter_no"),
                "chapter_title": chapter_name,
                "url": article.get("url", ""),
            }

            # Create Document
            doc = Document(
                text=text_content,
                metadata=metadata,
                excluded_embed_metadata_keys=["article_id", "url", "article_no"],
                excluded_llm_metadata_keys=["url", "article_id"],
            )
            documents.append(doc)

    logger.info(f"Loaded {len(documents)} raw documents")
    return documents
