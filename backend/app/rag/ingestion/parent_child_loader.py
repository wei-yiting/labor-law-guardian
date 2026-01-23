
import json
import os
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Adjust import to fetch from config
# Assuming we run from project root
try:
    from backend.app.rag.config import LAW_DATA_DIR, LAW_FILES, RAG_VERSIONS, LATEST_RAG_VERSION
    from backend.app.rag.ingestion.law_article_chunker import LawArticleChunker
    from backend.app.rag.models.ingestion_models import RawLawArticle, LawChunk, SplitStrategyEnum
except ImportError:
    import sys
    # Add project root to path (for backend.app...)
    project_root = Path(__file__).resolve().parents[4]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
        
    # Add backend directory to path (for app.models... imports in chunker)
    backend_dir = project_root / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.append(str(backend_dir))

    from backend.app.rag.config import LAW_DATA_DIR, LAW_FILES, RAG_VERSIONS, LATEST_RAG_VERSION
    from backend.app.rag.ingestion.law_article_chunker import LawArticleChunker
    from backend.app.rag.models.ingestion_models import RawLawArticle, LawChunk, SplitStrategyEnum

from llama_index.core.schema import TextNode, NodeRelationship, RelatedNodeInfo, Document, BaseNode

def load_parent_child_data(rag_version: str = LATEST_RAG_VERSION) -> Tuple[List[BaseNode], List[BaseNode]]:
    """
    Load law data for Parent-Child Indexing Strategy.
    Refactored for AutoMergingRetriever.
    
    Process:
    1. Load raw articles from LAW_FILES.
    2. Create Parent Documents (Full Articles) and Child Nodes (Chunks).
    3. Link Child Nodes to Parent (via relationships).
    4. Persist chunks to backend/data/law_data/parent_child_index/tier_1_{suffix}.json.
    
    Returns:
        Tuple[List[BaseNode], List[BaseNode]]: (leaf_nodes, all_nodes)
        - leaf_nodes: The granular chunks (children) to be indexed.
        - all_nodes: Parent documents + Child nodes (for DocStore).
    """
    strategy_name = RAG_VERSIONS.get(rag_version, "UNKNOWN")
    print(f"Loading Parent-Child Data (Version {rag_version}: {strategy_name}) ...")
    
    # 1. Load Parent Content Lookup Map
    articles_map_path = Path(LAW_DATA_DIR) / "raw_law_data/articles_map.json"
    if not articles_map_path.exists():
        raise FileNotFoundError(f"Articles Map not found at {articles_map_path}")
        
    with open(articles_map_path, "r", encoding="utf-8") as f:
        articles_map = json.load(f)
    
    # Configure Chunker
    chunker = LawArticleChunker(strategy=strategy_name)
    all_chunks: List[LawChunk] = []
    
    # 2. Process Files & Generate Chunks
    
    for relative_path in LAW_FILES:
        full_path = Path(LAW_DATA_DIR) / relative_path
        
        if not full_path.exists():
            print(f"Warning: File not found: {full_path}")
            continue
            
        file_chunks = chunker.process_files([str(full_path)])
        all_chunks.extend(file_chunks)
        
    # 3. Persist Intermediate Chunks (Tier 1)
    output_dir = Path(LAW_DATA_DIR) / "parent_child_index"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if strategy_name == "PARENT_CHILD_COARSE":
        tier_1_filename = "tier_1_coarse.json"
    else:
        tier_1_filename = "tier_1_fine.json"
        
    tier_1_path = output_dir / tier_1_filename
    
    chunks_data = [chunk.model_dump(mode='json') for chunk in all_chunks]
    
    with open(tier_1_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_chunks)} chunks to {tier_1_path}")
    
    # 4. Group Chunks by Parent ID
    chunks_by_parent: Dict[str, List[LawChunk]] = {}
    for chunk in all_chunks:
        if chunk.parent_id not in chunks_by_parent:
            chunks_by_parent[chunk.parent_id] = []
        chunks_by_parent[chunk.parent_id].append(chunk)

    leaf_nodes = []
    all_nodes = []
    
    # 5. Create Nodes (Chunks Only)
    for parent_id, children_chunks in chunks_by_parent.items():
        # Get parent metadata for shared fields if needed, but we rely on chunk metadata mainly.
        # We NO LONGER create a Parent Document node.
        
        for chunk in children_chunks:
            # Check for ID collision (atomic chunk ID == parent ID)
            chunk_node_id = chunk.chunk_id
            if chunk_node_id == parent_id:
                chunk_node_id = f"{chunk_node_id}_chunk"

            # Child Metadata
            meta = chunk.metadata
            hierarchy = meta.hierarchy
            
            # Subparagraph handling for metadata
            subparagraph_val = getattr(hierarchy, "subparagraph", None)

            child_metadata = {
                "chunk_id": chunk_node_id,
                "parent_id": parent_id,
                "chunk_text": chunk.text,
                "split_strategy": meta.split_strategy.value if hasattr(meta.split_strategy, 'value') else meta.split_strategy,
                "is_expanded": meta.is_expanded,
                "article_no": hierarchy.article,
                "paragraph_no": hierarchy.paragraph,
                "subparagraph_no": subparagraph_val,
                "citation_title": meta.citation_title,
                "url": str(meta.url)
            }
             # Filter None
            child_metadata = {k: v for k, v in child_metadata.items() if v is not None}

            # Construct formatted text content for the Node
            content_parts = []
            
            # 1. Title: e.g. 勞動基準法第x條第o項
            if meta.citation_title:
                content_parts.append(meta.citation_title)
                
            # # 2. Chapter: e.g. 章節：工資
            # if meta.chapter_title:
            #     content_parts.append(f"章節：{meta.chapter_title}")
                
            # 3. Content: 條文內容：...
            content_parts.append(f"條文內容：{chunk.text}")
            
            formatted_text = "\n".join(content_parts)

            child_node = TextNode(
                text=formatted_text, 
                id_=chunk_node_id,
                metadata=child_metadata,
                excluded_embed_metadata_keys=[
                    "chunk_id", "parent_id", "chunk_text", "url", "article_no", "icon_src"
                ],
                excluded_llm_metadata_keys=[
                    "chunk_id", "chunk_text", "url"
                ]
            )
            
            # NO explicit relationships needed for manual lookup strategy
            # child_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=parent_id)
            
            leaf_nodes.append(child_node)
            all_nodes.append(child_node) # In this strategy, all_nodes IS leaf_nodes
            
        
    print(f"Generated {len(all_nodes)} Total Nodes (Parents + Children).")
    print(f"Generated {len(leaf_nodes)} Leaf Nodes (Children).")
    
    return leaf_nodes, all_nodes

if __name__ == "__main__":
    # Test the loader with v0.0.3 (Coarse)
    print("Testing v0.0.3 (Coarse)...")
    try:
        leaves, all_n = load_parent_child_data(rag_version="0.0.3")
        if leaves:
            print("\nSample Leaf Node (Coarse):")
            print(leaves[0].text[:50])
            
        # Specific check for LSA-53 and LSA-54 if possible?
        # Manually scanning leaf_nodes for id containing LSA-53
        lsa_53_nodes = [n for n in leaves if "LSA-53" in n.metadata.get("parent_id", "")]
        print(f"\nLSA-53 Chunks: {len(lsa_53_nodes)}")
        for n in lsa_53_nodes:
            print(f" - {n.node_id}: {n.text[:30]}...")

        lsa_54_nodes = [n for n in leaves if "LSA-54" in n.metadata.get("parent_id", "")]
        print(f"\nLSA-54 Chunks: {len(lsa_54_nodes)}")
        for n in lsa_54_nodes:
            print(f" - {n.node_id}: {n.text[:30]}...")

    except Exception as e:
        print(f"Error v0.0.3: {e}")
        import traceback
        traceback.print_exc()

    # Test the loader with v0.0.2 (Fine)
    print("\nTesting v0.0.2 (Fine)...")
    try:
         leaves, all_n = load_parent_child_data(rag_version="0.0.2")
         print(f"Generated {len(leaves)} fine chunks.")
    except Exception as e:
         print(f"Error v0.0.2: {e}")
         import traceback
         traceback.print_exc()
