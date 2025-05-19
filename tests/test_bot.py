"""
Integration tests for the DOLF Trading Bot.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

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


async def test_full_pipeline():
    """Test the full signal generation pipeline."""
    print("Testing full signal generation pipeline...")
    
    # Initialize mock exchange
    exchange = MockBinanceExchange()
    
    # Initialize metrics
    metrics = [
        OpenInterestChange(exchange, window='24h'),
        FundingRate(exchange),
        VolumeSpike(exchange, lookback_periods=24),
        PriceRecovery(exchange, lookback_periods=12),
        CumulativeVolumeDelta(exchange, lookback_trades=1000),
        LiquidationSpike(exchange, timeframe='1h')
    ]
    
    # Test symbol
    symbol = 'BTC/USDT'
    
    # Calculate metrics
    results = []
    for metric in metrics:
        try:
            result = await metric.calculate(symbol)
            results.append(result)
            print(f"\n{result['name']} Result:")
            print(f"  Value: {result['value']}")
            print(f"  Status: {result['status']}")
            print(f"  Details: {json.dumps(result['details'], indent=2)}")
        except Exception as e:
            print(f"Error testing {metric.name}: {str(e)}")
    
    # Detect market condition
    market_detector = MarketConditionDetector()
    market_condition = market_detector.detect_condition(results)
    print(f"\nMarket condition: {market_condition}")
    
    # Generate signal
    thresholds = {
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
    
    signal_generator = SignalGenerator(thresholds)
    signal = signal_generator.generate_signal(symbol, results, market_condition)
    
    if signal:
        print("\nSignal generated:")
        print(f"  Direction: {signal['direction']}")
        print(f"  Confidence: {signal['confidence']:.1f}%")
        print(f"  Take Profit: ${signal['take_profit']:.2f}")
        print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
        print("\nExplanations:")
        for explanation in signal["explanations"]:
            print(f"  • {explanation}")
    else:
        print("\nNo signal generated.")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
