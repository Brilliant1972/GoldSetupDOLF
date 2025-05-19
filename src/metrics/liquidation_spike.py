"""
Liquidation Spike metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import time

from .base import BaseMetric, MetricStatus


class LiquidationSpike(BaseMetric):
    """Liquidation Spike metric for DOLF strategy."""
    
    def __init__(self, exchange, timeframe: str = '1h'):
        """Initialize the Liquidation Spike metric.
        
        Args:
            exchange: Exchange API connector
            timeframe: Timeframe for liquidation data (e.g., '1h', '4h', '1d')
        """
        super().__init__("Liquidation Spike")
        self.exchange = exchange
        self.timeframe = timeframe
        self.logger = logging.getLogger("metrics.liquidation_spike")
        
    async def calculate(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Calculate the Liquidation Spike metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get liquidation data from exchange
            liq_data = await self.exchange.get_liquidations(exchange_symbol, self.timeframe)
            
            if "error" in liq_data:
                self.logger.error(f"Error getting liquidation data: {liq_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": liq_data["error"]})
                return self.get_result()
            
            # Calculate liquidation spike
            if "liquidations" in liq_data and isinstance(liq_data["liquidations"], list) and liq_data["liquidations"]:
                liquidations = liq_data["liquidations"]
                
                # Get current time in milliseconds
                current_time = int(time.time() * 1000)
                
                # Define time window based on timeframe
                time_windows = {
                    "1h": 60 * 60 * 1000,  # 1 hour in milliseconds
                    "4h": 4 * 60 * 60 * 1000,
                    "1d": 24 * 60 * 60 * 1000
                }
                time_window = time_windows.get(self.timeframe, 60 * 60 * 1000)  # Default to 1h
                
                # Filter liquidations within the time window
                recent_liquidations = [
                    liq for liq in liquidations 
                    if current_time - liq.get("time", 0) <= time_window
                ]
                
                # Separate long and short liquidations
                long_liquidations = [liq for liq in recent_liquidations if liq.get("side") == "BUY"]
                short_liquidations = [liq for liq in recent_liquidations if liq.get("side") == "SELL"]
                
                # Calculate total liquidation volume
                long_liq_volume = sum(float(liq.get("executedQty", 0)) * float(liq.get("averagePrice", 0)) for liq in long_liquidations)
                short_liq_volume = sum(float(liq.get("executedQty", 0)) * float(liq.get("averagePrice", 0)) for liq in short_liquidations)
                total_liq_volume = long_liq_volume + short_liq_volume
                
                # Calculate net liquidation (positive for more shorts liquidated, negative for more longs)
                net_liquidation = short_liq_volume - long_liq_volume
                
                # Normalize as a percentage of total liquidation volume
                if total_liq_volume > 0:
                    liquidation_spike = (net_liquidation / total_liq_volume) * 100
                else:
                    liquidation_spike = 0.0
                
                details = {
                    "long_liquidations": {
                        "count": len(long_liquidations),
                        "volume": long_liq_volume
                    },
                    "short_liquidations": {
                        "count": len(short_liquidations),
                        "volume": short_liq_volume
                    },
                    "total_liquidations": len(recent_liquidations),
                    "total_volume": total_liq_volume,
                    "timeframe": self.timeframe,
                    "source": liq_data.get("source", "unknown"),
                    "timestamp": current_time
                }
                
                self._set_result(liquidation_spike, MetricStatus.LIVE, details)
            else:
                self.logger.warning("No liquidation data available, using fake value")
                self._set_result(0.0, MetricStatus.FAKE, {"error": "No liquidation data"})
                
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidation spike: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
