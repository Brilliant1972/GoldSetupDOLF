"""
CoinMarketCap API integration for DOLF Trading Bot.
"""
import os
import logging
import requests
import time
from typing import Dict, Any, List, Optional


class CoinMarketCapAPI:
    """CoinMarketCap API connector for fetching top cryptocurrencies."""
    
    def __init__(self):
        """Initialize the CoinMarketCap API connector."""
        self.api_key = os.getenv("COINMARKETCAP_API_KEY")
        self.use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
        self.logger = logging.getLogger("coinmarketcap")
        self.base_url = "https://pro-api.coinmarketcap.com/v1"
        
    def get_top_coins(self, limit: int = 60) -> Dict[str, Any]:
        """Get top cryptocurrencies by market cap.
        
        Args:
            limit: Number of coins to retrieve (default: 60)
            
        Returns:
            Dictionary containing the top coins data
        """
        if self.api_key and self.api_key != "your_coinmarketcap_api_key":
            try:
                self.logger.info(f"Fetching top {limit} coins from CoinMarketCap")
                url = f"{self.base_url}/cryptocurrency/listings/latest"
                
                headers = {
                    "X-CMC_PRO_API_KEY": self.api_key,
                    "Accept": "application/json"
                }
                
                params = {
                    "start": 1,
                    "limit": limit,
                    "convert": "USD",
                    "sort": "market_cap",
                    "sort_dir": "desc"
                }
                
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    coins = []
                    for coin in data.get("data", []):
                        symbol = coin.get("symbol")
                        if symbol:
                            coins.append({
                                "id": coin.get("id"),
                                "name": coin.get("name"),
                                "symbol": symbol,
                                "market_cap": coin.get("quote", {}).get("USD", {}).get("market_cap"),
                                "source": "CoinMarketCap",
                                "status": "LIVE"
                            })
                    
                    return {
                        "coins": coins,
                        "source": "CoinMarketCap",
                        "status": "LIVE"
                    }
                else:
                    self.logger.error(f"Error fetching data from CoinMarketCap: {response.text}")
            except Exception as e:
                self.logger.error(f"Error connecting to CoinMarketCap: {str(e)}")
        
        if self.use_mock:
            self.logger.info("Using mock data for CoinMarketCap")
            return self._get_mock_top_coins(limit)
        
        self.logger.warning("CoinMarketCap API key not found or failed, using CoinGecko as fallback")
        return self._get_coingecko_top_coins(limit)
            
    def _get_coingecko_top_coins(self, limit: int = 60) -> Dict[str, Any]:
        """Get top cryptocurrencies from CoinGecko as fallback.
        
        Args:
            limit: Number of coins to retrieve (default: 60)
            
        Returns:
            Dictionary containing the top coins data
        """
        try:
            self.logger.info(f"Fetching top {limit} coins from CoinGecko (fallback)")
            url = "https://api.coingecko.com/api/v3/coins/markets"
            
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                coins = []
                for coin in data:
                    symbol = coin.get("symbol", "").upper()
                    if symbol:
                        coins.append({
                            "id": coin.get("id"),
                            "name": coin.get("name"),
                            "symbol": symbol,
                            "market_cap": coin.get("market_cap"),
                            "source": "CoinGecko",
                            "status": "LIVE"
                        })
                
                return {
                    "coins": coins,
                    "source": "CoinGecko",
                    "status": "LIVE"
                }
            else:
                self.logger.error(f"Error fetching data from CoinGecko: {response.text}")
                return self._get_mock_top_coins(limit)
                
        except Exception as e:
            self.logger.error(f"Error connecting to CoinGecko: {str(e)}")
            return self._get_mock_top_coins(limit)
    
    def _get_mock_top_coins(self, limit: int = 60) -> Dict[str, Any]:
        """Get mock top cryptocurrencies.
        
        Args:
            limit: Number of coins to retrieve (default: 60)
            
        Returns:
            Dictionary containing mock top coins data
        """
        self.logger.info(f"Using mock data for top {limit} coins")
        
        mock_coins = [
            {"id": 1, "name": "Bitcoin", "symbol": "BTC", "market_cap": 1000000000000},
            {"id": 1027, "name": "Ethereum", "symbol": "ETH", "market_cap": 500000000000},
            {"id": 52, "name": "XRP", "symbol": "XRP", "market_cap": 100000000000},
            {"id": 1839, "name": "BNB", "symbol": "BNB", "market_cap": 80000000000},
            {"id": 3408, "name": "USD Coin", "symbol": "USDC", "market_cap": 50000000000},
            {"id": 825, "name": "Tether", "symbol": "USDT", "market_cap": 50000000000},
            {"id": 5426, "name": "Solana", "symbol": "SOL", "market_cap": 40000000000},
            {"id": 2, "name": "Litecoin", "symbol": "LTC", "market_cap": 30000000000},
            {"id": 74, "name": "Dogecoin", "symbol": "DOGE", "market_cap": 25000000000},
            {"id": 3890, "name": "Polygon", "symbol": "MATIC", "market_cap": 20000000000}
        ]
        
        for i in range(len(mock_coins), limit):
            mock_coins.append({
                "id": 10000 + i,
                "name": f"Coin{i}",
                "symbol": f"C{i}",
                "market_cap": 1000000000 - (i * 10000000),
                "source": "Mock",
                "status": "FAKE"
            })
        
        coins = []
        for coin in mock_coins[:limit]:
            coin["source"] = "Mock"
            coin["status"] = "FAKE"
            coins.append(coin)
        
        return {
            "coins": coins,
            "source": "Mock",
            "status": "FAKE"
        }
        
    def filter_supported_coins(self, coins: List[Dict[str, Any]], exchanges: List[str]) -> List[Dict[str, Any]]:
        """Filter coins to only include those supported by the specified exchanges.
        
        Args:
            coins: List of coins to filter
            exchanges: List of exchange names to check support for
            
        Returns:
            Filtered list of coins
        """
        self.logger.info(f"Filtering {len(coins)} coins for support on exchanges: {', '.join(exchanges)}")
        
        pairs_suffix = ["/USDT", "/USD", "/BUSD", "/USDC"]
        
        exchange_patterns = {
            "Binance": ["BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "MATIC", "DOT", "LTC", 
                        "LINK", "AVAX", "UNI", "ATOM", "ETC", "FIL", "NEAR", "ALGO", "APE", "AXS"],
            "Bybit": ["BTC", "ETH", "XRP", "SOL", "DOGE", "LTC", "LINK", "ADA", "MATIC", "AVAX", 
                      "DOT", "UNI", "ATOM", "ETC", "NEAR", "FIL", "APE", "AXS", "GALA", "SAND"],
            "OKX": ["BTC", "ETH", "XRP", "SOL", "DOGE", "LTC", "ADA", "LINK", "DOT", "AVAX", 
                    "MATIC", "UNI", "FIL", "ATOM", "ETC", "NEAR", "APE", "GALA", "SAND", "APT"],
            "KuCoin": ["BTC", "ETH", "XRP", "SOL", "ADA", "DOGE", "LTC", "DOT", "AVAX", "MATIC", 
                       "ATOM", "UNI", "LINK", "FIL", "TRX", "NEAR", "APE", "1INCH", "AAVE", "AGLD"],
            "Bitget": ["BTC", "ETH", "XRP", "SOL", "DOGE", "LTC", "ADA", "LINK", "DOT", "AVAX", 
                       "MATIC", "UNI", "TRX", "FIL", "ATOM", "ETC", "NEAR", "APE", "GALA", "CHZ"],
            "BingX": ["BTC", "ETH", "XRP", "SOL", "DOGE", "LTC", "ADA", "LINK", "DOT", "AVAX", 
                     "MATIC", "UNI", "FIL", "TRX", "ETC", "ATOM", "NEAR", "APE", "GALA", "INJ"],
            "HTX": ["BTC", "ETH", "XRP", "SOL", "ADA", "DOGE", "LTC", "DOT", "AVAX", "MATIC", 
                   "ATOM", "UNI", "LINK", "FIL", "TRX", "NEAR", "APT", "APE", "GALA", "AXS"]
        }
        
        filtered_coins = []
        skipped_coins = []
        
        for coin in coins:
            symbol = coin.get("symbol")
            is_supported = False
            supporting_exchanges = []
            
            for exchange in exchanges:
                if exchange in exchange_patterns:
                    if symbol in exchange_patterns[exchange] or symbol in ["BTC", "ETH"]:
                        is_supported = True
                        supporting_exchanges.append(exchange)
            
            if is_supported:
                coin["supporting_exchanges"] = supporting_exchanges
                coin["trading_pairs"] = [f"{symbol}{suffix}" for suffix in pairs_suffix if suffix != "/BUSD" or exchange != "Binance"]
                filtered_coins.append(coin)
                self.logger.info(f"Selected coin: {symbol} - Supported on {', '.join(supporting_exchanges)}")
            else:
                skipped_coins.append(coin)
                self.logger.info(f"Skipped coin: {symbol} - Not supported on any of the specified exchanges")
        
        self.logger.info(f"Filtered {len(filtered_coins)} supported coins from {len(coins)} total")
        self.logger.info(f"Skipped {len(skipped_coins)} unsupported coins")
        
        return filtered_coins
