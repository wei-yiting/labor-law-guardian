import re
import json
from typing import List, Optional, Tuple

from backend.app.rag.types import (
    RawLawArticle,
    LawChunk,
    LawChunkFine,
    LawChunkCoarse,
    ChunkMetadataFine,
    ChunkMetadataCoarse,
    HierarchyFine,
    HierarchyCoarse,
    SplitStrategyEnum,
)
from backend.data.law_data.law_config import LAW_FILES


class LawArticleChunker:
    """
    Core domain logic to split Law Articles into granular chunks (Fine or Coarse).
    Moved from backend/app/rag/ingestion/law_article_chunker.py
    """

    def __init__(self, strategy: str = "PARENT_CHILD_FINE"):
        self.strategy = strategy
        # Map prefix (e.g., "LSA") to Law Name (e.g., "勞動基準法")
        self.prefix_map = {item["prefix"]: item["name"] for item in LAW_FILES}

    def _get_law_name(self, article_id: str) -> str:
        """
        Resolve law name from article ID (e.g., 'LSA-24' -> '勞動基準法').
        """
        # Assume ID format is "{PREFIX}-{ArticleNum}"
        # Some prefixes might contain underscores, so we split by the first hyphen if present.
        # Check if hyphen exists
        if "-" in article_id:
            prefix = article_id.split("-")[0]
            return self.prefix_map.get(prefix, "勞動基準法")

        # Fallback logic if ID structure is different or prefix not found
        return "勞動基準法"

    def process_files(self, file_paths: List[str]) -> List[LawChunk]:
        all_chunks = []
        for file_path in file_paths:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Check if data matches LawData structure
                if "articles" in data:
                    articles_data = data["articles"]
                    # If articles_data contains RawLawArticle dicts
                    for article_dict in articles_data:
                        article = RawLawArticle(**article_dict)
                        chunks = self.parse_article(article)
                        all_chunks.extend(chunks)
                else:
                    pass
        return all_chunks

    def parse_article(self, article: RawLawArticle) -> List[LawChunk]:
        """
        Entry point for parsing a single article.
        """
        law_name = self._get_law_name(article.id)
        if self.strategy == "PARENT_CHILD_COARSE":
            return self._split_coarse(article, law_name)
        else:
            return self._split_fine(article, law_name)

    # --- Shared Helpers ---

    def _split_by_paragraph(self, text: str) -> List[Tuple[int, str, int, int]]:
        """
        Helper to identify numeric paragraphs (e.g., "(1)")
        Returns list of (para_num, full_text_of_para, start_idx, end_idx)
        """
        numeric_pattern = re.compile(r"(?:^|\n)\s*\((\d+)\)")
        matches = list(numeric_pattern.finditer(text))

        results = []
        if matches:
            for i, match in enumerate(matches):
                # The content ends at the start of the next match, or end of text
                if i < len(matches) - 1:
                    content_end = matches[i + 1].start()
                else:
                    content_end = len(text)

                para_num = int(match.group(1))
                # match.start() includes the newline before the paragraph, usually we want the block
                start_idx = match.start()

                extracted_full_text = text[match.start() : content_end].strip()

                results.append((para_num, extracted_full_text, start_idx, content_end))

        return results

    def _convert_to_chinese_numeral(self, n: int) -> str:
        """
        Simple implementation handling 0-999 for law articles.
        Crucial for citation formatting (e.g., '10' -> '十', '23' -> '二十三').
        Not intended for general purpose large number conversion.
        """
        digits = "零一二三四五六七八九"

        if n == 0:
            return digits[0]

        s = ""
        n_str = str(n)

        if 10 <= n < 20:
            if n == 10:
                return "十"
            s = "十" + digits[int(n_str[1])]
            return s

        res = ""
        h = n // 100
        t = (n % 100) // 10
        u = n % 10

        if h > 0:
            res += digits[h] + "百"

        if t == 0:
            if h > 0 and u > 0:
                res += "零"
        else:
            if t == 1 and h == 0:  # 10-19 handled above
                res += "十"
            else:
                res += digits[t] + "十"

        if u > 0:
            res += digits[u]

        return res

    # --- Coarse Strategy (v0.0.3) ---
    def _split_coarse(
        self, article: RawLawArticle, law_name: str
    ) -> List[LawChunkCoarse]:
        chunks = []

        # Base metadata info
        base_kwargs = {
            "url": article.url,
            "chapter_no": article.chapter_no,
            "chapter_title": article.chapter_name,
            "article_no": article.article_no,
        }

        # 1. Try splitting by Paragraph
        paragraphs = self._split_by_paragraph(article.content)

        if paragraphs:
            for para_num, para_text, _, _ in paragraphs:
                chunk_id = f"{article.id}_P{para_num}"

                hierarchy = HierarchyCoarse(
                    article=article.article_no, paragraph=para_num
                )

                # Format citation (No Subparagraph)
                citation = self._format_citation_coarse(hierarchy, law_name)

                metadata = ChunkMetadataCoarse(
                    **base_kwargs,
                    split_strategy=SplitStrategyEnum.numeric,
                    is_expanded=False,  # Coarse chunks are not "expanded" lists, they are blocks
                    citation_title=citation,
                    hierarchy=hierarchy,
                )

                chunk = LawChunkCoarse(
                    chunk_id=chunk_id,
                    parent_id=article.id,
                    text=para_text,
                    metadata=metadata,
                )
                chunks.append(chunk)
        else:
            # Atomic (Article Level)
            chunk_id = article.id
            hierarchy = HierarchyCoarse(article=article.article_no, paragraph=None)
            citation = self._format_citation_coarse(hierarchy, law_name)

            metadata = ChunkMetadataCoarse(
                **base_kwargs,
                split_strategy=SplitStrategyEnum.atomic,
                is_expanded=False,
                citation_title=citation,
                hierarchy=hierarchy,
            )

            chunk = LawChunkCoarse(
                chunk_id=chunk_id,
                parent_id=article.id,
                text=article.content.strip(),
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _format_citation_coarse(self, hierarchy: HierarchyCoarse, law_name: str) -> str:
        # Same logic as fine but without subparagraph check
        art_str = hierarchy.article

        if "-" in art_str:
            main_num, sub_num = art_str.split("-")
            main_cn = self._convert_to_chinese_numeral(int(main_num))
            sub_cn = self._convert_to_chinese_numeral(int(sub_num))
            art_text = f"第{main_cn}條之{sub_cn}"
        else:
            if art_str.isdigit():
                art_cn = self._convert_to_chinese_numeral(int(art_str))
                art_text = f"第{art_cn}條"
            else:
                art_text = f"第{art_str}條"

        title = f"{law_name}{art_text}"

        if hierarchy.paragraph:
            para_cn = self._convert_to_chinese_numeral(hierarchy.paragraph)
            title += f"第{para_cn}項"

        return title

    # --- Fine Strategy (v0.0.2) ---

    def _split_fine(self, article: RawLawArticle, law_name: str) -> List[LawChunkFine]:
        hierarchy = HierarchyFine(article=article.article_no)
        metadata = ChunkMetadataFine(
            url=article.url,
            split_strategy=SplitStrategyEnum.atomic,
            is_expanded=False,
            citation_title="",
            hierarchy=hierarchy,
            chapter_no=article.chapter_no,
            chapter_title=article.chapter_name,
            article_no=article.article_no,
        )
        return self._split_recursive_fine(
            article.content, article.id, article.article_no, metadata, law_name
        )

    def _split_recursive_fine(
        self,
        text: str,
        parent_id: str,
        article_no: str,
        base_metadata: ChunkMetadataFine,
        law_name: str,
    ) -> List[LawChunkFine]:
        # Step 1: Check for Numeric Paragraphs
        paragraphs = self._split_by_paragraph(text)

        if paragraphs:
            chunks = []
            for para_num, para_text, _, _ in paragraphs:
                sub_chunks = self._process_subparagraphs_fine(
                    para_text, parent_id, article_no, base_metadata, para_num, law_name
                )
                chunks.extend(sub_chunks)
            return chunks

        # Step 2: Check for Subparagraphs (e.g., "一、")
        else:
            return self._process_subparagraphs_fine(
                text, parent_id, article_no, base_metadata, None, law_name
            )

    def _process_subparagraphs_fine(
        self,
        text: str,
        parent_id: str,
        article_no: str,
        base_metadata: ChunkMetadataFine,
        para_num: Optional[int],
        law_name: str,
    ) -> List[LawChunkFine]:
        """
        Step 2 logic: Checks for "一、", "二、"...
        """
        sub_pattern = re.compile(r"(?:^|\n)\s*([一二三四五六七八九十百]+)、")
        matches = list(sub_pattern.finditer(text))

        if matches:
            chunks = []
            # Contextual Split
            first_match_start = matches[0].start()
            preamble = text[:first_match_start].strip()

            for i, match in enumerate(matches):
                if i < len(matches) - 1:
                    content_end = matches[i + 1].start()
                else:
                    content_end = len(text)

                item_text = text[match.start() : content_end].strip()
                full_text = f"{preamble}{item_text}"

                # Calc Sub ID
                current_sub_id = i + 1

                if para_num:
                    chunk_id = f"{parent_id}_P{para_num}_S{current_sub_id}"
                    strategy = SplitStrategyEnum.numeric_contextual
                else:
                    chunk_id = f"{parent_id}_S{current_sub_id}"
                    strategy = SplitStrategyEnum.contextual

                new_hierarchy = HierarchyFine(
                    article=article_no, paragraph=para_num, subparagraph=current_sub_id
                )

                citation = self._format_citation_fine(new_hierarchy, law_name)

                new_meta = base_metadata.model_copy()
                new_meta.split_strategy = strategy
                new_meta.is_expanded = True
                new_meta.hierarchy = new_hierarchy
                new_meta.citation_title = citation

                chunk = LawChunkFine(
                    chunk_id=chunk_id,
                    parent_id=parent_id,
                    text=full_text,
                    metadata=new_meta,
                )
                chunks.append(chunk)

            return chunks

        else:
            # Step 3: Atomic (Fallback)
            if para_num:
                chunk_id = f"{parent_id}_P{para_num}"
                strategy = SplitStrategyEnum.numeric
                new_hierarchy = HierarchyFine(
                    article=article_no, paragraph=para_num, subparagraph=None
                )
            else:
                chunk_id = parent_id
                strategy = SplitStrategyEnum.atomic
                new_hierarchy = HierarchyFine(
                    article=article_no, paragraph=None, subparagraph=None
                )

            citation = self._format_citation_fine(new_hierarchy, law_name)

            new_meta = base_metadata.model_copy()
            new_meta.split_strategy = strategy
            new_meta.is_expanded = False
            new_meta.hierarchy = new_hierarchy
            new_meta.citation_title = citation

            chunk = LawChunkFine(
                chunk_id=chunk_id,
                parent_id=parent_id,
                text=text.strip(),
                metadata=new_meta,
            )
            return [chunk]

    def _format_citation_fine(self, hierarchy: HierarchyFine, law_name: str) -> str:
        art_str = hierarchy.article
        if "-" in art_str:
            main_num, sub_num = art_str.split("-")
            main_cn = self._convert_to_chinese_numeral(int(main_num))
            sub_cn = self._convert_to_chinese_numeral(int(sub_num))
            art_text = f"第{main_cn}條之{sub_cn}"
        else:
            if art_str.isdigit():
                art_cn = self._convert_to_chinese_numeral(int(art_str))
                art_text = f"第{art_cn}條"
            else:
                art_text = f"第{art_str}條"

        title = f"{law_name}{art_text}"

        if hierarchy.paragraph:
            para_cn = self._convert_to_chinese_numeral(hierarchy.paragraph)
            title += f"第{para_cn}項"

        if hierarchy.subparagraph:
            sub_cn = self._convert_to_chinese_numeral(hierarchy.subparagraph)
            title += f"第{sub_cn}款"

        return title
