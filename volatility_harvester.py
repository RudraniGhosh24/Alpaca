import os
import json
import time
import subprocess
import yfinance as yf
from openai import OpenAI

def run_alpaca_cli(args):
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

def fetch_straddle_contracts(symbol):
    print(f"🔍 Fetching option chains for {symbol}...")
    res = run_alpaca_cli([
        "data", "option", "chain",
        "--underlying-symbol", symbol,
        "--limit", "200"
    ])
    if not res or "snapshots" not in res:
        return None

    snapshots = res["snapshots"]
    calls = {}
    puts = {}

    for contract, data in snapshots.items():
        suffix = contract[-15:]
        date_part = suffix[:6]
        cp = suffix[6]
        strike_part = suffix[7:]
        
        base = date_part + strike_part
        ask_price = data.get("latestQuote", {}).get("ap", 0.0)
        
        if ask_price > 0.10: 
            if cp == 'C':
                calls[base] = (contract, ask_price)
            elif cp == 'P':
                puts[base] = (contract, ask_price)
                
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

def submit_limit_order(contract_symbol, qty, limit_price, side="buy"):
    print(f"   -> [Agent] Executing {side.upper()} {qty} of {contract_symbol} at Limit ${limit_price}")
    return run_alpaca_cli([
        "order", "submit",
        "--symbol", contract_symbol,
        "--qty", str(qty),
        "--side", side,
        "--type", "limit",
        "--limit-price", str(limit_price),
        "--time-in-force", "day"
    ])

def main():
    print("==================================================")
    print("🧠 HEDGE OS: VOLATILITY HARVESTER (Straddle Agent)")
    print("==================================================\n")
    
    account = run_alpaca_cli(["account", "get"])
    if account:
        print(f"💰 Active Account. Buying Power: ${account.get('buying_power')}\n")
    else:
        print("❌ Could not connect to Alpaca.")
        return

    # Configuration for Featherless AI (or Nvidia NIM)
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.featherless.ai/v1")
    api_key = os.environ.get("OPENAI_API_KEY")
    # For Featherless AI, you can use any open-source model string. 
    # For Nvidia NIM, you might use "meta/llama3-70b-instruct"
    model_name = os.environ.get("MODEL_NAME", "meta-llama/Meta-Llama-3-70B-Instruct")

    if not api_key:
        print("⚠️ Warning: OPENAI_API_KEY not found in environment.")
        return
        
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    watchlist = ["NVDA", "CRWD", "PLTR", "TSLA"]

    for symbol in watchlist:
        print(f"\n========================================")
        print(f"📡 Analyzing {symbol}...")
        
        news = fetch_yahoo_news(symbol)
        print(f"📰 Latest Headlines:\n{news}\n")

        prompt = f"""
        You are an expert quantitative volatility trader. 
        Read the following recent news headlines for {symbol}:
        {news}
        
        Will this news cause EXTREME VOLATILITY (massive move up or down) or SIDEWAYS trading? 
        If it's extreme, we will execute an options straddle.
        Reply strictly with only the word 'EXTREME' or 'SIDEWAYS'. Do not output any other text.
        """
        
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            decision = response.choices[0].message.content.strip().upper()
            print(f"🧠 LLM Volatility Prediction ({model_name}): {decision}")
        except Exception as e:
            print(f"❌ Failed to get response from AI: {e}")
            continue

        if "EXTREME" in decision:
            print(f"⚠️ Extreme volatility detected. Sourcing Straddle contracts...")
            straddle = fetch_straddle_contracts(symbol)
            if not straddle:
                print("   ❌ No valid option pairs found on Alpaca for Straddle.")
                continue
                
            print(f"   ✅ Found optimal Straddle at Strike {straddle['strike']}")
            print(f"      Call: {straddle['call']} (Ask: ${straddle['call_ask']})")
            print(f"      Put:  {straddle['put']} (Ask: ${straddle['put_ask']})")
            print(f"      Total Premium: ${straddle['total_cost']}")
            
            print("\n🚀 Executing Straddle Limit Orders...")
            call_res = submit_limit_order(straddle['call'], 1, round(straddle['call_ask']*1.05, 2))
            put_res = submit_limit_order(straddle['put'], 1, round(straddle['put_ask']*1.05, 2))
            
            if call_res and "id" in call_res:
                print(f"   🎉 Call Order ID: {call_res.get('id')} ({call_res.get('status')})")
            if put_res and "id" in put_res:
                print(f"   🎉 Put Order ID: {put_res.get('id')} ({put_res.get('status')})")
        else:
            print(f"⏸️ No extreme catalyst. Skipping {symbol}.")
            
        time.sleep(2) 

if __name__ == "__main__":
    main()
