"""
HTX API connector for DOLF Trading Bot.
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


class HTXExchange(BaseExchange):
    """HTX exchange API connector."""
    
    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the HTX exchange connector."""
        super().__init__("HTX", api_key, api_secret)
        self.base_url = "https://api.htx.com"
        
    async def _request(self, method: str, endpoint: str, params: Dict = None, 
                      signed: bool = False) -> Dict[str, Any]:
        """Make an API request to HTX.
        
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
            timestamp = str(int(time.time()))
            
            params = params or {}
            params["AccessKeyId"] = self.api_key
            params["SignatureMethod"] = "HmacSHA256"
            params["SignatureVersion"] = "2"
            params["Timestamp"] = timestamp
            
            sorted_params = sorted(params.items())
            query_string = urllib.parse.urlencode(sorted_params)
            
            payload = f"{method}\n{urllib.parse.urlparse(url).netloc}\n{endpoint}\n{query_string}"
            
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256
            ).hexdigest()
            
            params["Signature"] = signature
            
        try:
            if method == "GET":
                response = await self.session.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await self.session.post(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            if response.status != 200:
                error_text = await response.text()
                self.logger.error(f"HTX API error: {error_text}")
                return {"error": error_text, "status_code": response.status}
                
            response_json = await response.json()
            
            if response_json.get("status") == "error":
                error_msg = response_json.get("err-msg", "Unknown error")
                self.logger.error(f"HTX API error: {error_msg}")
                return {"error": error_msg}
                
            return response_json.get("data", {})
            
        except Exception as e:
            self.logger.error(f"Error making request to HTX API: {str(e)}")
            return {"error": str(e)}
            
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Time window for data ('60min', '4hour', '1day')
            
        Returns:
            Dictionary containing open interest data
        """
        htx_symbol = symbol.replace('/', '-').lower()
        
        period_map = {
            '1h': '60min', '4h': '4hour', '1d': '1day'
        }
        period = period_map.get(timeframe, '60min')
        
        endpoint = "/linear-swap-api/v1/swap_his_open_interest"
        params = {
            "contract_code": htx_symbol,
            "period": period,
            "amount_type": 1  # 1 for number of contracts
        }
        
        response = await self._request("GET", endpoint, params)
        
        if "error" in response:
            return response
            
        history = response.get("data", [])
        current = history[0] if history else {}
        
        return {
            "current": current,
            "history": history,
            "source": "htx",
            "status": "LIVE"
        }
        
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get funding rate data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Dictionary containing funding rate data
        """
        htx_symbol = symbol.replace('/', '-').lower()
        
        endpoint = "/linear-swap-api/v1/swap_funding_rate"
        params = {
            "contract_code": htx_symbol
        }
        
        current_fr = await self._request("GET", endpoint, params)
        
        if "error" in current_fr:
            return current_fr
            
        hist_endpoint = "/linear-swap-api/v1/swap_historical_funding_rate"
        hist_params = {
            "contract_code": htx_symbol,
            "page_size": 100
        }
        
        history = await self._request("GET", hist_endpoint, hist_params)
        
        if "error" in history:
            return history
            
        return {
            "current": current_fr,
            "history": history.get("data", []),
            "source": "htx",
            "status": "LIVE"
        }
        
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1min', '5min', '15min', '30min', '60min', '4hour', '1day', '1week')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing volume data
        """
        htx_symbol = symbol.replace('/', '-').lower()
        
        interval_map = {
            '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '60min', '4h': '4hour', '1d': '1day', '1w': '1week'
        }
        interval = interval_map.get(timeframe, '60min')
        
        endpoint = "/linear-swap-ex/market/history/kline"
        params = {
            "contract_code": htx_symbol,
            "period": interval,
            "size": limit
        }
        
        klines = await self._request("GET", endpoint, params)
        
        if "error" in klines:
            return klines
            
        volumes = []
        for kline in klines:
            if isinstance(kline, dict) and "id" in kline and "vol" in kline:
                volumes.append({
                    "timestamp": int(kline["id"]) * 1000,  # Convert to milliseconds
                    "volume": float(kline["vol"])
                })
                
        return {
            "volumes": volumes,
            "source": "htx",
            "status": "LIVE"
        }
        
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for klines ('1min', '5min', '15min', '30min', '60min', '4hour', '1day', '1week')
            limit: Number of data points to retrieve
            
        Returns:
            Dictionary containing kline data
        """
        htx_symbol = symbol.replace('/', '-').lower()
        
        interval_map = {
            '1m': '1min', '5m': '5min', '15m': '15min', '30m': '30min',
            '1h': '60min', '4h': '4hour', '1d': '1day', '1w': '1week'
        }
        interval = interval_map.get(timeframe, '60min')
        
        endpoint = "/linear-swap-ex/market/history/kline"
        params = {
            "contract_code": htx_symbol,
            "period": interval,
            "size": limit
        }
        
        klines_data = await self._request("GET", endpoint, params)
        
        if "error" in klines_data:
            return klines_data
            
        formatted_klines = []
        for kline in klines_data:
            if isinstance(kline, dict) and "id" in kline:
                formatted_klines.append({
                    "timestamp": int(kline["id"]) * 1000,  # Convert to milliseconds
                    "open": float(kline["open"]),
                    "high": float(kline["high"]),
                    "low": float(kline["low"]),
                    "close": float(kline["close"]),
                    "volume": float(kline["vol"])
                })
                
        return {
            "klines": formatted_klines,
            "source": "htx",
            "status": "LIVE"
        }
        
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for data (not used directly in HTX API)
            
        Returns:
            Dictionary containing liquidation data
        """
        htx_symbol = symbol.replace('/', '-').lower()
        
        endpoint = "/linear-swap-api/v1/swap_liquidation_orders"
        params = {
            "contract_code": htx_symbol,
            "trade_type": 0,  # 0 for all, 5 for buy, 6 for sell
            "create_date": 7,  # Last 7 days
            "page_size": 100
        }
        
        liquidations = await self._request("GET", endpoint, params)
        
        if "error" in liquidations:
            return liquidations
            
        return {
            "liquidations": liquidations.get("data", {}).get("orders", []),
            "source": "htx",
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
        htx_symbol = symbol.replace('/', '-').lower()
        
        endpoint = "/linear-swap-ex/market/trade"
        params = {
            "contract_code": htx_symbol,
            "size": min(limit, 2000)  # HTX limit is 2000
        }
        
        trades_data = await self._request("GET", endpoint, params)
        
        if "error" in trades_data:
            return trades_data
            
        return {
            "trades": trades_data.get("data", []),
            "source": "htx",
            "status": "LIVE"
        }
