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
from src.telegram.bot import TelegramBot


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
        
        # Load environment variables
        load_dotenv()
        
        # Initialize exchange connectors
        self.exchange = MockBinanceExchange()
        self.logger.info("Using mock exchange data")
        
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
    parser.add_argument('--symbols', type=str, default='BTC/USDT', help='Comma-separated list of symbols to analyze')
    parser.add_argument('--interval', type=int, default=300, help='Analysis interval in seconds (default: 5 minutes)')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    # Initialize the bot
    bot = DOLFBot(use_mock=args.mock)
    
    # Parse symbols
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    if args.once:
        # Run once for each symbol
        for symbol in symbols:
            await bot.analyze_symbol(symbol)
    else:
        # Run in continuous mode
        await bot.run(symbols, args.interval)


if __name__ == "__main__":
    asyncio.run(main())
