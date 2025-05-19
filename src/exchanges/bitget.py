"""
Bitget API connector for DOLF Trading Bot.
"""
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import json

from .base import BaseExchange


class BitgetExchange(BaseExchange):
    """Bitget exchange API connector."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None):
        """Initialize the Bitget exchange connector."""
        super().__init__("Bitget", api_key, api_secret)
        self.base_url = "https://api.bitget.com"
        self.passphrase = passphrase
        
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      signed: bool = False) -> Dict[str, Any]:
        """Make an API request to Bitget.
        
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
        
        if signed and self.api_key and self.api_secret and self.passphrase:
            timestamp = str(int(time.time() * 1000))
            
            if method == "GET":
                str_to_sign = timestamp + method + endpoint
                if params:
                    query_string = urllib.parse.urlencode(params)
                    url = f"{url}?{query_string}"
            else:  # POST
                str_to_sign = timestamp + method + endpoint + (json.dumps(params) if params else "")
                
            signature = base64.b64encode(
                hmac.new(
                    self.api_secret.encode("utf-8"),
                    str_to_sign.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode("utf-8")
            
            headers.update({
                "ACCESS-KEY": self.api_key,
                "ACCESS-SIGN": signature,
                "ACCESS-TIMESTAMP": timestamp,
                "ACCESS-PASSPHRASE": self.passphrase
            })
            
        try:
            if method == "GET":
                response = await self.session.get(url, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status != 200:
                error_text = await response.text()
                self.logger.error(f"Bitget API error: {error_text}")
                return {"error": error_text, "status_code": response.status}
                
            response_json = await response.json()
            
            if response_json.get("code") != "00000":
                error_msg = response_json.get("msg", "Unknown error")
                self.logger.error(f"Bitget API error: {error_msg}")
                return {"error": error_msg}
                
            return response_json.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Error making request to Bitget API: {str(e)}")
            return {"error": str(e)}
            
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Time window for data (not used directly in Bitget API)
            
        Returns:
            Dictionary containing open interest data
        """
        coin = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        bitget_symbol = f"{coin}{quote}_UMCBL"
        
        endpoint = "/api/mix/v1/market/open-interest"
        params = {
            "symbol": bitget_symbol
        }
        
        current_oi = await self._request("GET", endpoint, params)
        
        if "error" in current_oi:
            return current_oi
            
        return {
            "current": current_oi,
            "history": [],
            "source": "bitget",
            "status": "LIVE"
        }
        
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dictionary containing funding rate data
        """
        coin = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        bitget_symbol = f"{coin}{quote}_UMCBL"
        
        endpoint = "/api/mix/v1/market/current-fundRate"
        params = {
            "symbol": bitget_symbol
        }
        
        current_fr = await self._request("GET", endpoint, params)
        
        if "error" in current_fr:
            return current_fr
            
        hist_endpoint = "/api/mix/v1/market/history-fundRate"
        hist_params = {
            "symbol": bitget_symbol,
            "pageSize": 100
        }
        
        history = await self._request("GET", hist_endpoint, hist_params)
        
        if "error" in history:
            return history
            
        return {
            "current": current_fr,
            "history": history,
            "source": "bitget",
            "status": "LIVE"
        }
        
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing volume data
        """
        coin = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        bitget_symbol = f"{coin}{quote}_UMCBL"
        
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W'
        }
        interval = interval_map.get(timeframe, '1H')
        
        endpoint = "/api/mix/v1/market/candles"
        params = {
            "symbol": bitget_symbol,
            "granularity": interval,
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
            "source": "bitget",
            "status": "LIVE"
        }
        
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing kline data
        """
        coin = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        bitget_symbol = f"{coin}{quote}_UMCBL"
        
        interval_map = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '4h': '4H', '1d': '1D', '1w': '1W'
        }
        interval = interval_map.get(timeframe, '1H')
        
        endpoint = "/api/mix/v1/market/candles"
        params = {
            "symbol": bitget_symbol,
            "granularity": interval,
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
            "source": "bitget",
            "status": "LIVE"
        }
        
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (not used directly in Bitget API)
            
        Returns:
            Dictionary containing liquidation data
        """
        self.logger.warning("Bitget doesn't provide public liquidation data. Returning empty data.")
        return {
            "liquidations": [],
            "source": "bitget",
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
        coin = symbol.split('/')[0]
        quote = symbol.split('/')[1]
        bitget_symbol = f"{coin}{quote}_UMCBL"
        
        endpoint = "/api/mix/v1/market/fills"
        params = {
            "symbol": bitget_symbol,
            "limit": min(limit, 100)  # Bitget limit is 100
        }
        
        trades_data = await self._request("GET", endpoint, params)
        
        if "error" in trades_data:
            return trades_data
            
        return {
            "trades": trades_data,
            "source": "bitget",
            "status": "LIVE"
        }
