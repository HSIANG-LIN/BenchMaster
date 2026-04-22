import pandas as pd
import yfinance as yf
import requests
import datetime
import os
import sys

# === Configuration ===
# In production, use environment variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "807353647")

# Target rules
MIN_VOLUME = 5000
MIN_VOL_GROWTH = 1.2  # 20% increase
MIN_SECTOR_RISING = 1 

# A realistic list of Taiwan stocks (adding .TW suffix)
STOCK_LIST = list(set([
    "2330.TW", "2317.TW", "2454.TW", "2357.TW", "2376.TW", "3231.TW", "2379.TW", "2455.TW", "2377.TW", "2382.TW",
    "2383.TW", "2353.TW", "2345.TW", "2457.TW", "2314.TW", "2308.TW", "2352.TW", "2368.TW", "2372.TW", "2472.TW",
    "2349.TW", "2454.TW", "2317.TW", "2330.TW", "2357.TW", "2376.TW", "3231.TW", "2379.TW", "2455.TW", "2377.TW",
    "2382.TW", "2383.TW", "2353.TW", "2345.TW", "2457.TW", "2314.TW", "2308.TW", "2352.TW", "2368.TW", "2372.TW"
]))

def send_telegram(message):
    if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Error: Telegram token not set.")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        print("Telegram message sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def run_scanner():
    print("🚀 Starting Smart Stock Scanner (using yfinance)...")
    
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    print(f"📈 Fetching data for {len(STOCK_LIST)} stocks from {start_date} to {end_date}...")
    
    candidates = []
    
    for symbol in STOCK_LIST:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty or len(df) < 11:
                continue
            
            # Ensure columns are flat (not MultiIndex)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Rule 1: Volume > 5000
            vol = df['Volume'].iloc[-1]
            if vol <= MIN_VOLUME:
                continue
                
            # Rule 2: Price > MA5 or MA10
            df['ma5'] = df['Close'].rolling(window=5).mean()
            df['ma10'] = df['Close'].rolling(window=10).mean()
            
            # Accessing by index to be safe
            current_price = df['Close'].iloc[-1]
            ma5 = df['ma5'].iloc[-1]
            ma10 = df['ma10'].iloc[-1]
            
            if not (current_price > ma5 or current_price > ma10):
                continue
                
            # Rule 3: Volume growth > 20%
            prev_vol = df['Volume'].iloc[-2]
            vol_growth = (vol / prev_vol) if prev_vol > 0 else 0
            if vol_growth < MIN_VOL_GROWTH:
                continue
            
            # If passed, add to candidates
            candidates.append({
                'symbol': symbol,
                'price': current_price,
                'vol': vol,
                'vol_growth': vol_growth,
                'change_pct': ((current_price / df['Close'].iloc[-2]) - 1) * 100
            })
        except Exception as e:
            print(f"⚠️ Error scanning {symbol}: {e}")
            continue

    if not candidates:
        print("ℹ️ No stocks met the criteria today.")
        return

    candidate_df = pd.DataFrame(candidates)
    
    # Rule 4: Sector Strength
    print("🔍 Checking sector strength for candidates...")
    
    sector_data = []
    for _, row in candidate_df.iterrows():
        try:
            t = yf.Ticker(row['symbol'])
            # yfinance sector might be None
            sector = t.info.get('sector', 'Unknown')
            sector_data.append(sector)
        except:
            sector_data.append('Unknown')
    
    candidate_df['sector'] = sector_data
    
    # For the demo, let's say a sector is strong if it has at least 1 candidate
    sector_counts = candidate_df[candidate_df['change_pct'] > 0].groupby('sector').size()
    strong_sectors = sector_counts[sector_counts >= MIN_SECTOR_RISING].index.tolist()
    
    final_candidates = candidate_df[candidate_df['sector'].isin(strong_sectors)]
    
    if final_candidates.empty:
        print("ℹ️ No stocks from strong sectors met the criteria.")
        return
        
    # Select top 10
    final_candidates = final_candidates.sort_values(by='vol_growth', ascending=False).head(10)
    
    # 4. Prepare Message
    msg = "<b>🚀 強勢選股報告 (yfinance 版)</b>\\n\\n"
    msg += f"📅 日期: {datetime.date.today()}\\n"
    msg += "--------------------------------\\n"
    
    for _, row in final_candidates.iterrows():
        msg += f"🔹 <b>{row['symbol']}</b>\\n"
        msg += f"   價格: {row['price']:.1f} | 漲幅: {row['change_pct']:+.2f}%\\n"
        msg += f"   成交量: {row['vol']:,} | 爆量: {row['vol_growth']:.1%}\\n"
        msg += f"   產業: {row['sector']}\\n\\n"
        
    msg += "--------------------------------\\n"
    msg += "✅ 篩選條件: 成交>5k, 站上MA5/10, 爆量>20%"
    
    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    run_scanner()
