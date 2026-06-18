import yfinance as yf
import pandas as pd
import pandas_ta as ta

def get_stock_data(symbol, period="2y"):
    """
    指定されたシンボルの株価・投資信託データを取得する。
    period: 取得期間（例: "6mo", "1y", "2y"）
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            return None
            
        # 欠損値がある場合は前日終値などで埋める（投資信託等への対応）
        df = df.ffill().bfill()
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def calculate_technical_indicators(df):
    """
    pandas_ta を使って基本的なテクニカル指標を計算する。
    """
    if df is None or len(df) < 50:
        # データが少なすぎる場合は計算をスキップ
        return df
        
    try:
        # 単純移動平均線 (SMA)
        df.ta.sma(length=25, append=True)
        df.ta.sma(length=50, append=True)
        
        # RSI (相対力指数)
        df.ta.rsi(length=14, append=True)
        
        # MACD (マックディー)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        
        return df
    except Exception as e:
        print(f"Error calculating technical indicators: {e}")
        return df

def get_latest_indicators_summary(df):
    """
    最新のテクニカル指標の数値を辞書型で返す。
    LLMへのプロンプト作成時に使用。
    """
    if df is None or df.empty:
        return None
        
    latest = df.iloc[-1]
    
    # 指標のキーは pandas_ta によって自動生成される名前になる
    # 例: SMA_25, RSI_14, MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    
    summary = {
        "Date": df.index[-1].strftime("%Y-%m-%d"),
        "Close": round(latest.get("Close", 0), 2),
    }
    
    if "SMA_25" in df.columns:
        summary["SMA_25"] = round(latest["SMA_25"], 2)
    if "SMA_50" in df.columns:
        summary["SMA_50"] = round(latest["SMA_50"], 2)
    if "RSI_14" in df.columns:
        summary["RSI_14"] = round(latest["RSI_14"], 2)
    if "MACD_12_26_9" in df.columns:
        summary["MACD"] = round(latest["MACD_12_26_9"], 2)
    if "MACDs_12_26_9" in df.columns:
        summary["MACD_Signal"] = round(latest["MACDs_12_26_9"], 2)
        
    return summary
