import json
import os
import yfinance as yf
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STOCK_LIST_FILE = os.path.join(BASE_DIR, 'stock_list.json')
_local_stocks = []

def load_local_stocks():
    global _local_stocks
    if os.path.exists(STOCK_LIST_FILE):
        try:
            with open(STOCK_LIST_FILE, 'r', encoding='utf-8') as f:
                _local_stocks = json.load(f)
        except Exception as e:
            print(f"Error loading {STOCK_LIST_FILE}: {e}")

def get_suggestions(query):
    query = query.strip().lower()
    if not query:
        return []

    results = []
    
    # 1. Search local JPX json
    if _local_stocks:
        for stock in _local_stocks:
            if query in stock['search_text'].lower() or query in stock['name'].lower() or query in stock['code']:
                results.append((stock['code'], stock['name']))
                if len(results) >= 10:
                    break
    
    # 2. YFJ Fallback (For Hiragana/Romaji or unconfirmed IME input)
    if not results:
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse
            import re
            
            q = urllib.parse.quote(query)
            r = requests.get(f'https://finance.yahoo.co.jp/search/?query={q}', headers={'User-Agent': 'Mozilla/5.0'}, timeout=2)
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=lambda href: href and '/quote/' in href)
            seen = set()
            for a in links:
                href = a['href']
                m = re.search(r'/quote/([0-9A-Za-z.]+)', href)
                if m:
                    code = m.group(1)
                    if code not in seen:
                        seen.add(code)
                        
                        # 名前から不要な文字を取り除く (簡易的)
                        raw_name = a.text.strip()
                        # '7203 PRM トヨタ自動車...' のようになっているため、
                        # コードや市場区分を取り除きたいが、単純に表示する
                        # 長すぎる場合はカット
                        if len(raw_name) > 20:
                            raw_name = raw_name[:20] + "..."
                        
                        results.append((code, raw_name))
                if len(results) >= 5:
                    break
        except Exception as e:
            print("YFJ search error:", e)

    # 3. If still no local match and query is purely alphabetic (likely US stock/crypto), use yf.Search
    if not results and query.isalnum():
        try:
            s = yf.Search(query, max_results=5)
            for q in s.quotes:
                sym = q.get('symbol', '')
                name = q.get('shortname', '')
                if sym:
                    results.append((sym, name))
        except Exception as e:
            print(f"yfinance search error: {e}")

    return results

# Load on import
load_local_stocks()
