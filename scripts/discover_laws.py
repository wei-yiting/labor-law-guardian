
import requests
from bs4 import BeautifulSoup
import time

url = "https://law.moj.gov.tw/LawClass/LawSlaveAll.aspx?pcode=N0030001"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Inspect structure
# Based on common structures, or try to find links with pcode
links = soup.find_all('a')
for link in links:
    href = link.get('href', '')
    if 'LawAll.aspx' in href and 'pcode=' in href:
        print(f"Name: {link.get_text().strip()} | URL: {href}")
