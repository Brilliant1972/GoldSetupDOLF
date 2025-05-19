"""
Cumulative Volume Delta (CVD) metric for DOLF strategy.
"""
from typing import Dict, Any, List, Optional
import logging
import asyncio

from .base import BaseMetric, MetricStatus


class CumulativeVolumeDelta(BaseMetric):
    """Cumulative Volume Delta (CVD) metric for DOLF strategy."""
    
    def __init__(self, exchange, lookback_trades: int = 1000):
        """Initialize the CVD metric.
        
        Args:
            exchange: Exchange API connector
            lookback_trades: Number of trades to look back for CVD calculation
        """
        super().__init__("Cumulative Volume Delta")
        self.exchange = exchange
        self.lookback_trades = lookback_trades
        self.logger = logging.getLogger("metrics.cvd")
        
    async def calculate(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Calculate the CVD metric.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            **kwargs: Additional parameters
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        try:
            # Convert symbol format if needed (BTC/USDT -> BTCUSDT for Binance)
            exchange_symbol = symbol.replace('/', '')
            
            # Get recent trades from exchange
            trades_data = await self.exchange.get_trades(
                exchange_symbol, 
                limit=self.lookback_trades
            )
            
            if "error" in trades_data:
                self.logger.error(f"Error getting trades data: {trades_data['error']}")
                self._set_result(0.0, MetricStatus.FAKE, {"error": trades_data["error"]})
                return self.get_result()
            
            # Calculate CVD
            if "trades" in trades_data and isinstance(trades_data["trades"], list) and trades_data["trades"]:
                trades = trades_data["trades"]
                
                # Sort trades by time (oldest first)
                trades.sort(key=lambda x: x.get("time", 0))
                
                # Calculate CVD
                cvd = 0.0
                buy_volume = 0.0
                sell_volume = 0.0
                
                for trade in trades:
                    price = float(trade.get("price", 0))
                    qty = float(trade.get("qty", 0))
                    is_buyer_maker = trade.get("isBuyerMaker", False)
                    
                    # In Binance, isBuyerMaker=True means the buyer was the maker,
                    # which implies the trade was a sell (taker was a seller)
                    if is_buyer_maker:
                        # Sell trade
                        cvd -= qty * price
                        sell_volume += qty * price
                    else:
                        # Buy trade
                        cvd += qty * price
                        buy_volume += qty * price
                
                # Normalize CVD as a percentage of total volume
                total_volume = buy_volume + sell_volume
                if total_volume > 0:
                    normalized_cvd = (cvd / total_volume) * 100
                else:
                    normalized_cvd = 0.0
                
                details = {
                    "cvd_raw": cvd,
                    "buy_volume": buy_volume,
                    "sell_volume": sell_volume,
                    "total_volume": total_volume,
                    "trade_count": len(trades),
                    "source": trades_data.get("source", "unknown"),
                    "timestamp": trades[-1].get("time", 0) if trades else 0
                }
                
                self._set_result(normalized_cvd, MetricStatus.LIVE, details)
            else:
                self.logger.warning("Not enough trades data, using fake value")
                self._set_result(0.0, MetricStatus.FAKE, {"error": "Not enough trades data"})
                
            return self.get_result()
            
        except Exception as e:
            self.logger.error(f"Error calculating CVD: {str(e)}")
            self._set_result(0.0, MetricStatus.FAKE, {"error": str(e)})
            return self.get_result()
