
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys
import time
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.app.rag.models.ingestion_models import RawLawData as LawData, RawLawArticle as LawArticle, LawCategory
    from scripts.law_scrape_utils import HEADERS, scrape_law_by_pcode
except ImportError as e:
    print(f"Could not import schemas or utils: {e}")
    sys.exit(1)

# Configuration
LAW_MAPPING = {
    "勞動基準法施行細則": {
        "filename": "enforcement_rules.json",
        "id_prefix": "ENF_RULE"
    },
    "勞動部積欠工資墊償基金管理委員會組織規程": {
        "filename": "wage_arrears_fund_mgmt_committee_org_rule.json",
        "id_prefix": "WAGE_ARREARS_FUND_COMM_ORG"
    },
    "積欠工資墊償基金提繳及墊償管理辦法": {
        "filename": "wage_arrears_fund_collection_payment_reg.json",
        "id_prefix": "WAGE_ARREARS_FUND_PAY_REG"
    },
    "勞工請假規則": {
        "filename": "labor_leave_rule.json",
        "id_prefix": "LEAVE_RULE"
    },
    "勞動基準法第四十五條無礙身心健康認定基準及審查辦法": {
        "filename": "lsa_mind_body_health_determination_std.json",
        "id_prefix": "LSA_HEALTH_DETERMINATION"
    },
    "事業單位僱用女性勞工夜間工作場所必要之安全衛生設施標準": {
        "filename": "female_labor_night_work_safety_std.json",
        "id_prefix": "FEMALE_NIGHT_SAFETY_STD"
    },
    "事業單位勞工退休準備金監督委員會組織準則": {
        "filename": "ret_reserve_sup_committee_org.json",
        "id_prefix": "RET_RESERVE_SUP_COMM_ORG"
    },
    "勞工退休基金收支保管及運用辦法": {
        "filename": "ret_fund_mgmt_reg.json",
        "id_prefix": "RET_FUND_MGMT_REG"
    },
    "勞工退休準備金提撥及管理辦法": {
        "filename": "ret_reserve_alloc_mgmt_reg.json",
        "id_prefix": "RET_RESERVE_ALLOC_REG"
    },
    "勞工退休準備金資料提供金融機構處理辦法": {
        "filename": "ret_reserve_fin_inst_data_reg.json",
        "id_prefix": "RET_RESERVE_FIN_INST_DATA"
    },
    "直轄市勞動檢查機構組織準則": {
        "filename": "municipal_labor_inspection_inst_org_rule.json",
        "id_prefix": "MUNI_INSPECT_INST_ORG"
    },
    "勞動基準法檢舉案件保密及處理辦法": {
        "filename": "lsa_report_confidentiality_proc_reg.json",
        "id_prefix": "LSA_REPORT_CONF_REG"
    },
    "勞資會議實施辦法": {
        "filename": "labor_mgmt_meeting_impl_measure.json",
        "id_prefix": "LABOR_MGMT_MEETING_IMPL"
    }
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'law_data', 'subsidiary_laws')

def get_subsidiary_laws_list(session):
    """
    Fetch the list of subsidiary laws from the entry URL.
    """
    url = "https://law.moj.gov.tw/LawClass/LawSlaveAll.aspx?pcode=N0030001"
    print(f"Fetching list from {url}...")
    try:
        response = session.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch list: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    laws = []
    
    # The structure usually contains links to LawAll.aspx
    for link in soup.find_all('a'):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        if 'LawAll.aspx' in href and 'pcode=' in href:
            match = re.search(r'pcode=([A-Z0-9]+)', href)
            if match:
                pcode = match.group(1)
                laws.append({'name': text, 'pcode': pcode})
                
    return laws

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # 1. Get List
    laws_list = get_subsidiary_laws_list(session)
    print(f"Found {len(laws_list)} links.")
    
    # 2. Iterate and Scrape
    count = 0
    for law in laws_list:
        name_clean = re.sub(r'（.*?）', '', law['name']).strip() # Remove date/status info often in parens
        
        if name_clean in LAW_MAPPING:
            config = LAW_MAPPING[name_clean]
            
            # rate limiting
            sleep_time = random.uniform(1, 3)
            print(f"Sleeping for {sleep_time:.2f}s...")
            time.sleep(sleep_time)
            
            law_data = scrape_law_by_pcode(session, law['pcode'], config, name_clean)
            
            if law_data:
                output_path = os.path.join(OUTPUT_DIR, config['filename'])
                with open(output_path, 'w', encoding='utf-8') as f:
                    json_data = law_data.model_dump(mode='json')
                    f.write(json.dumps(json_data, ensure_ascii=False, indent=2))
                print(f"Saved {output_path}")
                count += 1
        else:
            print(f"Skipping: {name_clean} (Not in target list)")

    print(f"Done. Processed {count} subsidiary laws.")

if __name__ == "__main__":
    main()
