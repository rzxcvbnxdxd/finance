import pandas as pd
import json

url = 'https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls'
print("Downloading data...")
df = pd.read_excel(url, engine='xlrd')

# Expected columns: 日付, コード, 銘柄名, 市場・商品区分, ...
# The code is usually "コード", name is "銘柄名"
stock_list = []
for index, row in df.iterrows():
    code = str(row.get('コード', ''))
    name = str(row.get('銘柄名', ''))
    if code.isdigit():
        stock_list.append({
            "code": f"{code}.T",
            "name": name,
            "search_text": f"{code} {name}"
        })

with open('stock_list.json', 'w', encoding='utf-8') as f:
    json.dump(stock_list, f, ensure_ascii=False)
print(f"Saved {len(stock_list)} stocks to stock_list.json")
