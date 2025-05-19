"""
Telegram bot integration for the DOLF Trading Bot.
"""
import logging
import datetime
import os
import json
from typing import Dict, Any, List, Optional
import requests

from src.exchanges.base import BaseExchange
from src.metrics.base import BaseMetric


class TelegramBot:
    """Telegram bot for sending trading signals."""
    
    def __init__(self):
        """Initialize the Telegram bot.
        
        Credentials are loaded from environment variables:
        - TELEGRAM_BOT_TOKEN: Telegram bot token
        - TELEGRAM_CHAT_ID: Telegram chat ID to send messages to (can be comma-separated for multiple IDs)
        """
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id_str = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is missing. Please add it to your .env file.")
        if not chat_id_str:
            raise ValueError("TELEGRAM_CHAT_ID environment variable is missing. Please add it to your .env file.")
            
        self.chat_ids = [chat_id.strip() for chat_id in chat_id_str.split(',')]
            
        self.logger = logging.getLogger("telegram_bot")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.exchanges = {}
        self.metrics = []
        self.market_condition = "Medium"  # Default market condition
        self.confidence_threshold = 0.5  # Default confidence threshold
        self.start_time = datetime.datetime.utcnow()
        
    def initialize(self, exchanges: Dict[str, BaseExchange], metrics: List[BaseMetric], 
                  market_condition: str = "Medium", confidence_threshold: float = 0.5):
        """Initialize the Telegram bot.
        
        Args:
            exchanges: Dictionary of exchange connectors
            metrics: List of metric calculators
            market_condition: Current market condition
            confidence_threshold: Confidence threshold for signal generation
        """
        self.exchanges = exchanges
        self.metrics = metrics
        self.market_condition = market_condition
        self.confidence_threshold = confidence_threshold
        self.start_time = datetime.datetime.utcnow()
        
        self.logger.info("Telegram bot initialized")
        
        self.send_status_message()
        
    def send_status_message(self):
        """Send a status message to the chat."""
        try:
            exchange_status = self._check_exchanges_status()
            
            metrics_status = self._check_metrics_status()
            
            # Format the message
            message = "✅ GoldSetup Bot is running\n\n"
            
            message += "Connected Exchanges:\n"
            for exchange_name, status in exchange_status.items():
                message += f"- {exchange_name}: {status}\n"
            
            message += "\nDOLF Indicators:\n"
            for metric_name, status in metrics_status.items():
                message += f"- {metric_name}: {status}\n"
            
            message += f"\nMarket Type: {self.market_condition}  \n"
            message += f"Confidence Threshold: {self.confidence_threshold}  \n"
            
            start_time_str = self.start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
            message += f"Start Time: {start_time_str}\n"
            
            # Send the message
            self.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Error sending status message to Telegram: {str(e)}")
    
    def _check_exchanges_status(self) -> Dict[str, str]:
        """Check the status of all exchanges.
        
        Returns:
            Dictionary mapping exchange names to status (LIVE or FAKE)
        """
        exchange_status = {
            "Binance": "FAKE",
            "Bybit": "FAKE",
            "OKX": "FAKE",
            "KuCoin": "FAKE",
            "Bitget": "FAKE",
            "BingX": "FAKE",
            "HTX": "FAKE"
        }
        
        if self.exchanges:
            for name, exchange in self.exchanges.items():
                if name in exchange_status:
                    exchange_status[name] = "LIVE"
        
        return exchange_status
    
    def _check_metrics_status(self) -> Dict[str, str]:
        """Check the status of all metrics.
        
        Returns:
            Dictionary mapping metric names to status (LIVE or FAKE)
        """
        metrics_status = {
            "Open Interest Change": "FAKE",
            "Volume Spike": "FAKE",
            "Funding Rate": "FAKE",
            "Price Recovery": "FAKE",
            "CVD": "FAKE",
            "Liquidation Spike": "FAKE"
        }
        
        if self.metrics:
            for metric in self.metrics:
                name = metric.name
                if name == "Cumulative Volume Delta":
                    metrics_status["CVD"] = "LIVE"
                elif name in metrics_status:
                    metrics_status[name] = "LIVE"
        
        return metrics_status
        
    def send_message(self, text: str, parse_mode: str = "Markdown"):
        """Send a message to the chat.
        
        Args:
            text: Message text
            parse_mode: Parse mode for the message
        """
        success = False
        for chat_id in self.chat_ids:
            try:
                url = f"{self.base_url}/sendMessage"
                
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }
                
                response = requests.post(url, json=payload)
                
                if response.status_code == 200:
                    self.logger.info(f"Message sent to Telegram chat {chat_id}")
                    success = True
                else:
                    self.logger.error(f"Error sending message to Telegram chat {chat_id}: {response.text}")
                    
            except Exception as e:
                self.logger.error(f"Error sending message to Telegram chat {chat_id}: {str(e)}")
                
        return success
            
    def send_signal(self, signal: Dict[str, Any]):
        """Send a trading signal to Telegram.
        
        Args:
            signal: Trading signal information
        """
        # Format the signal message
        message = self._format_signal_message(signal)
        
        # Send the message
        self.send_message(message)
        
    def _format_signal_message(self, signal: Dict[str, Any]) -> str:
        """Format a trading signal as a Telegram message.
        
        Args:
            signal: Trading signal information
            
        Returns:
            Formatted message string
        """
        # Emoji based on direction
        emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
        
        # Format the message
        message = f"{emoji} *DOLF SIGNAL: {signal['direction']} {signal['symbol']}*\n\n"
        message += f"*Confidence:* {signal['confidence']}%\n"
        message += f"*Market Condition:* {signal['market_condition']}\n\n"
        
        message += "*Metrics:*\n"
        for explanation in signal["explanations"]:
            message += f"• {explanation}\n"
        
        message += f"\n*Current Price:* ${signal['current_price']}\n"
        message += f"*Take Profit:* ${signal['take_profit']}\n"
        message += f"*Stop Loss:* ${signal['stop_loss']}\n"
        
        return message
        
    def shutdown(self):
        """Shutdown the Telegram bot."""
        self.logger.info("Telegram bot stopped")
