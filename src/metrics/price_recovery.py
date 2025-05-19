"""
Price Recovery metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio

from .base import BaseMetric, MetricStatus


class PriceRecovery(BaseMetric):
    """Price Recovery metric for DOLF strategy."""
    
    def __init__(self, exchange, lookback_periods: int = 12):
        """Initialize the Price Recovery metric.
        
        Args:
            exchange: Exchange API connector
            lookback_periods: Number of periods to look back for price drop detection
        """
        super().__init__("Price Recovery")
        self.exchange = exchange
        self.lookback_periods = lookback_periods
        self.logger = logging.getLogger("metrics.price_recovery")
        
    async def calculate(self, symbol: str, timeframe: str = '15m', **kwargs) -> Dict[str, Any]:
        """Calculate the Price Recovery metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for price data (e.g., '15m', '1h', '4h')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get kline data from exchange
            kline_data = await self.exchange.get_klines(
                exchange_symbol, 
                timeframe=timeframe, 
                limit=self.lookback_periods
            )
            
            if "error" in kline_data:
                self.logger.error(f"Error getting kline data: {kline_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": kline_data["error"]})
                return self.get_result()
            
            # Calculate price recovery
            if "klines" in kline_data and isinstance(kline_data["klines"], list) and len(kline_data["klines"]) > 2:
                klines = kline_data["klines"]
                
                # Sort klines by timestamp (newest first)
                klines.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                
                # Get current price
                current_price = float(klines[0].get("close", 0))
                
                # Find the lowest low in the lookback period
                lowest_low = min(float(k.get("low", float('inf'))) for k in klines)
                
                # Find the highest high after the lowest low
                lowest_low_idx = next(
                    (i for i, k in enumerate(klines) if float(k.get("low", 0)) == lowest_low),
                    None
                )
                
                if lowest_low_idx is not None:
                    # Get klines after the lowest low
                    klines_after_low = klines[:lowest_low_idx]
                    
                    if klines_after_low:
                        highest_high_after_low = max(float(k.get("high", 0)) for k in klines_after_low)
                        
                        # Calculate recovery percentage
                        if lowest_low > 0:
                            recovery_pct = ((highest_high_after_low - lowest_low) / lowest_low) * 100
                        else:
                            recovery_pct = 0.0
                        
                        details = {
                            "current_price": current_price,
                            "lowest_low": lowest_low,
                            "highest_high_after_low": highest_high_after_low,
                            "lookback_periods": self.lookback_periods,
                            "timeframe": timeframe,
                            "source": kline_data.get("source", "unknown"),
                            "timestamp": klines[0].get("timestamp", 0)
                        }
                        
                        self._set_result(recovery_pct, MetricStatus.LIVE, details)
                        return self.get_result()
                
                # If we couldn't find a proper recovery pattern, return a default value
                self.logger.warning("No clear price recovery pattern found, using default value")
                self._set_result(0.0, MetricStatus.LIVE, {
                    "current_price": current_price,
                    "lowest_low": lowest_low,
                    "timeframe": timeframe,
                    "source": kline_data.get("source", "unknown"),
                    "timestamp": klines[0].get("timestamp", 0)
                })
            else:
                self.logger.warning("Not enough kline data, using fake value")
                self._set_result(0.0, MetricStatus.FAKE, {"error": "Not enough kline data"})
                
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating price recovery: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
