"""
Open Interest Change metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio

from .base import BaseMetric, MetricStatus


class OpenInterestChange(BaseMetric):
    """Open Interest Change metric for DOLF strategy."""
    
    def __init__(self, exchange, window: str = '24h'):
        """Initialize the Open Interest Change metric.
        
        Args:
            exchange: Exchange API connector
            window: Time window for change calculation ('1h' or '24h')
        """
        super().__init__("Open Interest Change")
        self.exchange = exchange
        self.window = window
        self.logger = logging.getLogger("metrics.open_interest")
        
    async def calculate(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Calculate the Open Interest Change metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get open interest data from exchange
            oi_data = await self.exchange.get_open_interest(exchange_symbol, self.window)
            
            if "error" in oi_data:
                self.logger.error(f"Error getting open interest data: {oi_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": oi_data["error"]})
                return self.get_result()
            
            # Calculate open interest change
            if "history" in oi_data and isinstance(oi_data["history"], list) and len(oi_data["history"]) > 1:
                history = oi_data["history"]
                
                # Get current and previous open interest
                current_oi = float(history[0].get("sumOpenInterest", 0))
                
                # For 1h window, compare with 1 hour ago
                # For 24h window, compare with 24 hours ago or the oldest available data point
                prev_idx = 1 if self.window == '1h' else min(24, len(history) - 1)
                previous_oi = float(history[prev_idx].get("sumOpenInterest", 0))
                
                # Calculate percentage change
                if previous_oi > 0:
                    oi_change_pct = ((current_oi - previous_oi) / previous_oi) * 100
                else:
                    oi_change_pct = 0.0
                
                details = {
                    "current_oi": current_oi,
                    "previous_oi": previous_oi,
                    "window": self.window,
                    "source": oi_data.get("source", "unknown"),
                    "timestamp": history[0].get("timestamp", 0)
                }
                
                self._set_result(oi_change_pct, MetricStatus.LIVE, details)
            else:
                # If we don't have enough historical data, use fake data
                self.logger.warning("Not enough historical open interest data, using fake value")
                self._set_result(0.0, MetricStatus.FAKE, {"error": "Not enough historical data"})
                
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating open interest change: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
