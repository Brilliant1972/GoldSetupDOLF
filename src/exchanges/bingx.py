"""
BingX API connector for DOLF Trading Bot.
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


class BingXExchange(BaseExchange):
    """BingX exchange API connector."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the BingX exchange connector."""
        super().__init__("BingX", api_key, api_secret)
        self.base_url = "https://open-api.bingx.com"
        
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      signed: bool = False) -> Dict[str, Any]:
        """Make an API request to BingX.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Request parameters
            signed: Whether the request needs to be signed
            
        Returns:
            API response as a dictionary
        """
        await self.create_session()
        
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if signed and self.api_key and self.api_secret:
            timestamp = str(int(time.time() * 1000))
            
            params = params or {}
            params["timestamp"] = timestamp
            params["recvWindow"] = 5000  # Optional, but recommended
            
            query_string = urllib.parse.urlencode(params)
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            params["signature"] = signature
            headers["X-BX-APIKEY"] = self.api_key
            
        try:
            if method == "GET":
                response = await self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status != 200:
                error_text = await response.text()
                self.logger.error(f"BingX API error: {error_text}")
                return {"error": error_text, "status_code": response.status}
                
            response_json = await response.json()
            
            if response_json.get("code") != 0:
                error_msg = response_json.get("msg", "Unknown error")
                self.logger.error(f"BingX API error: {error_msg}")
                return {"error": error_msg}
                
            return response_json.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Error making request to BingX API: {str(e)}")
            return {"error": str(e)}
            
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Time window for data (not used directly in BingX API)
            
        Returns:
            Dictionary containing open interest data
        """
        bingx_symbol = symbol.replace('/', '')
        
        self.logger.warning("BingX doesn't provide public open interest data. Returning empty data.")
        return {
            "current": {},
            "history": [],
            "source": "bingx",
            "status": "FAKE"
        }
        
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dictionary containing funding rate data
        """
        bingx_symbol = symbol.replace('/', '')
        
        endpoint = "/openApi/swap/v2/quote/premiumIndex"
        params = {
            "symbol": bingx_symbol
        }
        
        current_fr = await self._request("GET", endpoint, params)
        
        if "error" in current_fr:
            return current_fr
            
        return {
            "current": current_fr,
            "history": [],
            "source": "bingx",
            "status": "LIVE"
        }
        
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing volume data
        """
        bingx_symbol = symbol.replace('/', '')
        
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '12h': '12h',
            '1d': '1d', '1w': '1w'
        }
        interval = interval_map.get(timeframe, '1h')
        
        endpoint = "/openApi/swap/v3/quote/klines"
        params = {
            "symbol": bingx_symbol,
            "interval": interval,
            "limit": limit
        }
        
        klines = await self._request("GET", endpoint, params)
        
        if "error" in klines:
            return klines
            
        volumes = []
        for kline in klines:
            if isinstance(kline, list) and len(kline) >= 6:
                volumes.append({
                    "timestamp": int(kline[0]),
                    "volume": float(kline[5])
                })
                
        return {
            "volumes": volumes,
            "source": "bingx",
            "status": "LIVE"
        }
        
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '1w')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing kline data
        """
        bingx_symbol = symbol.replace('/', '')
        
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '12h': '12h',
            '1d': '1d', '1w': '1w'
        }
        interval = interval_map.get(timeframe, '1h')
        
        endpoint = "/openApi/swap/v3/quote/klines"
        params = {
            "symbol": bingx_symbol,
            "interval": interval,
            "limit": limit
        }
        
        klines_data = await self._request("GET", endpoint, params)
        
        if "error" in klines_data:
            return klines_data
            
        formatted_klines = []
        for kline in klines_data:
            if isinstance(kline, list) and len(kline) >= 6:
                formatted_klines.append({
                    "timestamp": int(kline[0]),
                    "open": float(kline[1]),
                    "high": float(kline[2]),
                    "low": float(kline[3]),
                    "close": float(kline[4]),
                    "volume": float(kline[5])
                })
                
        return {
            "klines": formatted_klines,
            "source": "bingx",
            "status": "LIVE"
        }
        
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (not used directly in BingX API)
            
        Returns:
            Dictionary containing liquidation data
        """
        self.logger.warning("BingX doesn't provide public liquidation data. Returning empty data.")
        return {
            "liquidations": [],
            "source": "bingx",
            "status": "FAKE"
        }
        
    async def get_trades(self, symbol: str, limit: int = 1000) -> Dict[str, Any]:
        """Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            limit: Number of trades to retrieve
            
        Returns:
            Dictionary containing trade data
        """
        bingx_symbol = symbol.replace('/', '')
        
        endpoint = "/openApi/swap/v3/quote/trades"
        params = {
            "symbol": bingx_symbol,
            "limit": min(limit, 1000)  # BingX limit is 1000
        }
        
        trades_data = await self._request("GET", endpoint, params)
        
        if "error" in trades_data:
            return trades_data
            
        return {
            "trades": trades_data,
            "source": "bingx",
            "status": "LIVE"
        }
