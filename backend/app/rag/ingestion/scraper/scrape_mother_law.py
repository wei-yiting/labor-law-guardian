
import sys
import os
import json
import requests

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.app.schemas.law import LawData, LawArticle, LawCategory
    from scripts.law_scrape_utils import HEADERS, scrape_law_by_pcode
except ImportError as e:
    print(f"Could not import schemas or utils: {e}")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'law_data')

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        session.get("https://law.moj.gov.tw/")
    except Exception as e:
        print(f"Warning: Failed to visit homepage to set cookies: {e}")

    # Configuration for Mother Law
    target = {
        "pcode": "N0030001",
        "filename": "labor_standards_act.json",
        "id_prefix": "LSA",
        "title": "勞動基準法"
    }

    law_data = scrape_law_by_pcode(session, target['pcode'], target, target['title'])
    
    if law_data:
        output_path = os.path.join(OUTPUT_DIR, target['filename'])
        with open(output_path, 'w', encoding='utf-8') as f:
            json_data = law_data.model_dump(mode='json')
            f.write(json.dumps(json_data, ensure_ascii=False, indent=2))
        print(f"Saved {output_path}")

if __name__ == "__main__":
    main()
