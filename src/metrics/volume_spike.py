"""
Volume Spike metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio
import statistics

from .base import BaseMetric, MetricStatus


class VolumeSpike(BaseMetric):
    """Volume Spike metric for DOLF strategy."""
    
    def __init__(self, exchange, lookback_periods: int = 24):
        """Initialize the Volume Spike metric.
        
        Args:
            exchange: Exchange API connector
            lookback_periods: Number of periods to look back for average volume calculation
        """
        super().__init__("Volume Spike")
        self.exchange = exchange
        self.lookback_periods = lookback_periods
        self.logger = logging.getLogger("metrics.volume_spike")
        
    async def calculate(self, symbol: str, timeframe: str = '1h', **kwargs) -> Dict[str, Any]:
        """Calculate the Volume Spike metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for volume data (e.g., '1h', '4h', '1d')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get volume data from exchange
            volume_data = await self.exchange.get_volume(
                exchange_symbol, 
                timeframe=timeframe, 
                limit=self.lookback_periods + 1  # +1 for current period
            )
            
            if "error" in volume_data:
                self.logger.error(f"Error getting volume data: {volume_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": volume_data["error"]})
                return self.get_result()
            
            # Calculate volume spike
            if "volumes" in volume_data and isinstance(volume_data["volumes"], list) and len(volume_data["volumes"]) > 1:
                volumes = volume_data["volumes"]
                
                # Get current volume (most recent period)
                current_volume = float(volumes[0].get("volume", 0))
                
                # Calculate average volume over lookback periods (excluding current)
                historical_volumes = [float(v.get("volume", 0)) for v in volumes[1:]]
                if historical_volumes:
                    avg_volume = statistics.mean(historical_volumes)
                    
                    # Calculate volume spike as percentage above average
                    if avg_volume > 0:
                        volume_spike_pct = ((current_volume - avg_volume) / avg_volume) * 100
                    else:
                        volume_spike_pct = 0.0
                    
                    details = {
                        "current_volume": current_volume,
                        "avg_volume": avg_volume,
                        "lookback_periods": len(historical_volumes),
                        "timeframe": timeframe,
                        "source": volume_data.get("source", "unknown"),
                        "timestamp": volumes[0].get("timestamp", 0)
                    }
                    
                    self._set_result(volume_spike_pct, MetricStatus.LIVE, details)
                else:
                    self.logger.warning("Not enough historical volume data, using fake value")
                    self._set_result(0.0, MetricStatus.FAKE, {"error": "Not enough historical data"})
            else:
                self.logger.warning("Invalid volume data format, using fake value")
                self._set_result(0.0, MetricStatus.FAKE, {"error": "Invalid data format"})
                
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating volume spike: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
