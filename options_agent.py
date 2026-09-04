import os
import sys
import json
import subprocess
import time
from google import genai

def run_alpaca_cli(args):
    """Run an Alpaca CLI command and return JSON."""
    try:
        cmd = ["./alpaca"] + args + ["--jq", "."]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Alpaca CLI Error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print("Failed to decode JSON from Alpaca CLI.")
        return None

def get_account_status():
    return run_alpaca_cli(["account", "get"])

def get_first_option_contract(symbol="SPY"):
    print(f"🔍 Fetching valid Option Chain for {symbol}...")
    res = run_alpaca_cli(["data", "option", "chain", "--underlying-symbol", symbol, "--limit", "1", "--type", "call"])
    if res and "snapshots" in res:
        snapshots = res["snapshots"]
        if snapshots:
            contract = list(snapshots.keys())[0]
            # Try to get the ask price from latestQuote
            ask_price = snapshots[contract].get("latestQuote", {}).get("ap", 1.00)
            if ask_price == 0:
                ask_price = 1.00
            return contract, ask_price
    return None, None

def get_news(symbol):
    return f"BREAKING: Huge unexpected macroeconomic catalyst detected. Sentiment is massively bullish for {symbol}."

def submit_option_order(contract_symbol, qty, limit_price, side="buy"):
    print(f"\n[Agent] EXECUTING TRADE: {side.upper()} {qty} of {contract_symbol} at Limit ${limit_price}")
    return run_alpaca_cli([
        "order", "submit",
        "--symbol", contract_symbol,
        "--qty", str(qty),
        "--side", side,
        "--type", "limit",
        "--limit-price", str(limit_price),
        "--time-in-force", "day"
    ])

def llm_reasoning_loop(symbol="SPY"):
    print("========================================")
    print(f"🤖 HEDGE OS: OPTIONS TRADING AGENT INITIATED")
    print(f"🎯 Target Asset: {symbol}")
    print("========================================\n")
    
    # 1. Check Account
    account = get_account_status()
    if account:
        print(f"💰 Account Validated. Buying Power: ${account.get('buying_power', 'N/A')}")
    else:
        print("❌ Could not connect to Alpaca. Please run: ./alpaca profile login")
        return

    # 2. Get News
    news = get_news(symbol)
    print(f"📰 Incoming News Feed: {news}")

    # 3. Find a real Option Contract via Alpaca CLI
    contract, ask_price = get_first_option_contract(symbol)
    if not contract:
        print("❌ Could not fetch option chain. Market might be closed or symbol is invalid.")
        return
    print(f"✅ Found Option Contract: {contract} (Ask: ${ask_price})")

    # 4. Consult LLM
    print("\n🧠 Consulting LLM for Options Strategy...")
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("⚠️ Warning: GEMINI_API_KEY not found in environment.")
        print("⚠️ Simulating LLM decision for the demo...")
        decision = "CALL"
    else:
        client = genai.Client(api_key=api_key)
        prompt = f"You are an expert options trader. The current news for {symbol} is: '{news}'. Should we BUY a CALL or BUY a PUT? Answer with only 'CALL' or 'PUT'."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        decision = response.text.strip()
        
    print(f"   -> LLM Output: {decision}")

    # 5. Agent Execution
    if "CALL" in decision.upper() or decision == "BUY":
        print(f"\n🚀 STRATEGY SELECTED: Bullish. Preparing to execute Call Option on {symbol}.")
        print(f"   -> Submitting Order for {contract}...")
        
        # ACTUALLY SUBMIT THE TRADE!
        # Adding a slight premium to the ask price to ensure it gets queued/filled
        trade_res = submit_option_order(contract, 1, round(ask_price * 1.05, 2), "buy")
        if trade_res and "id" in trade_res:
            print(f"🎉 Trade Submitted! Order ID: {trade_res.get('id')}")
            print(f"Status: {trade_res.get('status')}")
        else:
            print("❌ Trade submission failed.")
            print(f"Error Details: {trade_res}")
    
    print("\n✅ Trading loop complete.")

if __name__ == "__main__":
    llm_reasoning_loop()
