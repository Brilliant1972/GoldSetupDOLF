"""
Test script for DOLF metrics calculation.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exchanges.binance import BinanceExchange
from src.metrics.open_interest import OpenInterestChange
from src.metrics.funding_rate import FundingRate
from src.metrics.volume_spike import VolumeSpike
from src.metrics.price_recovery import PriceRecovery
from src.metrics.cvd import CumulativeVolumeDelta
from src.metrics.liquidation_spike import LiquidationSpike


async def test_metrics():
    """Test all DOLF metrics with sample data."""
    # Initialize exchange connector
    exchange = BinanceExchange()
    
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
    
    # Calculate and print results for each metric
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
    
    # Check if we have enough confirmed metrics for a signal
    confirmed_count = 0
    for result in results:
        # This is a placeholder for the confirmation logic
        # In a real implementation, we would check against thresholds
        if result['value'] != 0 and result['status'] == 'LIVE':
            confirmed_count += 1
    
    print(f"\nConfirmed metrics: {confirmed_count}/6")
    if confirmed_count >= 4:
        print("Signal would be generated!")
    else:
        print("No signal would be generated.")


if __name__ == "__main__":
    asyncio.run(test_metrics())
