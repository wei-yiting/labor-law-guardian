import unittest
from app.models.law import RawLawArticle
# Note: These modules are not yet implemented, but required for the test.
# We expect ImportError until implemented, verifying "Red" state of TDD.
try:
    from app.ingestion.law_article_chunker import LawArticleChunker
    from app.models.chunk import SplitStrategyEnum
except ImportError:
    pass

class TestLawArticleChunker(unittest.TestCase):
    def setUp(self):
        # We try to instantiate the chunker. If it doesn't exist, tests will fail (as expected in TDD)
        try:
            self.chunker = LawArticleChunker()
        except NameError:
            self.chunker = None

    def test_case_1_atomic_strategy_simple_article(self):
        """Case 1: Atomic Strategy (Simple Article)"""
        if not self.chunker:
            self.fail("LawArticleChunker not implemented")

        input_article = RawLawArticle(
            id="LSA-5",
            article_no="5",
            content="雇主不得以強暴、脅迫、拘禁或其他非法之方法，強制勞工從事勞動。",
            url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=5"
        )

        chunks = self.chunker.parse_article(input_article)
        
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertEqual(chunk.chunk_id, "LSA-5")
        self.assertEqual(chunk.parent_id, "LSA-5")
        self.assertEqual(chunk.text, "雇主不得以強暴、脅迫、拘禁或其他非法之方法，強制勞工從事勞動。")
        self.assertEqual(chunk.metadata.article_no, "5")
        self.assertEqual(chunk.metadata.split_strategy, SplitStrategyEnum.atomic)
        self.assertFalse(chunk.metadata.is_expanded)
        self.assertEqual(chunk.metadata.hierarchy.article, "5")
        self.assertIsNone(chunk.metadata.hierarchy.paragraph)
        self.assertIsNone(chunk.metadata.hierarchy.subparagraph)
        self.assertEqual(chunk.metadata.citation_title, "勞動基準法第五條")

    def test_case_2_numeric_strategy_standard_paragraphs(self):
        """Case 2: Numeric Strategy (Standard Paragraphs)"""
        if not self.chunker:
            self.fail("LawArticleChunker not implemented")

        input_article = RawLawArticle(
            id="LSA-23",
            article_no="23",
            content="(1)工資之給付，除當事人有特別約定或按月預付者外，每月至少定期發給二次，並應提供工資各項目計算方式明細；按件計酬者亦同。\n(2)雇主應置備勞工工資清冊，將發放工資、工資各項目計算方式明細、工資總額等事項記入。工資清冊應保存五年。",
            url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=23"
        )

        chunks = self.chunker.parse_article(input_article)
        
        self.assertEqual(len(chunks), 2)
        
        # Chunk 1
        c1 = chunks[0]
        self.assertEqual(c1.chunk_id, "LSA-23_P1")
        self.assertEqual(c1.parent_id, "LSA-23")
        self.assertEqual(c1.text, "(1)工資之給付，除當事人有特別約定或按月預付者外，每月至少定期發給二次，並應提供工資各項目計算方式明細；按件計酬者亦同。")
        self.assertEqual(c1.metadata.split_strategy, SplitStrategyEnum.numeric)
        self.assertEqual(c1.metadata.hierarchy.paragraph, 1)
        self.assertEqual(c1.metadata.citation_title, "勞動基準法第二十三條第一項")

        # Chunk 2
        c2 = chunks[1]
        self.assertEqual(c2.chunk_id, "LSA-23_P2")
        self.assertEqual(c2.parent_id, "LSA-23")
        self.assertEqual(c2.text, "(2)雇主應置備勞工工資清冊，將發放工資、工資各項目計算方式明細、工資總額等事項記入。工資清冊應保存五年。")
        self.assertEqual(c2.metadata.split_strategy, SplitStrategyEnum.numeric)
        self.assertEqual(c2.metadata.hierarchy.paragraph, 2)
        self.assertEqual(c2.metadata.citation_title, "勞動基準法第二十三條第二項")

    def test_case_3_contextual_strategy_subparagraphs_only(self):
        """Case 3: Contextual Strategy (Subparagraphs only)"""
        if not self.chunker:
            self.fail("LawArticleChunker not implemented")

        input_article = RawLawArticle(
            id="LSA-2",
            article_no="2",
            content="本法用詞，定義如下：\n一、勞工：指受雇主僱用從事工作獲致工資者。\n二、雇主：指僱用勞工之事業主、事業經營之負責人或代表事業主處理有關勞工事務之人。",
            url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=2"
        )

        chunks = self.chunker.parse_article(input_article)
        
        self.assertEqual(len(chunks), 2)
        
        # Chunk 1
        c1 = chunks[0]
        self.assertEqual(c1.chunk_id, "LSA-2_S1")
        self.assertEqual(c1.text, "本法用詞，定義如下：一、勞工：指受雇主僱用從事工作獲致工資者。")
        self.assertEqual(c1.metadata.split_strategy, SplitStrategyEnum.contextual)
        self.assertTrue(c1.metadata.is_expanded)
        self.assertEqual(c1.metadata.hierarchy.subparagraph, 1)
        self.assertEqual(c1.metadata.citation_title, "勞動基準法第二條第一款")

        # Chunk 2
        c2 = chunks[1]
        self.assertEqual(c2.chunk_id, "LSA-2_S2")
        self.assertEqual(c2.text, "本法用詞，定義如下：二、雇主：指僱用勞工之事業主、事業經營之負責人或代表事業主處理有關勞工事務之人。")
        self.assertEqual(c2.metadata.split_strategy, SplitStrategyEnum.contextual)
        self.assertEqual(c2.metadata.hierarchy.subparagraph, 2)
        self.assertEqual(c2.metadata.citation_title, "勞動基準法第二條第二款")

    def test_case_4_dash_article_handling(self):
        """Case 4: Dash Article Handling"""
        if not self.chunker:
            self.fail("LawArticleChunker not implemented")

        input_article = RawLawArticle(
            id="LSA-84-2",
            article_no="84-2",
            content="勞工工作年資自受僱之日起算...",
            url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=84-2"
        )

        chunks = self.chunker.parse_article(input_article)
        
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertEqual(chunk.chunk_id, "LSA-84-2")
        self.assertEqual(chunk.text, "勞工工作年資自受僱之日起算...")
        self.assertEqual(chunk.metadata.citation_title, "勞動基準法第八十四條之二")

    def test_case_5_recursive_strategy(self):
        """Case 5: Recursive Strategy (Numeric + Contextual)"""
        if not self.chunker:
            self.fail("LawArticleChunker not implemented")

        content_79 = (
            "(1)有下列各款規定行為之一者，處新臺幣二萬元以上一百萬元以下罰鍰：\n"
            "一、違反第二十一條第一項、第二十二條至第二十五條...規定。\n"
            "二、違反主管機關依第二十七條限期給付工資...命令。\n"
            "三、違反中央主管機關依第四十三條所定假期...標準。\n"
            "(2)違反第三十條第五項或第四十九條第五項規定者，處新臺幣九萬元以上四十五萬元以下罰鍰。\n"
            "(3)違反第七條...處新臺幣二萬元以上三十萬元以下罰鍰。\n"
            "(4)有前三項規定行為之一者...。"
        )

        input_article = RawLawArticle(
            id="LSA-79",
            article_no="79",
            content=content_79,
            url="https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode=N0030001&flno=79"
        )

        chunks = self.chunker.parse_article(input_article)
        
        # P1 has 3 Subparagraphs -> 3 chunks
        # P2, P3, P4 are Atomic Paragraphs -> 3 chunks
        # Total = 6
        self.assertEqual(len(chunks), 6)

        # Check P1 S1
        c1 = chunks[0]
        self.assertEqual(c1.chunk_id, "LSA-79_P1_S1")
        self.assertEqual(c1.text, "(1)有下列各款規定行為之一者，處新臺幣二萬元以上一百萬元以下罰鍰：一、違反第二十一條第一項、第二十二條至第二十五條...規定。")
        self.assertEqual(c1.metadata.split_strategy, SplitStrategyEnum.numeric_contextual)
        self.assertEqual(c1.metadata.hierarchy.paragraph, 1)
        self.assertEqual(c1.metadata.hierarchy.subparagraph, 1)
        self.assertEqual(c1.metadata.citation_title, "勞動基準法第七十九條第一項第一款")

        # Check P1 S2
        c2 = chunks[1]
        self.assertEqual(c2.chunk_id, "LSA-79_P1_S2")
        self.assertEqual(c2.text, "(1)有下列各款規定行為之一者，處新臺幣二萬元以上一百萬元以下罰鍰：二、違反主管機關依第二十七條限期給付工資...命令。")
        self.assertEqual(c2.metadata.hierarchy.paragraph, 1)
        self.assertEqual(c2.metadata.hierarchy.subparagraph, 2)
        self.assertEqual(c2.metadata.citation_title, "勞動基準法第七十九條第一項第二款")
        
        # Check P2
        c4 = chunks[3]
        self.assertEqual(c4.chunk_id, "LSA-79_P2")
        self.assertEqual(c4.text, "(2)違反第三十條第五項或第四十九條第五項規定者，處新臺幣九萬元以上四十五萬元以下罰鍰。")
        self.assertEqual(c4.metadata.split_strategy, SplitStrategyEnum.numeric)
        self.assertEqual(c4.metadata.hierarchy.paragraph, 2)
        self.assertEqual(c4.metadata.citation_title, "勞動基準法第七十九條第二項")

if __name__ == "__main__":
    unittest.main()
