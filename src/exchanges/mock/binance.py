"""
Mock Binance API connector for testing.
"""
import time
import random
from typing import Dict, Any, List, Optional

from ..base import BaseExchange


class MockBinanceExchange(BaseExchange):
    """Mock Binance exchange API connector for testing."""
    
    def __init__(self):
        """Initialize the mock Binance exchange connector."""
        super().__init__("MockBinance")
        
    async def create_session(self):
        """Create a mock session."""
        pass
    
    async def close_session(self):
        """Close the mock session."""
        pass
    
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get mock open interest data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock historical open interest data
        history = []
        base_oi = 1000000000  # Base open interest value
        
        for i in range(30):
            # Add some randomness to the open interest values
            variation = random.uniform(-0.05, 0.05)
            oi_value = base_oi * (1 + variation)
            
            history.append({
                "symbol": symbol,
                "sumOpenInterest": oi_value,
                "sumOpenInterestValue": oi_value * 30000,  # Assuming BTC price around 30000
                "timestamp": current_time - (i * 3600000)  # 1 hour intervals
            })
        
        return {
            "current": {
                "symbol": symbol,
                "openInterest": history[0]["sumOpenInterest"],
                "time": current_time
            },
            "history": history,
            "source": "mock_binance",
            "status": "FAKE"
        }
    
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get mock funding rate data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock funding rate data
        current_fr = random.uniform(-0.001, 0.001)  # Current funding rate
        
        # Generate mock historical funding rates
        history = []
        for i in range(100):
            history.append({
                "symbol": symbol,
                "fundingRate": random.uniform(-0.001, 0.001),
                "fundingTime": current_time - (i * 8 * 3600000)  # 8 hour intervals
            })
        
        return {
            "current": {
                "symbol": symbol,
                "markPrice": 30000 + random.uniform(-1000, 1000),
                "indexPrice": 30000 + random.uniform(-1000, 1000),
                "lastFundingRate": current_fr,
                "nextFundingTime": current_time + (8 * 3600000),
                "time": current_time
            },
            "history": history,
            "source": "mock_binance",
            "status": "FAKE"
        }
    
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get mock volume data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock volume data
        volumes = []
        base_volume = 1000  # Base volume in BTC
        
        for i in range(limit):
            # Add some randomness to the volume values
            variation = random.uniform(-0.3, 0.3)
            volume_value = base_volume * (1 + variation)
            
            volumes.append({
                "timestamp": current_time - (i * 3600000),  # 1 hour intervals
                "volume": volume_value
            })
        
        # Occasionally add a volume spike
        if random.random() < 0.2:
            spike_idx = random.randint(0, min(5, limit - 1))
            volumes[spike_idx]["volume"] = volumes[spike_idx]["volume"] * random.uniform(2, 4)
        
        return {
            "volumes": volumes,
            "source": "mock_binance",
            "status": "FAKE"
        }
    
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get mock kline/candlestick data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock kline data
        klines = []
        base_price = 30000  # Base price for BTC
        current_price = base_price
        
        for i in range(limit):
            # Add some randomness to the price movement
            price_change = current_price * random.uniform(-0.02, 0.02)
            open_price = current_price
            close_price = current_price + price_change
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            volume = 1000 * (1 + random.uniform(-0.3, 0.3))
            
            klines.append({
                "timestamp": current_time - (i * 3600000),  # 1 hour intervals
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "close_time": current_time - (i * 3600000) + 3599999,
                "quote_asset_volume": volume * ((open_price + close_price) / 2),
                "number_of_trades": int(volume * 10),
                "taker_buy_base_asset_volume": volume * random.uniform(0.4, 0.6),
                "taker_buy_quote_asset_volume": volume * random.uniform(0.4, 0.6) * ((open_price + close_price) / 2)
            })
            
            current_price = close_price
        
        return {
            "klines": klines,
            "source": "mock_binance",
            "status": "FAKE"
        }
    
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get mock liquidation data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock liquidation data
        liquidations = []
        
        # Number of liquidations to generate
        num_liquidations = random.randint(5, 20)
        
        for i in range(num_liquidations):
            # Randomly decide if it's a long or short liquidation
            side = "BUY" if random.random() < 0.5 else "SELL"
            
            # Generate random liquidation data
            price = 30000 + random.uniform(-1000, 1000)
            qty = random.uniform(0.1, 5)
            
            liquidations.append({
                "symbol": symbol.replace('/', ''),
                "price": price,
                "origQty": qty,
                "executedQty": qty,
                "averagePrice": price,
                "status": "FILLED",
                "side": side,
                "time": current_time - int(random.uniform(0, 3600000))  # Random time within the last hour
            })
        
        return {
            "liquidations": liquidations,
            "source": "mock_binance",
            "status": "FAKE"
        }
    
    async def get_trades(self, symbol: str, limit: int = 1000) -> Dict[str, Any]:
        """Get mock trade data."""
        current_time = int(time.time() * 1000)
        
        # Generate mock trade data
        trades = []
        
        for i in range(limit):
            # Randomly decide if it's a buy or sell
            is_buyer_maker = random.random() < 0.5
            
            # Generate random trade data
            price = 30000 + random.uniform(-1000, 1000)
            qty = random.uniform(0.01, 1)
            
            trades.append({
                "id": i,
                "price": price,
                "qty": qty,
                "quoteQty": price * qty,
                "time": current_time - int(random.uniform(0, 3600000)),  # Random time within the last hour
                "isBuyerMaker": is_buyer_maker
            })
        
        return {
            "trades": trades,
            "source": "mock_binance",
            "status": "FAKE"
        }
