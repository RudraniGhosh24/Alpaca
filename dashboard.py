import streamlit as st
import subprocess
import json
import pandas as pd

st.set_page_config(page_title="HedgeOS", page_icon="🧠", layout="wide")

def run_alpaca_cli(args):
    try:
        cmd = ["./alpaca"] + args + ["--jq", "."]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        return None

st.title("🧠 HedgeOS: Volatility Harvester")
st.markdown("Live monitoring dashboard for the autonomous LLM options trader.")

# 1. Account Info
account = run_alpaca_cli(["account", "get"])
if account:
    col1, col2, col3 = st.columns(3)
    col1.metric("Buying Power", f"${float(account.get('buying_power', 0)):,.2f}")
    col2.metric("Portfolio Value", f"${float(account.get('portfolio_value', 0)):,.2f}")
    col3.metric("Status", account.get("status", "UNKNOWN"))
else:
    st.error("Could not connect to Alpaca CLI. Please authenticate.")

st.divider()

# 2. Live Orders
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
    df = pd.DataFrame(order_data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No active orders found. Run `volatility_harvester.py` to hunt for volatility!")

st.divider()

st.subheader("📡 How It Works")
st.markdown("""
1. **Live News Scraping:** Agent pulls live Yahoo Finance news for high-beta stocks.
2. **NVIDIA Nemotron 550B:** The LLM reads the news and predicts extreme volatility vs sideways trading.
3. **Alpaca CLI Execution:** If extreme volatility is detected, the agent mathematically prices and executes a **Delta-Neutral Straddle** directly via the Alpaca API.
""")
