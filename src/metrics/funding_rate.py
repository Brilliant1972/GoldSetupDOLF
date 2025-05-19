"""
Funding Rate metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import statistics

from .base import BaseMetric, MetricStatus


class FundingRate(BaseMetric):
    """Funding Rate metric for DOLF strategy."""
    
    def __init__(self, exchange):
        """Initialize the Funding Rate metric.
        
        Args:
            exchange: Exchange API connector
        """
        super().__init__("Funding Rate")
        self.exchange = exchange
        self.logger = logging.getLogger("metrics.funding_rate")
        
    async def calculate(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Calculate the Funding Rate metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get funding rate data from exchange
            fr_data = await self.exchange.get_funding_rate(exchange_symbol)
            
            if "error" in fr_data:
                self.logger.error(f"Error getting funding rate data: {fr_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": fr_data["error"]})
                return self.get_result()
            
            # Get current funding rate
            current_fr = 0.0
            if "current" in fr_data and isinstance(fr_data["current"], dict):
                current_fr = float(fr_data["current"].get("lastFundingRate", 0)) * 100  # Convert to percentage
            
            # Calculate 8h average funding rate
            avg_fr = 0.0
            if "history" in fr_data and isinstance(fr_data["history"], list) and len(fr_data["history"]) > 0:
                # Take up to 8 most recent funding rates (Binance has 8h funding intervals)
                recent_rates = [float(rate.get("fundingRate", 0)) * 100 for rate in fr_data["history"][:8]]
                if recent_rates:
                    avg_fr = statistics.mean(recent_rates)
            
            details = {
                "current_rate": current_fr,
                "avg_rate_8h": avg_fr,
                "source": fr_data.get("source", "unknown"),
                "timestamp": fr_data.get("current", {}).get("time", 0)
            }
            
            # For DOLF strategy, we're interested in the current funding rate
            # but we also provide the 8h average for additional context
            self._set_result(current_fr, MetricStatus.LIVE, details)
            
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating funding rate: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
