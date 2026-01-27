import datetime
from typing import List, Dict, Any, Tuple, Optional
from backend.app.rag.interface import RetrieverStrategy
from backend.app.rag.config import (
    RETRIEVER_TOP_K, OPENAI_MODEL_NAME, EMBEDDING_MODEL_NAME, CHUNK_SIZE, RAG_VERSIONS
)
# Note: Evaluation might need to access original LawLookup logic
from backend.app.rag.core.evaluation.law_lookup import LawLookup

class RetrieverEvaluator:
    def __init__(self, strategy: RetrieverStrategy, rag_version: str, project_root: str, use_json_logging: bool = False):
        self.strategy = strategy
        self.rag_version = rag_version
        self.use_json_logging = use_json_logging
        self.law_lookup = LawLookup(project_root) if use_json_logging else None

    def run_retrieval(self, query: str) -> List[Any]:
        return self.strategy.retrieve(query)

    def calculate_metrics(self, retrieved_nodes, ground_truth_ids: List[str]) -> Tuple[float, float, List[str]]:
        # Use Strategy to get Evaluation IDs (Polymorphism)
        retrieved_article_ids = set()
        
        for node in retrieved_nodes:
            retrieved_id = self.strategy.get_retrieved_article_id(node)
            if retrieved_id:
                retrieved_article_ids.add(retrieved_id)
        
        hits_set = retrieved_article_ids & set(ground_truth_ids)
        hits = len(hits_set)
        
        retrieved_ids_list = list(retrieved_article_ids)

        if not ground_truth_ids:
            recall = 0.0
        else:
            recall = hits / len(ground_truth_ids)
            
        if not retrieved_ids_list:
            precision = 0.0
        else:
            precision = hits / len(retrieved_ids_list)
            
        return recall, precision, retrieved_ids_list

    def _get_unique_ordered_ids(self, nodes: List[Any]) -> List[str]:
        """
        Extracts ordered unique article IDs from retrieved nodes.
        Maintains the original retrieval order which is crucial for ranking metrics.
        """
        seen = set()
        ordered_ids = []
        for node in nodes:
            retrieved_id = self.strategy.get_retrieved_article_id(node)
            if retrieved_id and retrieved_id not in seen:
                seen.add(retrieved_id)
                ordered_ids.append(retrieved_id)
        return ordered_ids

    def _calculate_APk(self, retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
        """
        Calculates Average Precision at k (AP@k) for a single query.
        
        Formula: AP@k = (1 / R) * sum(P@i * rel(i)) for i=1 to k
        Where:
            R = Total number of relevant items (len(ground_truth_ids))
            P@i = Precision at rank i
            rel(i) = 1 if item at rank i is relevant, 0 otherwise
        """
        if not ground_truth_ids:
            return 0.0
            
        relevant_set = set(ground_truth_ids)
        R = len(relevant_set)
        
        # Only consider top k retrieved items (though typically retrieved_ids is already length k)
        retrieved_at_k = retrieved_ids[:k]
        
        score = 0.0
        num_hits = 0.0
        
        for i, doc_id in enumerate(retrieved_at_k):
            if doc_id in relevant_set:
                num_hits += 1.0
                precision_at_i = num_hits / (i + 1.0)
                score += precision_at_i
                
        # AP@k is the sum of precisions for relevant items divided by total relevant items
        return score / R

    def _calculate_RRk(self, retrieved_ids: List[str], ground_truth_ids: List[str], k: int) -> float:
        """
        Calculates Reciprocal Rank at k (RR@k) for a single query.
        
        Formula: 1 / rank_of_first_relevant_item
        """
        if not ground_truth_ids:
            return 0.0
            
        relevant_set = set(ground_truth_ids)
        retrieved_at_k = retrieved_ids[:k]
        
        for i, doc_id in enumerate(retrieved_at_k):
            if doc_id in relevant_set:
                return 1.0 / (i + 1.0)
                
        return 0.0

    def evaluate_dataset(self, dataset: List[Dict[str, Any]], verbose: bool = True) -> Dict[str, Any]:
        """
        Runs full evaluation on a dataset.
        Returns a dictionary containing metrics and failure cases.
        """
        from backend.app.rag.config import RETRIEVER_TOP_K
        k = RETRIEVER_TOP_K

        total_recall = 0.0
        total_precision = 0.0
        total_AP = 0.0
        total_RR = 0.0
        
        full_failed_cases = [] 
        fail_cases_data = []  
        
        total_items = len(dataset)
        
        for i, item in enumerate(dataset):
            query = item["question"]
            qid = item["id"]
            gt_ids = item["reference_articles_id"]
            supporting_context = item.get("supporting_context", "N/A")
            reasoning = item.get("reasoning", "N/A")
            
            nodes = self.run_retrieval(query)
            recall, precision, retrieved_ids = self.calculate_metrics(nodes, gt_ids)
            
            # Calculate AP@k using ordered unique IDs
            ordered_retrieved_ids = self._get_unique_ordered_ids(nodes)
            ap = self._calculate_APk(ordered_retrieved_ids, gt_ids, k)
            rr = self._calculate_RRk(ordered_retrieved_ids, gt_ids, k)
            total_AP += ap
            total_RR += rr

            total_recall += recall
            total_precision += precision
            
            if recall < 1.0:
                # Basic failure info
                full_failed_cases.append({
                    "id": qid,
                    "question": query,
                    "recall": recall,
                    "gt": gt_ids,
                    "retrieved": retrieved_ids,
                    "supporting_context": supporting_context,
                    "reasoning": reasoning
                })
                
                # Detailed JSON log info
                if self.use_json_logging and self.law_lookup:
                    case_data = self._build_failure_case_data(qid, query, gt_ids, nodes)
                    fail_cases_data.append(case_data)
            
            if verbose and (i + 1) % 10 == 0:
                print(f"Processed {i + 1}/{total_items} queries...")

        avg_recall = total_recall / total_items if total_items > 0 else 0
        avg_precision = total_precision / total_items if total_items > 0 else 0
        MAP_score = total_AP / total_items if total_items > 0 else 0
        MRR_score = total_RR / total_items if total_items > 0 else 0
        
        results = {
            "total_items": total_items,
            f"avg_recall@{k}": avg_recall,
            f"avg_precision@{k}": avg_precision,
            f"MAP@{k}": MAP_score,
            f"MRR@{k}": MRR_score,
            "full_failed_cases": full_failed_cases,
            "fail_cases_data": fail_cases_data
        }


        return results

    def _build_failure_case_data(self, qid, query, gt_ids, nodes):
        # 1. Build Ground Truth Docs
        gt_docs = []
        for art_id in gt_ids:
            article = self.law_lookup.get_article(art_id)
            content = article.get("content", "") if article else "Content not found"
            gt_docs.append({
                "article_id": art_id,
                "content": content
            })
        
        # 2. Build Retrieval Nodes
        retrieved_nodes_data = []
        for node in nodes:
            meta = node.metadata
            chunk_text = node.get_content()
            
            # Polymorphic ID extraction
            # But specific fields (chunk_id vs parent_id) might depend on strategy type
            # For logging purposes, we want to show 'parent_id' if it exists.
            
            pid = meta.get("parent_id")
            aid = meta.get("article_id")
            chunk_id = meta.get("chunk_id", node.id_)
            
            # Logic: If parent_id exists (ParentChild), show it + parent content
            # If not (Naive), show article_id + content.
            
            if pid:
                p_art = self.law_lookup.get_article(pid)
                parent_content = p_art.get("content", "Parent Article Not Found") if p_art else "Parent Not Found"
                retrieved_nodes_data.append({
                    "parent_id": pid,
                    "retrieved_parent_content": parent_content,
                    "retrieved_chunk_id": chunk_id,
                    "retrieved_chunk_text": chunk_text
                })
            else:
                # Naive Case
                retrieved_nodes_data.append({
                    "article_id": aid,
                    "content": chunk_text
                })

        return {
            "test_case_id": qid,
            "question": query,
            "ground_truth_documents": gt_docs,
            "retrieval_nodes": retrieved_nodes_data,
            "judge_feedback": [],
            "possible_resolution": []
        }

    def run_smoke_test(self, dataset: List[Dict[str, Any]]) -> bool:
        print("\n" + "="*30)
        print("RUNNING SMOKE TEST")
        print("="*30)
        
        smoke_items = [item for item in dataset if "smoke_test" in item.get("tags", [])]
        if not smoke_items:
            print("Warning: No smoke test items found.")
            return True 
        
        total_smoke_recall = 0.0
        failed = False
        
        for item in smoke_items:
            query = item["question"]
            qid = item["id"]
            gt_ids = item["reference_articles_id"]
            
            print(f"Processing QID: {qid}...", end="", flush=True)
            nodes = self.run_retrieval(query)
            recall, _, retrieved_ids = self.calculate_metrics(nodes, gt_ids)
            
            total_smoke_recall += recall
            status = "PASS" if recall == 1.0 else ("PARTIAL" if recall > 0 else "FAIL")
            print(f"\r[{status}] {qid}: {query[:30]}... | GT: {gt_ids} | Retrieved: {retrieved_ids} | Recall: {recall:.2f}")
            
        avg = total_smoke_recall / len(smoke_items)
        print(f"\nSmoke Test Average Recall: {avg:.2%}")
        
        if avg < 0.6:
            print("CRITICAL: Smoke Test Average Recall < 60%.")
            return False
            
        print("Smoke Test Passed.")
        return True
