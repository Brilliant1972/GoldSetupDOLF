# DOLF Trading Bot

A Telegram trading bot based on the DOLF formula for cryptocurrency trading.

## Features

- Analyzes real-time cryptocurrency data using the DOLF strategy
- Connects to 7 major exchanges: Binance, Bybit, OKX, KuCoin, Bitget, BingX, HTX
- Processes 6 key DOLF metrics:
  - Open Interest Change
  - Volume Spike
  - Funding Rate
  - Price Recovery
  - CVD (Cumulative Volume Delta)
  - Liquidation Spike
- Generates trading signals (Long or Short) when 4 out of 6 metrics are confirmed
- Identifies market conditions (Calm, Medium, Aggressive) and adjusts thresholds
- Sends signals via Telegram with detailed explanations

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/crypto_trading_bot.git
   cd crypto_trading_bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file based on `.env.example` and add your API keys:
   ```
   cp .env.example .env
   # Edit .env with your API keys and Telegram bot token
   ```

## Usage

### Running with Real Data

```
python src/main.py --symbols BTC/USDT,ETH/USDT --interval 3600
```

### Running with Mock Data (for testing)

```
python src/main.py --mock --symbols BTC/USDT --once
```

### Command Line Arguments

- `--mock`: Use mock data instead of real API data
- `--symbols`: Comma-separated list of symbols to analyze (default: BTC/USDT)
- `--interval`: Analysis interval in seconds (default: 3600)
- `--once`: Run once and exit (default: run continuously)

## Testing

Run the tests:

```
python tests/test_bot.py
```

## Project Structure

- `src/`: Source code
  - `exchanges/`: Exchange API connectors
  - `metrics/`: DOLF metrics implementation
  - `signals/`: Signal generation logic
  - `market/`: Market condition detection
  - `telegram/`: Telegram bot integration
  - `main.py`: Main bot script
- `tests/`: Test scripts
- `requirements.txt`: Python dependencies
- `.env.example`: Example environment variables

## License

MIT
