
import json
from pathlib import Path
from typing import Dict, Any, Optional

class LawLookup:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.articles_map: Dict[str, Dict[str, Any]] = {}
        self.law_data_dir = self.project_root / "backend/data/law_data"
        self._load_data()

    def _load_data(self):
        map_path = self.law_data_dir / "articles_map.json"
        
        if not map_path.exists():
            print(f"Warning: Articles map not found at {map_path}")
            print("Please run `python scripts/generate_articles_map.py` to generate it.")
            return

        try:
            with open(map_path, "r", encoding="utf-8") as f:
                self.articles_map = json.load(f)
        except Exception as e:
            print(f"Error loading articles map: {e}")

    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        return self.articles_map.get(article_id)
