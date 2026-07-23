import time
import requests
import pandas as pd
import numpy as np

# --- Configuration ---
TELEGRAM_BOT_TOKEN = "8307375515:AAEdiueipE-Y_a1-wMuQW6Fw6f14a361iu8"
TELEGRAM_CHAT_ID = "370736928"

SYMBOL = "PAXGUSDT"
TIMEFRAME = "5m"

SENSITIVITY = 1
ATR_PERIOD = 10

last_sent_signal = 0

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("Telegram Response Status:", res.status_code)
        if res.status_code != 200:
            print("Telegram Error Detail:", res.text)
    except Exception as e:
        print("Error sending message:", e)

def get_klines():
    url = f"https://api.kucoin.com/api/v1/market/candles?symbol={SYMBOL}&type={TIMEFRAME}"
    try:
        res = requests.get(url, timeout=10).json()
        if "data" in res and res["data"]:
            df = pd.DataFrame(res["data"], columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
            df = df.sort_values('time').reset_index(drop=True)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            return df
    except Exception as e:
        print("Error fetching data from KuCoin:", e)
    return None

def calculate_ut_bot(df):
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['prev_close']), 
                                     abs(df['low'] - df['prev_close'])))
    df['atr'] = df['tr'].rolling(ATR_PERIOD).mean()
    df['nLoss'] = SENSITIVITY * df['atr']

    trailing_stop = [0.0] * len(df)
    position = [0] * len(df)

    for i in range(1, len(df)):
        prev_ts = trailing_stop[i-1]
        close = df['close'].iloc[i]
        prev_close = df['close'].iloc[i-1]
        nLoss = df['nLoss'].iloc[i]

        if close > prev_ts and prev_close > prev_ts:
            trailing_stop[i] = max(prev_ts, close - nLoss)
        elif close < prev_ts and prev_close < prev_ts:
            trailing_stop[i] = min(prev_ts, close + nLoss)
        elif close > prev_ts:
            trailing_stop[i] = close - nLoss
        else:
            trailing_stop[i] = close + nLoss

        if close > trailing_stop[i] and prev_close <= trailing_stop[i-1]:
            position[i] = 1
        elif close < trailing_stop[i] and prev_close >= trailing_stop[i-1]:
            position[i] = -1
        else:
            position[i] = position[i-1]

    df['signal'] = position
    return df

print("Starting Bot...")
send_telegram_msg("🚀 <b>Bot Gold កំពុងចាប់ផ្តើមដំណើរការលើ Render...</b>")

while True:
    try:
        df = get_klines()
        if df is not None and len(df) > ATR_PERIOD:
            df = calculate_ut_bot(df)
            
            closed_candle = df.iloc[-2]
            current_signal = int(closed_candle['signal'])
            entry_price = float(closed_candle['close'])

            print(f"[{time.strftime('%H:%M:%S')}] Price: {entry_price:.2f} | Current Signal: {current_signal} | Last Sent: {last_sent_signal}")

            if current_signal != last_sent_signal and current_signal != 0:
                signal_type = "BUY" if current_signal == 1 else "SELL"
                
                if signal_type == "BUY":
                    tp = entry_price + 5.0
                    sl = entry_price - 3.0
                    icon = "🔵 Entry Buy"
                else:
                    tp = entry_price - 5.0
                    sl = entry_price + 3.0
                    icon = "🔵 Entry Sell"

                msg = (
                    f"🔔 <b>Signal Gold Everyday</b>\n\n"
                    f"⏰ <b>Timeframe : 5minute</b>\n\n"
                    f"🌍 <b>Gold Now : {signal_type} 100%</b>\n"
                    f"{icon} : <b>{entry_price:.2f}</b>\n"
                    f"🟢 Take Profit: <b>{tp:.2f}</b>\n"
                    f"🔴 Stop Loss : <b>{sl:.2f}</b>"
                )

                send_telegram_msg(msg)
                print(f"--> SUCCESS: Sent Signal {signal_type}")
                last_sent_signal = current_signal

    except Exception as e:
        print("Error in loop:", e)

    time.sleep(15)
