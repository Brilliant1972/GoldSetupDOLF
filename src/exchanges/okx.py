"""
OKX API connector for DOLF Trading Bot.
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


class OKXExchange(BaseExchange):
    """OKX exchange API connector."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None):
        """Initialize the OKX exchange connector."""
        super().__init__("OKX", api_key, api_secret)
        self.base_url = "https://www.okx.com"
        self.passphrase = passphrase
        
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      signed: bool = False) -> Dict[str, Any]:
        """Make an API request to OKX.
        
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
            timestamp = str(int(time.time()))
            
            if method == "GET" and params:
                query_string = urllib.parse.urlencode(params)
                endpoint = f"{endpoint}?{query_string}"
                params = None
                
            message = timestamp + method + endpoint
            if params:
                message += json.dumps(params)
                
            signature = base64.b64encode(
                hmac.new(
                    self.api_secret.encode("utf-8"),
                    message.encode("utf-8"),
                    hashlib.sha256
                ).digest()
            ).decode("utf-8")
            
            headers.update({
                "OK-ACCESS-KEY": self.api_key,
                "OK-ACCESS-SIGN": signature,
                "OK-ACCESS-TIMESTAMP": timestamp,
                "OK-ACCESS-PASSPHRASE": self.passphrase
            })
            
        try:
            if method == "GET":
                response = await self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status != 200:
                error_text = await response.text()
                self.logger.error(f"OKX API error: {error_text}")
                return {"error": error_text, "status_code": response.status}
                
            response_json = await response.json()
            
            if response_json.get("code") != "0":
                error_msg = response_json.get("msg", "Unknown error")
                self.logger.error(f"OKX API error: {error_msg}")
                return {"error": error_msg}
                
            return response_json.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Error making request to OKX API: {str(e)}")
            return {"error": str(e)}
            
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Time window for data ('5m', '1H', '4H', '12H', '1D', '1W')
            
        Returns:
            Dictionary containing open interest data
        """
        okx_symbol = symbol.replace('/', '-')
        
        period_map = {
            '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '4h': '4H', '12h': '12H',
            '1d': '1D', '1w': '1W'
        }
        period = period_map.get(timeframe, '1H')
        
        endpoint = "/api/v5/rubik/stat/contracts/open-interest-volume"
        params = {
            "ccy": okx_symbol.split('-')[0],  # Extract the coin part (e.g., BTC from BTC-USDT)
            "period": period
        }
        
        response = await self._request("GET", endpoint, params)
        
        if "error" in response:
            return response
            
        history = response
        
        return {
            "history": history,
            "source": "okx",
            "status": "LIVE"
        }
        
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Dictionary containing funding rate data
        """
        okx_symbol = symbol.replace('/', '-') + "-SWAP"
        
        endpoint = "/api/v5/public/funding-rate"
        params = {
            "instId": okx_symbol
        }
        
        current_fr = await self._request("GET", endpoint, params)
        
        if "error" in current_fr:
            return current_fr
            
        hist_endpoint = "/api/v5/public/funding-rate-history"
        hist_params = {
            "instId": okx_symbol,
            "limit": 100
        }
        
        history = await self._request("GET", hist_endpoint, hist_params)
        
        if "error" in history:
            return history
            
        return {
            "current": current_fr[0] if current_fr else {},
            "history": history,
            "source": "okx",
            "status": "LIVE"
        }
        
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1H', '2H', '4H', '6H', '12H', '1D', '1W')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing volume data
        """
        okx_symbol = symbol.replace('/', '-') + "-SWAP"
        
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '2h': '2H', '4h': '4H', '6h': '6H', '12h': '12H',
            '1d': '1D', '1w': '1W'
        }
        interval = interval_map.get(timeframe, '1H')
        
        endpoint = "/api/v5/market/candles"
        params = {
            "instId": okx_symbol,
            "bar": interval,
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
            "source": "okx",
            "status": "LIVE"
        }
        
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for klines ('1m', '3m', '5m', '15m', '30m', '1H', '2H', '4H', '6H', '12H', '1D', '1W')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing kline data
        """
        okx_symbol = symbol.replace('/', '-') + "-SWAP"
        
        interval_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1H', '2h': '2H', '4h': '4H', '6h': '6H', '12h': '12H',
            '1d': '1D', '1w': '1W'
        }
        interval = interval_map.get(timeframe, '1H')
        
        endpoint = "/api/v5/market/candles"
        params = {
            "instId": okx_symbol,
            "bar": interval,
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
            "source": "okx",
            "status": "LIVE"
        }
        
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe for data (not used directly in OKX API)
            
        Returns:
            Dictionary containing liquidation data
        """
        endpoint = "/api/v5/public/liquidation-orders"
        params = {
            "instType": "SWAP",
            "ccy": symbol.split('/')[0],  # Extract the coin part (e.g., BTC from BTC/USDT)
            "limit": 100
        }
        
        liquidations = await self._request("GET", endpoint, params)
        
        if "error" in liquidations:
            return liquidations
            
        return {
            "liquidations": liquidations,
            "source": "okx",
            "status": "LIVE"
        }
        
    async def get_trades(self, symbol: str, limit: int = 1000) -> Dict[str, Any]:
        """Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            limit: Number of trades to retrieve
            
        Returns:
            Dictionary containing trade data
        """
        okx_symbol = symbol.replace('/', '-') + "-SWAP"
        
        endpoint = "/api/v5/market/trades"
        params = {
            "instId": okx_symbol,
            "limit": min(limit, 500)  # OKX limit is 500
        }
        
        trades_data = await self._request("GET", endpoint, params)
        
        if "error" in trades_data:
            return trades_data
            
        return {
            "trades": trades_data,
            "source": "okx",
            "status": "LIVE"
        }
