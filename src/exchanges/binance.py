"""
Binance API connector for DOLF Trading Bot.
"""
import time
import hmac
import hashlib
import urllib.parse
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import json

from .base import BaseExchange


class BinanceExchange(BaseExchange):
    """Binance exchange API connector."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the Binance exchange connector."""
        super().__init__("Binance", api_key, api_secret)
        self.base_url = "https://api.binance.com"
        self.futures_url = "https://fapi.binance.com"
        
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      signed: bool = False, futures: bool = False) -> Dict[str, Any]:
        """Make an API request to Binance.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether the request needs to be signed
            futures: Whether to use the futures API
            
        Returns:
            API response as a dictionary
        """
        await self.create_session()
        
        url = f"{self.futures_url if futures else self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        
        if signed and self.api_key and self.api_secret:
            timestamp = int(time.time() * 1000)
            
            params = params or {}
            params["timestamp"] = timestamp
            
            query_string = urllib.parse.urlencode(params)
            
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            params["signature"] = signature
            
        try:
            if method == "GET":
                response = await self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status != 200:
                error_text = await response.text()
                self.logger.error(f"Binance API error: {error_text}")
                return {"error": error_text, "status_code": response.status}
                
            response_json = await response.json()
            
            if "code" in response_json and response_json["code"] != 0:
                error_msg = response_json.get("msg", "Unknown error")
                self.logger.error(f"Binance API error: {error_msg}")
                return {"error": error_msg}
                
            return response_json
            
        except Exception as e:
            self.logger.error(f"Error making request to Binance API: {str(e)}")
            return {"error": str(e)}
            
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Time window for data ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d')
            
        Returns:
            Dictionary containing open interest data
        """
        binance_symbol = symbol.replace('/', '')
        
        period_map = {
            '5m': '5m', '15m': '15m', '30m': '30m', '1h': '1h', 
            '2h': '2h', '4h': '4h', '6h': '6h', '12h': '12h', '1d': '1d'
        }
        period = period_map.get(timeframe, '1h')
        
        endpoint = "/fapi/v1/openInterest"
        params = {
            "symbol": binance_symbol
        }
        
        current_oi = await self._request("GET", endpoint, params, futures=True)
        
        if "error" in current_oi:
            return current_oi
            
        hist_endpoint = "/futures/data/openInterestHist"
        hist_params = {
            "symbol": binance_symbol,
            "period": period,
            "limit": 30
        }
        
        history = await self._request("GET", hist_endpoint, hist_params, futures=True)
        
        if "error" in history:
            return history
            
        return {
            "current": current_oi,
            "history": history,
            "source": "binance",
            "status": "LIVE"
        }
        
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dictionary containing funding rate data
        """
        binance_symbol = symbol.replace('/', '')
        
        endpoint = "/fapi/v1/premiumIndex"
        params = {
            "symbol": binance_symbol
        }
        
        current_fr = await self._request("GET", endpoint, params, futures=True)
        
        if "error" in current_fr:
            return current_fr
            
        hist_endpoint = "/fapi/v1/fundingRate"
        hist_params = {
            "symbol": binance_symbol,
            "limit": 100
        }
        
        history = await self._request("GET", hist_endpoint, hist_params, futures=True)
        
        if "error" in history:
            return history
            
        return {
            "current": current_fr,
            "history": history,
            "source": "binance",
            "status": "LIVE"
        }
        
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing volume data
        """
        klines = await self.get_klines(symbol, timeframe, limit)
        
        if "error" in klines:
            return klines
            
        volumes = []
        for kline in klines.get("klines", []):
            volumes.append({
                "timestamp": kline["timestamp"],
                "volume": kline["volume"]
            })
                
        return {
            "volumes": volumes,
            "source": "binance",
            "status": "LIVE"
        }
        
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing kline data
        """
        binance_symbol = symbol.replace('/', '')
        
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w', '1M': '1M'
        }
        interval = interval_map.get(timeframe, '1h')
        
        endpoint = "/fapi/v1/klines"
        params = {
            "symbol": binance_symbol,
            "interval": interval,
            "limit": limit
        }
        
        klines_data = await self._request("GET", endpoint, params, futures=True)
        
        if "error" in klines_data:
            return klines_data
            
        formatted_klines = []
        for kline in klines_data:
            if isinstance(kline, list) and len(kline) >= 11:
                formatted_klines.append({
                    "timestamp": int(kline[0]),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5]),
                    "close_time": int(kline[6]),
                    "quote_asset_volume": float(kline[7]),
                    "number_of_trades": int(kline[8]),
                    "taker_buy_base_asset_volume": float(kline[9]),
                    "taker_buy_quote_asset_volume": float(kline[10])
                })
                
        return {
            "klines": formatted_klines,
            "source": "binance",
            "status": "LIVE"
        }
        
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (not used directly in Binance API)
            
        Returns:
            Dictionary containing liquidation data
        """
        
        binance_symbol = symbol.replace('/', '')
        
        endpoint = "/fapi/v1/allForceOrders"
        params = {
            "symbol": binance_symbol,
            "limit": 100
        }
        
        liquidations = await self._request("GET", endpoint, params, futures=True)
        
        if "error" in liquidations:
            return liquidations
            
        return {
            "liquidations": liquidations,
            "source": "binance",
            "status": "LIVE"
        }
        
    async def get_trades(self, symbol: str, limit: int = 1000) -> Dict[str, Any]:
        """Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            limit: Number of trades to retrieve
            
        Returns:
            Dictionary containing trade data
        """
        binance_symbol = symbol.replace('/', '')
        
        endpoint = "/fapi/v1/trades"
        params = {
            "symbol": binance_symbol,
            "limit": min(limit, 1000)  # Binance limit is 1000
        }
        
        trades_data = await self._request("GET", endpoint, params, futures=True)
        
        if "error" in trades_data:
            return trades_data
            
        return {
            "trades": trades_data,
            "source": "binance",
            "status": "LIVE"
        }
