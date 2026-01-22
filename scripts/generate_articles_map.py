
import json
import sys
from pathlib import Path

# Adjust sys.path to ensure absolute imports work from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.data.law_data.law_config import LAW_DATA_DIR, LAW_FILES

def generate_articles_map():
    articles_map = {}
    total_articles = 0

    print("Generating articles map...")
    
    for law_info in LAW_FILES:
        name = law_info["name"]
        rel_path = law_info["path"]
        
        full_path = LAW_DATA_DIR / rel_path
        
        if not full_path.exists():
            print(f"Warning: File not found for {name}: {full_path}")
            continue
            
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                articles = data.get("articles", [])
                
                count = 0
                for article in articles:
                    aid = article.get("id")
                    if aid:
                        articles_map[aid] = article
                        count += 1
                
                print(f"Loaded {count} articles from {name} ({rel_path})")
                total_articles += count
                
        except Exception as e:
            print(f"Error loading {name} at {full_path}: {e}")

    output_path = LAW_DATA_DIR / "articles_map.json"
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(articles_map, f, ensure_ascii=False, indent=2)
        print(f"\nSuccessfully generated articles_map.json at {output_path}")
        print(f"Total Unique Articles: {len(articles_map)}")
        print(f"Total Processed Articles: {total_articles}")
        
    except Exception as e:
        print(f"Error saving articles_map.json: {e}")

if __name__ == "__main__":
    generate_articles_map()
