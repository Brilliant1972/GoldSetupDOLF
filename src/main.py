"""
Main script for the DOLF Trading Bot.
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exchanges.mock.binance import MockBinanceExchange
from src.metrics.open_interest import OpenInterestChange
from src.metrics.funding_rate import FundingRate
from src.metrics.volume_spike import VolumeSpike
from src.metrics.price_recovery import PriceRecovery
from src.metrics.cvd import CumulativeVolumeDelta
from src.metrics.liquidation_spike import LiquidationSpike
from src.signals.generator import SignalGenerator
from src.market.condition import MarketConditionDetector
from src.market.coinmarketcap import CoinMarketCapAPI
from src.telegram.bot import TelegramBot

# Import exchange connectors
from src.exchanges.binance import BinanceExchange
from src.exchanges.bybit import BybitExchange
from src.exchanges.okx import OKXExchange
from src.exchanges.kucoin import KuCoinExchange
from src.exchanges.bitget import BitgetExchange
from src.exchanges.bingx import BingXExchange
from src.exchanges.htx import HTXExchange


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dolf_bot.log')
    ]
)

logger = logging.getLogger("dolf_bot")


class DOLFBot:
    """DOLF Trading Bot main class."""
    
    def __init__(self, use_mock: bool = False):
        """Initialize the DOLF Trading Bot."""
        self.logger = logger
        self.use_mock = use_mock
        
        if os.getenv("USE_MOCK_DATA", "false").lower() == "true":
            self.use_mock = True
            self.logger.info("USE_MOCK_DATA is set to true in .env, using mock data")
        
        # Load environment variables
        load_dotenv()
        
        # Initialize exchange connectors
        self.exchanges = {}
        if self.use_mock:
            self.exchanges["Binance"] = MockBinanceExchange()
            self.logger.info("Using mock exchange data")
        else:
            # Initialize exchanges with API keys from .env
            binance_key = os.getenv("BINANCE_API_KEY")
            binance_secret = os.getenv("BINANCE_API_SECRET")
            if binance_key and binance_secret and binance_key != "your_binance_api_key":
                self.exchanges["Binance"] = BinanceExchange(binance_key, binance_secret)
                self.logger.info("Initialized Binance exchange with real API keys")
            else:
                self.exchanges["Binance"] = MockBinanceExchange()
                self.logger.info("Using mock Binance exchange (missing API keys)")
                
            # Initialize Bybit exchange
            bybit_key = os.getenv("BYBIT_API_KEY")
            bybit_secret = os.getenv("BYBIT_API_SECRET")
            if bybit_key and bybit_secret and bybit_key != "your_bybit_api_key":
                self.exchanges["Bybit"] = BybitExchange(bybit_key, bybit_secret)
                self.logger.info("Initialized Bybit exchange with real API keys")
                
            # Initialize OKX exchange
            okx_key = os.getenv("OKX_API_KEY")
            okx_secret = os.getenv("OKX_API_SECRET")
            okx_passphrase = os.getenv("OKX_PASSPHRASE")
            if okx_key and okx_secret and okx_passphrase and okx_key != "your_okx_api_key":
                self.exchanges["OKX"] = OKXExchange(okx_key, okx_secret, okx_passphrase)
                self.logger.info("Initialized OKX exchange with real API keys")
                
            # Initialize KuCoin exchange
            kucoin_key = os.getenv("KUCOIN_API_KEY")
            kucoin_secret = os.getenv("KUCOIN_API_SECRET")
            kucoin_passphrase = os.getenv("KUCOIN_PASSPHRASE")
            if kucoin_key and kucoin_secret and kucoin_passphrase and kucoin_key != "your_kucoin_api_key":
                self.exchanges["KuCoin"] = KuCoinExchange(kucoin_key, kucoin_secret, kucoin_passphrase)
                self.logger.info("Initialized KuCoin exchange with real API keys")
                
            # Initialize Bitget exchange
            bitget_key = os.getenv("BITGET_API_KEY")
            bitget_secret = os.getenv("BITGET_API_SECRET")
            bitget_passphrase = os.getenv("BITGET_PASSPHRASE")
            if bitget_key and bitget_secret and bitget_passphrase and bitget_key != "your_bitget_api_key":
                self.exchanges["Bitget"] = BitgetExchange(bitget_key, bitget_secret, bitget_passphrase)
                self.logger.info("Initialized Bitget exchange with real API keys")
                
            # Initialize BingX exchange
            bingx_key = os.getenv("BINGX_API_KEY")
            bingx_secret = os.getenv("BINGX_API_SECRET")
            if bingx_key and bingx_secret and bingx_key != "your_bingx_api_key":
                self.exchanges["BingX"] = BingXExchange(bingx_key, bingx_secret)
                self.logger.info("Initialized BingX exchange with real API keys")
                
            # Initialize HTX exchange
            htx_key = os.getenv("HTX_API_KEY")
            htx_secret = os.getenv("HTX_API_SECRET")
            if htx_key and htx_secret and htx_key != "your_htx_api_key":
                self.exchanges["HTX"] = HTXExchange(htx_key, htx_secret)
                self.logger.info("Initialized HTX exchange with real API keys")
        
        if self.exchanges:
            self.exchange = next(iter(self.exchanges.values()))
        else:
            self.exchange = MockBinanceExchange()
            self.logger.warning("No exchanges initialized, using mock exchange")
        
        # Initialize metrics
        self.metrics = [
            OpenInterestChange(self.exchange, window='24h'),
            FundingRate(self.exchange),
            VolumeSpike(self.exchange, lookback_periods=24),
            PriceRecovery(self.exchange, lookback_periods=12),
            CumulativeVolumeDelta(self.exchange, lookback_trades=1000),
            LiquidationSpike(self.exchange, timeframe='1h')
        ]
        
        # Initialize other components
        self.market_detector = MarketConditionDetector()
        
        # Default thresholds for each market condition
        self.thresholds = {
            "Calm": {
                "Open Interest Change": 5.0,
                "Funding Rate": 0.01,
                "Volume Spike": 50.0,
                "Price Recovery": 2.0,
                "Cumulative Volume Delta": 10.0,
                "Liquidation Spike": 30.0
            },
            "Medium": {
                "Open Interest Change": 10.0,
                "Funding Rate": 0.02,
                "Volume Spike": 100.0,
                "Price Recovery": 3.0,
                "Cumulative Volume Delta": 20.0,
                "Liquidation Spike": 50.0
            },
            "Aggressive": {
                "Open Interest Change": 15.0,
                "Funding Rate": 0.03,
                "Volume Spike": 150.0,
                "Price Recovery": 5.0,
                "Cumulative Volume Delta": 30.0,
                "Liquidation Spike": 70.0
            }
        }
        
        self.signal_generator = SignalGenerator(self.thresholds)
        
        # Initialize Telegram bot
        try:
            self.telegram_bot = TelegramBot()
            self.logger.info("Telegram bot initialized")
            # Initialize the Telegram bot with exchanges and metrics
            self.telegram_bot.initialize(
                exchanges=self.exchanges,
                metrics=self.metrics,
                market_condition="Medium",
                confidence_threshold=0.5
            )
        except ValueError as e:
            self.telegram_bot = None
            self.logger.warning(f"Telegram bot not initialized: {str(e)}")
    
    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze a trading pair using DOLF metrics."""
        self.logger.info(f"Analyzing symbol: {symbol}")
        
        # Calculate all metrics
        results = []
        for metric in self.metrics:
            try:
                result = await metric.calculate(symbol)
                results.append(result)
                self.logger.info(f"{result['name']} = {result['value']} [{result['status']}]")
            except Exception as e:
                self.logger.error(f"Error calculating {metric.name}: {str(e)}")
        
        # Determine market condition
        market_condition = self.market_detector.detect_condition(results)
        self.logger.info(f"Market condition: {market_condition}")
        
        # Generate signal
        signal = self.signal_generator.generate_signal(symbol, results, market_condition)
        
        # Send signal to Telegram if generated and Telegram bot is available
        if signal and self.telegram_bot is not None:
            try:
                await self.telegram_bot.send_signal(signal)
            except Exception as e:
                self.logger.error(f"Error sending signal to Telegram: {str(e)}")
            
        return {
            "symbol": symbol,
            "market_condition": market_condition,
            "metrics": results,
            "signal": signal
        }
    
    async def get_top_coins(self, limit: int = 60) -> List[Dict[str, Any]]:
        """Get top cryptocurrencies and filter for supported futures markets.
        
        Args:
            limit: Number of coins to retrieve (default: 60)
            
        Returns:
            List of supported coin symbols in trading pair format (e.g., 'BTC/USDT')
        """
        self.logger.info(f"Fetching top {limit} coins from CoinMarketCap/CoinGecko")
        
        # Initialize CoinMarketCap API
        cmc = CoinMarketCapAPI()
        
        top_coins_data = cmc.get_top_coins(limit)
        coins = top_coins_data.get("coins", [])
        source = top_coins_data.get("source", "Unknown")
        
        self.logger.info(f"Retrieved {len(coins)} coins from {source}")
        
        filtered_coins = cmc.filter_supported_coins(coins, list(self.exchanges.keys()))
        
        return filtered_coins
        
    async def run(self, symbols: List[str], interval: int = 300):
        """Run the bot in continuous mode.
        
        Args:
            symbols: List of trading pair symbols to analyze
            interval: Analysis interval in seconds (default: 5 minutes)
        """
        self.logger.info(f"Starting DOLF Trading Bot in continuous mode")
        
        while True:
            for symbol in symbols:
                try:
                    await self.analyze_symbol(symbol)
                except Exception as e:
                    self.logger.error(f"Error analyzing {symbol}: {str(e)}")
                
                # Sleep a bit between symbols to avoid rate limiting
                await asyncio.sleep(5)
            
            self.logger.info(f"Sleeping for {interval} seconds before next analysis")
            await asyncio.sleep(interval)


async def main():
    """Main function to run the DOLF Trading Bot."""
    import argparse
    parser = argparse.ArgumentParser(description='DOLF Trading Bot')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real API data')
    parser.add_argument('--symbols', type=str, default='', help='Comma-separated list of symbols to analyze (optional)')
    parser.add_argument('--interval', type=int, default=300, help='Analysis interval in seconds (default: 5 minutes)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--limit', type=int, default=60, help='Number of top coins to analyze (default: 60)')
    args = parser.parse_args()
    
    # Initialize the bot
    bot = DOLFBot(use_mock=args.mock)
    
    # Get symbols to analyze
    symbols = []
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(',')]
        logger.info(f"Using command-line provided symbols: {', '.join(symbols)}")
    else:
        top_coins = await bot.get_top_coins(limit=args.limit)
        
        for coin in top_coins:
            symbol = coin.get("symbol")
            symbol_pairs = [f"{symbol}/USDT", f"{symbol}/USD", f"{symbol}/USDC"]
            symbols.extend(symbol_pairs[:1])  # Just add the first pair for each coin to avoid overloading
        
        logger.info(f"Using top {len(symbols)} coins from market data")
    
    if args.once:
        # Run once for each symbol
        for symbol in symbols:
            try:
                await bot.analyze_symbol(symbol)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {str(e)}")
    else:
        # Initialize Telegram bot with exchanges and metrics
        if bot.telegram_bot is not None:
            try:
                bot.telegram_bot.initialize(
                    exchanges=bot.exchanges,
                    metrics=bot.metrics,
                    market_condition="Medium",
                    confidence_threshold=0.5
                )
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {str(e)}")
                
        # Run in continuous mode
        await bot.run(symbols, args.interval)


if __name__ == "__main__":
    asyncio.run(main())
