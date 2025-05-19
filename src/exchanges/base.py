"""
Base class for exchange API connectors.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import time


class BaseExchange(ABC):
    """Base class for all exchange API connectors."""
    
    def __init__(self, name: str, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize the exchange connector.
        
        Args:
            name: Name of the exchange
            api_key: API key for authenticated requests
            api_secret: API secret for authenticated requests
        """
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = None
        self.logger = logging.getLogger(f"exchange.{name.lower()}")
    
    async def create_session(self):
        """Create an HTTP session for API requests."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    @abstractmethod
    async def get_open_interest(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get open interest data for a symbol."""
        pass
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate for a symbol."""
        pass
    
    @abstractmethod
    async def get_volume(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get volume data for a symbol."""
        pass
    
    @abstractmethod
    async def get_klines(self, symbol: str, timeframe: str = '1h', limit: int = 24) -> Dict[str, Any]:
        """Get kline/candlestick data for a symbol."""
        pass
    
    @abstractmethod
    async def get_liquidations(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Get liquidation data for a symbol."""
        pass
    
    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 1000) -> Dict[str, Any]:
        """Get recent trades for a symbol."""
        pass
