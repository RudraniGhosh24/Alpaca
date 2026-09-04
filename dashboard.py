import streamlit as st
import subprocess
import json
import pandas as pd
import yfinance as yf
import os
import time
from openai import OpenAI

st.set_page_config(page_title="HedgeOS", page_icon="🧠", layout="wide")

def run_alpaca_cli(args):
    try:
        
        import platform
        binary = "./alpaca-linux" if platform.system() == "Linux" else "./alpaca"
        cmd = [binary] + args + ["--jq", "."]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        return None

def fetch_yahoo_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        news_items = ticker.news
        if not news_items:
            return "No recent news."
        headlines = [item['content']['title'] for item in news_items[:5] if 'content' in item and 'title' in item['content']]
        return "\n".join(headlines)
    except Exception as e:
        return f"Error fetching news: {e}"

def fetch_straddle_contracts(symbol):
    res = run_alpaca_cli(["data", "option", "chain", "--underlying-symbol", symbol, "--limit", "200"])
    if not res or "snapshots" not in res:
        return None
    snapshots = res["snapshots"]
    calls = {}
    puts = {}
    for contract, data in snapshots.items():
        suffix = contract[-15:]
        base = suffix[:6] + suffix[7:]
        cp = suffix[6]
        ask_price = data.get("latestQuote", {}).get("ap", 0.0)
        if ask_price > 0.10: 
            if cp == 'C': calls[base] = (contract, ask_price)
            elif cp == 'P': puts[base] = (contract, ask_price)
                
    best_straddle = None
    best_cost = float('inf')
    for base in calls:
        if base in puts:
            call_contract, call_ask = calls[base]
            put_contract, put_ask = puts[base]
            total_cost = call_ask + put_ask
            if total_cost < best_cost:
                best_cost = total_cost
                best_straddle = {
                    "call": call_contract, "call_ask": call_ask,
                    "put": put_contract, "put_ask": put_ask,
                    "total_cost": total_cost,
                    "strike": float(base[6:11]) + (float(base[11:])/1000)
                }
    return best_straddle

def submit_limit_order(contract_symbol, qty, limit_price, side="buy"):
    return run_alpaca_cli([
        "order", "submit", "--symbol", contract_symbol, "--qty", str(qty),
        "--side", side, "--type", "limit", "--limit-price", str(limit_price),
        "--time-in-force", "day"
    ])

st.title("🧠 HedgeOS: Autonomous Options Harvester")

account = run_alpaca_cli(["account", "get"])
if account:
    col1, col2, col3 = st.columns(3)
    col1.metric("Buying Power", f"${float(account.get('buying_power', 0)):,.2f}")
    col2.metric("Portfolio Value", f"${float(account.get('portfolio_value', 0)):,.2f}")
    col3.metric("Status", account.get("status", "UNKNOWN"))
else:
    st.error("Could not connect to Alpaca CLI. Please authenticate.")

st.divider()

if st.button("▶️ Initialize Harvester Agent", use_container_width=True):
    base_url = os.environ.get("OPENAI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    api_key = os.environ.get("OPENAI_API_KEY")
    model_name = os.environ.get("MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b")
    
    if not api_key:
        st.error("Please export OPENAI_API_KEY in your terminal before running streamlit.")
        st.stop()
        
    client = OpenAI(base_url=base_url, api_key=api_key)
    watchlist = ["NVDA", "TSLA", "PLTR"]
    
    for symbol in watchlist:
        with st.expander(f"📡 Processing {symbol}..."):
            st.write(f"**1. Scraping Live News for {symbol}...**")
            news = fetch_yahoo_news(symbol)
            st.code(news)
            
            st.write(f"**2. Prompting NVIDIA Nemotron 550B...**")
            prompt = f"Read the following recent news headlines for {symbol}:\n{news}\n\nWill this news cause EXTREME VOLATILITY (massive move) or SIDEWAYS trading? Reply strictly with only the word 'EXTREME' or 'SIDEWAYS'."
            
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                decision = response.choices[0].message.content.strip().upper()
                if "EXTREME" in decision:
                    st.success(f"🧠 LLM Prediction: {decision} VOLATILITY")
                else:
                    st.warning(f"🧠 LLM Prediction: {decision}")
                    
                if "EXTREME" in decision:
                    st.write("**3. Sourcing Straddle Contracts from Alpaca...**")
                    straddle = fetch_straddle_contracts(symbol)
                    if straddle:
                        st.write(f"✅ Found optimal Straddle at Strike {straddle['strike']} (Total Premium: ${straddle['total_cost']})")
                        
                        st.write("**4. Executing Multi-Leg Limit Orders...**")
                        call_res = submit_limit_order(straddle['call'], 1, round(straddle['call_ask']*1.05, 2))
                        put_res = submit_limit_order(straddle['put'], 1, round(straddle['put_ask']*1.05, 2))
                        
                        if call_res and "id" in call_res:
                            st.info(f"🎉 Call Order ID: {call_res.get('id')} ({call_res.get('status')})")
                        if put_res and "id" in put_res:
                            st.info(f"🎉 Put Order ID: {put_res.get('id')} ({put_res.get('status')})")
                    else:
                        st.error("❌ No valid option pairs found on Alpaca for Straddle.")
            except Exception as e:
                st.error(f"❌ Failed to get response from AI: {e}")
        time.sleep(1)
        
    st.success("✅ Harvester Loop Complete.")

st.divider()

st.subheader("🚀 Active Options Straddles (Live Orders)")
orders = run_alpaca_cli(["order", "list"])
if orders:
    order_data = []
    for o in orders:
        order_data.append({
            "Symbol": o.get("symbol"),
            "Side": o.get("side").upper(),
            "Qty": o.get("qty"),
            "Type": o.get("type").upper(),
            "Limit Price": f"${float(o.get('limit_price', 0)):.2f}" if o.get('limit_price') else "MKT",
            "Status": o.get("status").upper(),
            "Submitted At": o.get("submitted_at")[:10]
        })
    st.dataframe(pd.DataFrame(order_data), use_container_width=True)
