from typing import List, Optional, Set
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

class ArticleDedupPostprocessor(BaseNodePostprocessor):
    """
    Postprocessor that filters out multiple chunks from the same article.
    Only the highest-scoring chunk from each article is preserved.
    """
    
    def _postprocess_nodes(
        self, nodes: List[NodeWithScore], query_bundle: Optional[QueryBundle] = None
    ) -> List[NodeWithScore]:
        unique_nodes = []
        seen_articles: Set[str] = set()
        
        for node in nodes:
            # Safely get article_id or parent_id for deduplication
            # Priority: "article_id" (Naive) -> "parent_id" (Parent-Child) -> None
            art_id = node.node.metadata.get("article_id") or node.node.metadata.get("parent_id")
            
            # If we simply can't find an ID, we treat it as unique (or could skip)
            # Treating as unique is safer to avoid dropping valid content with schema issues
            if not art_id:
                unique_nodes.append(node)
                continue
            
            if art_id not in seen_articles:
                unique_nodes.append(node)
                seen_articles.add(art_id)
                
        return unique_nodes
