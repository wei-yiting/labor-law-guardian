
import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys

# Add project root to path to import schemas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.app.schemas.law import LawData, LawArticle, LawCategory
except ImportError:
    print("Could not import schemas. Please ensure you are running from project root or scripts directory.")
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://law.moj.gov.tw/",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

CN_NUMBERS = {
    '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
}

def chinese_to_int(cn_str):
    if not cn_str:
        return 0
    
    result = 0
    temp_val = 0
    
    if len(cn_str) == 1 and cn_str in CN_NUMBERS:
        return CN_NUMBERS[cn_str]
        
    for char in cn_str:
        if char == '十':
            result += (temp_val if temp_val > 0 else 1) * 10
            temp_val = 0
        elif char in CN_NUMBERS:
            temp_val = CN_NUMBERS[char]
            
    result += temp_val
    return result

def parse_chapter_title(text):
    match = re.search(r"第\s*([一二三四五六七八九十]+)\s*章\s*(.+)", text.strip())
    if match:
        cn_num = match.group(1)
        name = match.group(2).strip()
        return chinese_to_int(cn_num), name
    return None, text

def parse_article_no(text):
    match = re.search(r"第\s*([\d\-]+)\s*條", text.strip())
    if match:
        return match.group(1)
    return text

def parse_content_with_hierarchy(col_data_element):
    """
    Parse content preserving hierarchy.
    Handles 'show-number' class which serves as a CSS counter for paragraphs (1, 2, 3...).
    Structure: col-data -> div.law-article -> div.show-number
    """
    # Try finding the wrapper law-article first
    law_article_div = col_data_element.find('div', class_='law-article')
    target_container = law_article_div if law_article_div else col_data_element
    
    children = target_container.find_all('div', recursive=False)
    
    # If no div structure found, fallback to simple text extraction
    if not children:
        return col_data_element.get_text(separator="\n", strip=True)

    lines = []
    current_number = 0
    
    for child in children:
        classes = child.get('class', [])
        text = child.get_text(strip=True)
        
        # Check for show-number class which implies an ordered list item (1, 2, 3...)
        if 'show-number' in classes:
            current_number += 1
            # Prepend the number to the text with parentheses. 
            lines.append(f"({current_number}){text}")
        else:
            lines.append(text)
            
    return "\n".join(lines)

def scrape_law(target_config, session):
    url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={target_config['pcode']}"
    print(f"Scraping {url}...")
    try:
        response = session.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch URL: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    main_content = soup.find('div', class_='law-reg-content')
    
    if not main_content:
        print("Could not find law content div.")
        return None

    articles = []
    current_chapter_no = 0
    current_chapter_name = "總則" 
    
    for element in main_content.find_all('div', recursive=False):
        classes = element.get('class', [])
        
        if 'h3' in classes:
            text = element.get_text(strip=True)
            c_no, c_name = parse_chapter_title(text)
            if c_no:
                current_chapter_no = c_no
                current_chapter_name = c_name
            continue
            
        if "row" in classes:
            col_no = element.find('div', class_='col-no')
            col_data = element.find('div', class_='col-data')
            
            if col_no and col_data:
                raw_article_no = col_no.get_text(strip=True)
                article_no_str = parse_article_no(raw_article_no)
                
                content = parse_content_with_hierarchy(col_data)
                content = re.sub(r'\n{3,}', '\n\n', content)
                
                article_id = f"{target_config['id_prefix']}-{article_no_str}"
                single_article_url = f"https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode={target_config['pcode']}&flno={article_no_str}"
                
                law_article = LawArticle(
                    id=article_id,
                    chapter_no=current_chapter_no,
                    chapter_name=current_chapter_name,
                    article_no=article_no_str,
                    content=content,
                    url=single_article_url,
                    summary=None,
                    related_concepts=[]
                )
                articles.append(law_article)

    return LawData(
        category=target_config['category'],
        title=target_config['title'],
        articles=articles
    )

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        session.get("https://law.moj.gov.tw/")
    except Exception as e:
        print(f"Warning: Failed to visit homepage to set cookies: {e}")

    targets = [
        {
            "pcode": "N0030001",
            "filename": "labor_standards_act.json",
            "category": LawCategory.MOTHER_LAW,
            "id_prefix": "LSA",
            "title": "勞動基準法"
        },
        {
            "pcode": "N0030002",
            "filename": "enforcement_rules.json",
            "category": LawCategory.SUBSIDIARY_LAW,
            "id_prefix": "ENF_RULE",
            "title": "勞動基準法施行細則"
        }
    ]

    for target in targets:
        law_data = scrape_law(target, session)
        if law_data:
            output_path = target['filename']
            with open(output_path, 'w', encoding='utf-8') as f:
                json_data = law_data.model_dump(mode='json')
                f.write(json.dumps(json_data, ensure_ascii=False, indent=2))
            print(f"Saved {output_path}")

if __name__ == "__main__":
    main()
