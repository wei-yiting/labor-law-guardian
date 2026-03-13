from typing import List, Dict, Any, Tuple, Union
from backend.app.rag.interface import RetrieverStrategy

# Note: Evaluation might need to access original LawLookup logic
from backend.app.rag.core.evaluation.law_lookup import LawLookup


class RetrieverEvaluator:
    def __init__(
        self,
        strategy: RetrieverStrategy,
        rag_version: str,
        project_root: str,
        use_json_logging: bool = False,
    ):
        self.strategy = strategy
        self.rag_version = rag_version
        self.use_json_logging = use_json_logging
        self.law_lookup = LawLookup(project_root) if use_json_logging else None

    def run_retrieval(self, query: str) -> List[Any]:
        return self.strategy.retrieve(query)

    def calculate_metrics(
        self, retrieved_nodes, ground_truth_groups: List[List[str]]
    ) -> Tuple[float, float, List[str], List[str]]:
        """
        Calculates Strict Recall and Precision.

        Args:
            retrieved_nodes: Nodes returned by retriever.
            ground_truth_groups: List of valid ground truth sets. e.g. [["LSA-1", "LSA-2"]] means ALL are required.
                                 If multiple inner lists exist, they are alternatives (OR).

        Returns:
            recall, precision, retrieved_ids, best_matching_group
        """
        # Use Strategy to get Evaluation IDs (Polymorphism)
        retrieved_article_ids = set()

        for node in retrieved_nodes:
            retrieved_id = self.strategy.get_retrieved_article_id(node)
            if retrieved_id:
                retrieved_article_ids.add(retrieved_id)

        retrieved_ids_list = list(retrieved_article_ids)

        best_recall = 0.0
        best_precision = 0.0
        best_group = []

        # If GT is empty or legacy issues? We assume migration is done so it is List[List[str]]
        if not ground_truth_groups:
            return 0.0, 0.0, retrieved_ids_list, []

        for group in ground_truth_groups:
            required_set = set(group)
            if not required_set:
                continue

            hits = len(retrieved_article_ids & required_set)

            # --- STRICT EVALUATION LOGIC ---
            # For Level 2 Multi-hop: must retrieve ALL required articles to count as a hit.
            if hits == len(required_set):
                current_recall = 1.0
            else:
                current_recall = 0.0

            # Precision: If Strict Recall is 0, Precision is 0 (as "Hit" is binary execution success)
            if current_recall == 0.0:
                current_precision = 0.0
            else:
                if not retrieved_ids_list:
                    current_precision = 0.0
                else:
                    # Hits here acts as "Valid Info Retrieved".
                    # If we got the full set, we credit 'hits' (size of set) amount of correct info?
                    # Or do we count each document?
                    # Standard Precision = (Relevant Retrieved) / (Total Retrieved)
                    # If we have 2 docs required, we got 2. Precision = 2 / N.
                    current_precision = hits / len(retrieved_ids_list)

            # Maximize score (OR logic between groups if any)
            if current_recall > best_recall:
                best_recall = current_recall
                best_precision = current_precision
                best_group = group
            elif current_recall == best_recall and current_precision > best_precision:
                best_precision = current_precision
                best_group = group

        # If no match found at all and best_group is empty, just pick the first one for logging purposes
        if not best_group and ground_truth_groups:
            best_group = ground_truth_groups[0]

        return best_recall, best_precision, retrieved_ids_list, best_group

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

    def _calculate_APk(
        self, retrieved_ids: List[str], relevant_group: List[str], k: int
    ) -> float:
        """
        Calculates Average Precision at k (AP@k) using the best matching group.
        Strictness is handled by caller (if recall=0, this isn't called or result ignored).
        """
        if not relevant_group:
            return 0.0

        relevant_set = set(relevant_group)
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

        return score / R

    def _calculate_RRk(
        self, retrieved_ids: List[str], relevant_group: List[str], k: int
    ) -> float:
        """
        Calculates Reciprocal Rank at k (RR@k).
        For multi-doc queries, RR usually refers to the *first* relevant doc found?
        Or should it be 0 if strict criteria fails?
        Caller handles strictness. We just calc standard RR based on the set.
        """
        if not relevant_group:
            return 0.0

        relevant_set = set(relevant_group)
        retrieved_at_k = retrieved_ids[:k]

        for i, doc_id in enumerate(retrieved_at_k):
            if doc_id in relevant_set:
                return 1.0 / (i + 1.0)

        return 0.0

    def evaluate_dataset(
        self, dataset: List[Dict[str, Any]], verbose: bool = True
    ) -> Dict[str, Any]:
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
            # GT is now List[List[str]] thanks to migration
            # Handle potential Type error if migration failed for some reason?
            raw_gt = item.get("reference_articles_id", [])

            # Safety Check / Normalization (if somehow we missed the migration for in-memory objects?)
            gt_groups = []
            if raw_gt:
                if isinstance(raw_gt[0], str):
                    # Fallback for unmigrated data
                    gt_groups = [raw_gt]
                else:
                    gt_groups = raw_gt

            ground_truth_text = item.get("ground_truth", "N/A")
            supporting_context = item.get("supporting_context", "N/A")
            reasoning = item.get("reasoning", "N/A")
            tags = item.get("tags", [])

            nodes = self.run_retrieval(query)
            recall, precision, retrieved_ids, best_group = self.calculate_metrics(
                nodes, gt_groups
            )

            # Strict Logic Propagation to Ranking Metrics
            if recall == 1.0:
                # Only calculate ranking scores if we passed the strict gate
                ordered_retrieved_ids = self._get_unique_ordered_ids(nodes)
                ap = self._calculate_APk(ordered_retrieved_ids, best_group, k)
                rr = self._calculate_RRk(ordered_retrieved_ids, best_group, k)
            else:
                ap = 0.0
                rr = 0.0

            total_AP += ap
            total_RR += rr

            total_recall += recall
            total_precision += precision

            if recall < 1.0:
                # Basic failure info
                full_failed_cases.append(
                    {
                        "id": qid,
                        "question": query,
                        "recall": recall,
                        "gt": gt_groups,  # Show all groups
                        "retrieved": retrieved_ids,
                        "supporting_context": supporting_context,
                        "reasoning": reasoning,
                    }
                )

                # Detailed JSON log info
                if self.use_json_logging and self.law_lookup:
                    case_data = self._build_failure_case_data(
                        qid,
                        query,
                        gt_groups,
                        nodes,
                        ground_truth_text,
                        supporting_context,
                        tags,
                        reasoning,
                    )
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
            "fail_cases_data": fail_cases_data,
        }

        return results

    def _build_failure_case_data(
        self,
        qid,
        query,
        gt_groups,
        nodes,
        ground_truth_text,
        supporting_context,
        tags,
        reasoning,
    ):
        # 1. Build Ground Truth Docs
        # gt_groups is List[List[str]]. Flatten? or show groups?
        # For simplicity, let's flatten distinct IDs but maybe group them in display?
        # Or just show all distinct GTs.

        gt_docs = []
        seen_gt = set()

        for group in gt_groups:
            for art_id in group:
                if art_id in seen_gt:
                    continue
                seen_gt.add(art_id)

                article = self.law_lookup.get_article(art_id)
                content = article.get("content", "") if article else "Content not found"
                gt_docs.append({"article_id": art_id, "content": content})

        # 2. Build Retrieval Nodes
        retrieved_nodes_data = []
        for node in nodes:
            meta = node.metadata
            chunk_text = node.get_content()

            pid = meta.get("parent_id")
            aid = meta.get("article_id")
            chunk_id = meta.get("chunk_id", node.id_)

            if pid:
                p_art = self.law_lookup.get_article(pid)
                parent_content = (
                    p_art.get("content", "Parent Article Not Found")
                    if p_art
                    else "Parent Not Found"
                )
                retrieved_nodes_data.append(
                    {
                        "parent_id": pid,
                        "retrieved_parent_content": parent_content,
                        "retrieved_chunk_id": chunk_id,
                        "retrieved_chunk_text": chunk_text,
                    }
                )
            else:
                # Naive Case
                retrieved_nodes_data.append({"article_id": aid, "content": chunk_text})

        return {
            "test_case_id": qid,
            "question": query,
            "ground_truth": ground_truth_text,
            "supporting_context": supporting_context,
            "tags": tags,
            "reasoning": reasoning,
            "ground_truth_documents": gt_docs,  # Just list of dicts
            "retrieval_nodes": retrieved_nodes_data,
            "judge_feedback": [],
            "possible_resolution": [],
        }

    def run_smoke_test(self, dataset: List[Dict[str, Any]]) -> bool:
        print("\n" + "=" * 30)
        print("RUNNING SMOKE TEST")
        print("=" * 30)

        smoke_items = [item for item in dataset if "smoke_test" in item.get("tags", [])]
        if not smoke_items:
            print("Warning: No smoke test items found.")
            return True

        total_smoke_recall = 0.0

        for item in smoke_items:
            query = item["question"]
            qid = item["id"]
            # Handle list of lists
            raw_gt = item.get("reference_articles_id", [])
            gt_groups = []
            if raw_gt:
                if isinstance(raw_gt[0], str):
                    gt_groups = [raw_gt]
                else:
                    gt_groups = raw_gt

            print(f"Processing QID: {qid}...", end="", flush=True)
            nodes = self.run_retrieval(query)
            recall, _, retrieved_ids, _ = self.calculate_metrics(nodes, gt_groups)

            total_smoke_recall += recall
            status = "PASS" if recall == 1.0 else ("PARTIAL" if recall > 0 else "FAIL")
            print(
                f"\r[{status}] {qid}: {query[:30]}... | GT: {gt_groups} | Retrieved: {retrieved_ids} | Recall: {recall:.2f}"
            )

        avg = total_smoke_recall / len(smoke_items)
        print(f"\nSmoke Test Average Recall: {avg:.2%}")

        if avg < 0.6:
            print("CRITICAL: Smoke Test Average Recall < 60%.")
            return False

        print("Smoke Test Passed.")
        return True
