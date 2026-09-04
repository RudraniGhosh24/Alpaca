# 🧠 VolHarvest: Autonomous Volatility Harvester

**🔥 [Live Demo Available Here](https://alpaca-hackathon.streamlit.app/) 🔥**

**VolHarvest** is an autonomous AI trading agent built for the Alpaca AI Trading Hackathon. Instead of making basic directional bets ("stock goes up"), VolHarvest uses large language models to analyze real-time macroeconomic news and execute **Delta-Neutral Options Straddles** via the Alpaca CLI to profit off pure market volatility.

## 🚀 How It Works

1. **Live News Scraping**: The agent iterates through a watchlist of high-beta tech stocks (NVDA, TSLA, CRWD, PLTR) and fetches the latest live news headlines via `yfinance`.
2. **LLM Volatility Reasoning**: It passes these headlines to an open-source Large Language Model (e.g., NVIDIA's `nemotron-3-ultra-550b-a55b` via the NVIDIA NIM API or Featherless AI). The LLM is prompted strictly as a Quantitative Analyst to predict if the catalyst will cause **EXTREME VOLATILITY** or **SIDEWAYS** trading.
3. **Autonomous Execution**: If the LLM predicts extreme volatility (e.g., an upcoming earnings call, product launch, or acquisition), VolHarvest:
   * Uses the **Alpaca CLI** to fetch the live options chain for the asset.
   * Parses the JSON to mathematically find the cheapest valid **Options Straddle** (buying a Call and a Put at the exact same strike price).
   * Automatically executes the multi-leg limit orders directly to the Alpaca Paper account.

If the LLM predicts "SIDEWAYS" trading, the agent smartly skips the trade to preserve capital.

## 🛠 Prerequisites

* Python 3.9+
* Alpaca Paper Trading Account (API Key & Secret)
* NVIDIA NIM API Key (or Featherless AI Key)

## ⚙️ Setup & Installation

1. **Clone the repository and enter the directory**:
   ```bash
   cd hackathon-agent
   ```

2. **Set up your Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install yfinance openai
   ```

3. **Install & Authenticate the Alpaca CLI**:
   * Ensure the `alpaca` CLI binary is in your directory (or installed globally).
   * Authenticate your paper account:
     ```bash
     ./alpaca profile login --api-key
     ```
     *(Paste your Alpaca API Key and Secret when prompted).*

## ▶️ Running the Agent

You need to set your LLM API credentials in your environment. We use NVIDIA's massive 550B Nemotron model for maximum reasoning capabilities.

Run the following commands in your terminal:

```bash
# Ensure your virtual environment is active
source venv/bin/activate

# Set your LLM API credentials (NVIDIA NIM example)
export OPENAI_BASE_URL="https://integrate.api.nvidia.com/v1"
export OPENAI_API_KEY="your_nvidia_api_key_here"
export MODEL_NAME="nvidia/nemotron-3-ultra-550b-a55b"

# Start the Volatility Harvester
python3 volatility_harvester.py
```

Watch the terminal as the agent loops through the watchlist, analyzes the news, and executes the options straddles autonomously!

## 🏆 Hackathon Requirements Met
* **Autonomous Agents**: VolHarvest operates entirely autonomously on a loop.
* **Alpaca CLI**: All account validation, option chain fetching, and order execution is handled dynamically via subprocess calls to the Alpaca CLI.
* **Options Trading**: Executes complex multi-leg options strategies (Straddles).
* **Partner Technology**: Integrated with OpenAI-compatible endpoints to seamlessly support Featherless AI and NVIDIA NIM open-source models.
