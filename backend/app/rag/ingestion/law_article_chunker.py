import re
import json
from typing import List, Optional, Dict
from pydantic import HttpUrl

from app.models.law import RawLawArticle
from app.models.chunk import LawChunk, ChunkMetadata, Hierarchy, SplitStrategyEnum

class LawArticleChunker:
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
                    # Handle raw list case if necessary, or just skip
                    pass
        return all_chunks

    def parse_article(self, article: RawLawArticle) -> List[LawChunk]:
        """
        Entry point for parsing a single article.
        """
        hierarchy = Hierarchy(article=article.article_no)
        metadata = ChunkMetadata(
            url=article.url,
            split_strategy=SplitStrategyEnum.atomic, # Initial value; refined in recursion
            is_expanded=False,
            citation_title="", # Initial value; populated based on final hierarchy
            hierarchy=hierarchy,
            chapter_no=article.chapter_no,
            chapter_title=article.chapter_name,
            article_no=article.article_no
        )
        
        return self._split_recursive(article.content, article.id, article.article_no, metadata)

    def _split_recursive(self, text: str, parent_id: str, article_no: str, base_metadata: ChunkMetadata) -> List[LawChunk]:
        """
        Recursive splitting logic.
        """
        # Step 1: Check for Numeric Paragraphs (e.g., "(1)")
        # Identify numeric patterns ((1), (2), etc.) at the start of lines
        numeric_pattern = re.compile(r'(?:^|\n)\s*\((\d+)\)')
        
        # Determine if we have numeric paragraphs
        matches = list(numeric_pattern.finditer(text))
        
        if matches:
            chunks = []
            # Iterate through all numeric matches to slice the text accordingly
            
            for i, match in enumerate(matches):
                start = match.start()
                # The regex `(?:^|\n)\s*\((\d+)\)` matches the newline before the number as well
                
                para_num = int(match.group(1))
                
                # The content of this paragraph starts after the full match
                content_start = match.end()
                
                # The content ends at the start of the next match, or end of text
                if i < len(matches) - 1:
                    content_end = matches[i+1].start()
                else:
                    content_end = len(text)
                
                # Reconstruct full text e.g. (1) content ...
                para_text = f"({para_num})" + text[content_start:content_end]
                # Strip leading/trailing whitespace from the extracted text section
                extracted_full_text = text[match.start():content_end].strip()
                
                # Recursively process this paragraph (check for Contextual Split)
                
                # Create base metadata for this paragraph
                para_hierarchy = Hierarchy(
                    article=article_no,
                    paragraph=para_num,
                    subparagraph=None
                )
                
                # Check for subparagraphs in this paragraph
                sub_chunks = self._process_subparagraphs(extracted_full_text, parent_id, article_no, base_metadata, para_num)
                chunks.extend(sub_chunks)
                
            return chunks

        # Step 2: Check for Subparagraphs (e.g., "一、")
        else:
            return self._process_subparagraphs(text, parent_id, article_no, base_metadata, None)

    def _process_subparagraphs(self, text: str, parent_id: str, article_no: str, base_metadata: ChunkMetadata, para_num: Optional[int]) -> List[LawChunk]:
        """
        Step 2 logic extracted to be reusable by Step 1.
        Checks for "一、", "二、"...
        """
        # Pattern for "One、" at start of line
        # Chinese numbers regex is tricky. [一二三...]+、
        sub_pattern = re.compile(r'(?:^|\n)\s*([一二三四五六七八九十百]+)、')
        
        matches = list(sub_pattern.finditer(text))
        
        if matches:
            chunks = []
            # Contextual Split
            # 1. Extract Preamble: text before the first match
            first_match_start = matches[0].start()
            preamble = text[:first_match_start].strip()
            
            for i, match in enumerate(matches):
                # Calculate subarray index (1-based index)
                # Assumption: Subparagraphs are ordered sequentially in the source text (一、, 二、, ...)
                current_sub_id = i + 1
                
                content_start = match.end()
                if i < len(matches) - 1:
                    content_end = matches[i+1].start()
                else:
                    content_end = len(text)
                
                item_text = text[match.start():content_end].strip() # Includes "一、..."
                
                # Combine Preamble + Item
                full_text = f"{preamble}{item_text}"
                
                # Construct Chunk
                
                # ID Construction
                if para_num:
                    chunk_id = f"{parent_id}_P{para_num}_S{current_sub_id}"
                    strategy = SplitStrategyEnum.numeric_contextual
                else:
                    chunk_id = f"{parent_id}_S{current_sub_id}"
                    strategy = SplitStrategyEnum.contextual
                
                new_hierarchy = Hierarchy(
                    article=article_no,
                    paragraph=para_num,
                    subparagraph=current_sub_id
                )
                
                citation = self._format_citation_title(new_hierarchy)
                
                new_meta = base_metadata.model_copy()
                new_meta.split_strategy = strategy
                new_meta.is_expanded = True
                new_meta.hierarchy = new_hierarchy
                new_meta.citation_title = citation
                
                chunk = LawChunk(
                    chunk_id=chunk_id,
                    parent_id=parent_id,
                    text=full_text,
                    metadata=new_meta
                )
                chunks.append(chunk)
            
            return chunks
        
        else:
            # Step 3: Atomic (Fallback)
            # If we are inside a paragraph (para_num is set), this is a "Numeric" chunk (Paragraph only)
            # If we are at top level (para_num None), this is "Atomic" chunk (Article only)
            
            if para_num:
                chunk_id = f"{parent_id}_P{para_num}"
                strategy = SplitStrategyEnum.numeric
                new_hierarchy = Hierarchy(
                    article=article_no,
                    paragraph=para_num,
                    subparagraph=None
                )
            else:
                chunk_id = parent_id # LSA-5
                strategy = SplitStrategyEnum.atomic
                new_hierarchy = Hierarchy(
                    article=article_no,
                    paragraph=None,
                    subparagraph=None
                )

            citation = self._format_citation_title(new_hierarchy)
            
            new_meta = base_metadata.model_copy()
            new_meta.split_strategy = strategy
            new_meta.is_expanded = False
            new_meta.hierarchy = new_hierarchy
            new_meta.citation_title = citation
            
            chunk = LawChunk(
                chunk_id=chunk_id,
                parent_id=parent_id,
                text=text.strip(),
                metadata=new_meta
            )
            return [chunk]

    def _convert_to_chinese_numeral(self, n: int) -> str:
        """
        Simple implementation handling 1-999.
        """
        digits = "零一二三四五六七八九"
        
        if n == 0:
            return digits[0]
            
        s = ""
        n_str = str(n)
        length = len(n_str)
        
        # Special case for 10-19: "十", "十一" (not "一十", "一十一")
        if 10 <= n < 20:
             if n == 10: return "十"
             s = "十" + digits[int(n_str[1])]
             return s

        # Logic for other numbers (1-9, >=20)
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
            if t == 1 and h == 0: # 10-19, but 10-19 is handled above, so this branch might be unreachable or implicit
                res += "十"
            else:
                res += digits[t] + "十"
        
        if u > 0:
            res += digits[u]
        
        return res



    def _format_citation_title(self, hierarchy: Hierarchy) -> str:
        """
        Logic: 勞動基準法 + 第{art}條 + (If P exists)第{P}項 + (If S exists)第{S}款
        Special Handling for "84-2": Must convert to 第八十四條之二
        """
        # Article Part
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
                art_text = f"第{art_str}條" # Fallback
                
        title = f"勞動基準法{art_text}"
        
        if hierarchy.paragraph:
            para_cn = self._convert_to_chinese_numeral(hierarchy.paragraph)
            title += f"第{para_cn}項"
            
        if hierarchy.subparagraph:
            sub_cn = self._convert_to_chinese_numeral(hierarchy.subparagraph)
            title += f"第{sub_cn}款"
            
        return title
