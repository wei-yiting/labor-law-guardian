from datetime import date
import re
import requests
from bs4 import BeautifulSoup
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from backend.app.schemas.law import LawData, LawArticle, LawCategory
except ImportError:
    pass 
    try:
        from backend.app.schemas.law import LawData, LawArticle, LawCategory
    except ImportError as e:
        print(f"Could not import schemas in law_utils: {e}")

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

def parse_chinese_date(date_str):
    """
    Parse Chinese date string like '中華民國 113 年 03 月 27 日' into datetime.date object.
    """
    if not date_str:
        return None
    try:
        # Expected format: 中華民國 113 年 03 月 27 日 or 民國 113 年 03 月 27 日
        match = re.search(r"(?:中華)?民國\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日", date_str)
        if match:
            year = int(match.group(1)) + 1911
            month = int(match.group(2))
            day = int(match.group(3))
            return date(year, month, day)
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
    return None

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

def scrape_law_by_pcode(session, pcode, config, law_name):
    """
    Unified scraping function (extracted from previous scripts).
    Traverses the LawAll page and extracts articles.
    """
    url = f"https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode={pcode}"
    print(f"Scraping {law_name} ({url})...")
    
    try:
        response = session.get(url)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract Last Modified Date
    last_modified_date = None
    date_text = None
    
    # Try standard ID for "Amendment Date"
    date_element = soup.find('tr', id='trLNNDate')
    if date_element:
        date_text = date_element.get_text(strip=True)
    else:
        # Fallback: Search for "Promulgation Date" or "Amendment Date" by text headers
        # Usually it's in a th/td structure
        for th in soup.find_all('th'):
            text = th.get_text(strip=True)
            if "修正日期" in text or "發布日期" in text:
                next_td = th.find_next_sibling('td')
                if next_td:
                    date_text = next_td.get_text(strip=True)
                    break
    
    if date_text:
        last_modified_date = parse_chinese_date(date_text)
    
    if not last_modified_date:
        print(f"Warning: Could not find last modified date for {law_name}")
        # Default to today or handle as None? Schema expects date, but let's see if we can make it optional or default.
        # Ideally we should find it. If not found, maybe None if schema allows, but schema has default?
        # User requested type should be date. Let's assume we find it or set a dummy if critical, 
        # but better to let Pydantic validation fail if strict or make it Optional in utils if needed.
        # Schema definition: last_modified_date: date
        # If we return None, pydantic might complain if not Optional. 
        # Let's check schema again. I set it to `date`, not `date | None`. 
        # So it is required. Valid laws should have it.
        pass

    main_content = soup.find('div', class_='law-reg-content')
    
    if not main_content:
        print(f"Could not find law content div for {law_name}")
        return None

    articles = []
    current_chapter_no = None
    current_chapter_name = None
    
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
                
                article_id = f"{config['id_prefix']}-{article_no_str}"
                single_article_url = f"https://law.moj.gov.tw/LawClass/LawSingle.aspx?pcode={pcode}&flno={article_no_str}"
                
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
    
    # Determine Category
    category = LawCategory.SUBSIDIARY_LAW
    if config.get('id_prefix') == 'LSA':
        category = LawCategory.MOTHER_LAW
        
    return LawData(
        category=category,
        title=law_name,
        last_modified_date=last_modified_date,
        articles=articles
    )
