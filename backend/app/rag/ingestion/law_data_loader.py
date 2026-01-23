
import json
import os
from typing import List
from pathlib import Path

# Adjust import to fetch from config
# Assuming we run from project root, we need to ensure backend.app.core.config is importable
try:
    from backend.app.rag.config import LAW_DATA_DIR, LAW_FILES
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[4]))
    from backend.app.rag.config import LAW_DATA_DIR, LAW_FILES

from llama_index.core import Document

def load_law_data() -> List[Document]:
    """
    Load law data from JSON files defined in config and convert them into LlamaIndex Documents.
    
    Returns:
        List of Document objects ready for indexing.
    """
    documents = []
    
    for relative_path in LAW_FILES:
        full_path = Path(LAW_DATA_DIR) / relative_path
        
        if not full_path.exists():
            print(f"Warning: File not found: {full_path}")
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
            metadata = {
                "law_title": law_title,
                "article_no": article_no,
                "article_id": article.get("id", ""),
                "url": article.get("url", "")
            }
            
            # Create Document
            doc = Document(
                text=text_content,
                metadata=metadata,
                excluded_embed_metadata_keys=["article_id", "url", "article_no"],
                excluded_llm_metadata_keys=["url", "article_id"]
            )
            documents.append(doc)
            
    return documents

if __name__ == "__main__":
    # Test the loader
    docs = load_law_data()
    print(f"Loaded {len(docs)} documents.")
    if len(docs) > 0:
        print("Sample Document:")
        print("Text:", docs[0].text)
        print("Metadata:", docs[0].metadata)
