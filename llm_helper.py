from google import genai
import database

def get_api_key():
    return database.get_setting("GEMINI_API_KEY", "")

def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"Failed to configure Gemini: {e}")
        return None

def get_stock_analysis(symbol, name, indicators_summary):
    """
    指定銘柄のテクニカル指標を元にGeminiに分析させる
    """
    client = get_client()
    if not client:
        return "エラー: Gemini APIキーが設定されていないか、無効です。「Settings」タブから設定してください。"
        
    if not indicators_summary:
        return "エラー: 分析に必要なデータが不足しています（株価データが取得できないなど）。"

    prompt = f"""
あなたはプロの証券アナリストであり、親切な投資アドバイザーです。
以下の銘柄について、直近の株価とテクニカル指標のデータを提供します。
このデータをもとに、「買い判断」「売り判断」「現在の危険性（過熱感や下落リスク）」について、分かりやすくコメントしてください。
投資信託やETFの場合は、個別株ほどテクニカル指標が効かない場合がありますので、その点も加味して一般的なアドバイスをお願いします。

【対象銘柄】
シンボル: {symbol}
銘柄名: {name if name else "名称未設定"}

【最新データ ({indicators_summary.get('Date', 'N/A')})】
- 終値: {indicators_summary.get('Close', 'N/A')}
- 25日移動平均線(SMA25): {indicators_summary.get('SMA_25', 'N/A')}
- 50日移動平均線(SMA50): {indicators_summary.get('SMA_50', 'N/A')}
- RSI(14日): {indicators_summary.get('RSI_14', 'N/A')}
- MACD: {indicators_summary.get('MACD', 'N/A')}
- MACDシグナル: {indicators_summary.get('MACD_Signal', 'N/A')}

【出力形式の希望】
1. 現在の状況の要約
2. 買い判断についての見解
3. 売り判断についての見解
4. 危険性・注意点
"""
    try:
        return _generate_with_retry(client, 'gemini-2.5-flash', prompt)
    except Exception as e:
        return f"Gemini API通信エラー: {e}\n（アクセス集中により一時的に利用できない場合があります。しばらく経ってから再度お試しください）"

import time

def _generate_with_retry(client, model, contents, max_retries=3):
    last_exception = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents
            )
            return response.text
        except Exception as e:
            last_exception = e
            error_str = str(e).upper()
            if "503" in error_str or "UNAVAILABLE" in error_str or "429" in error_str or "TOO_MANY_REQUESTS" in error_str:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                    continue
            raise last_exception
            
def get_portfolio_advice(portfolio_items):
    """
    保有銘柄リストを元にGeminiに運用アドバイスを生成させる
    """
    client = get_client()
    if not client:
        return "エラー: Gemini APIキーが設定されていないか、無効です。「Settings」タブから設定してください。"

    if not portfolio_items:
        return "ポートフォリオに銘柄が登録されていません。"

    portfolio_text = ""
    for item in portfolio_items:
        portfolio_text += f"- {item['symbol']} ({item['name']}): 保有数 {item['quantity']}, 平均取得単価 {item['average_cost']}\n"

    prompt = f"""
あなたはプロの証券アナリストであり、親切な投資アドバイザーです。
以下のユーザーの現在のポートフォリオ（保有銘柄一覧）を見て、運用に関する総合的なアドバイスを提供してください。
日本株や投資信託が含まれることを想定しています。

【現在のポートフォリオ】
{portfolio_text}

【出力形式の希望】
1. ポートフォリオ全体のバランスや印象についてのコメント
2. 今後の運用に向けた具体的なアドバイスや見直しの提案
3. 追加で購入を検討すべきおすすめの銘柄や、今後上がる可能性が高いと予測される銘柄・セクターのサジェスト（現在のポートフォリオとの相性や分散を考慮して提案してください）
4. リスク管理に関する注意点
"""
    try:
        return _generate_with_retry(client, 'gemini-2.5-flash', prompt)
    except Exception as e:
        return f"Gemini API通信エラー: {e}\n（アクセス集中により一時的に利用できない場合があります。しばらく経ってから再度お試しください）"
