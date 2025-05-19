"""
Signal generator for the DOLF Trading Bot.
"""
import logging
from typing import Dict, Any, List, Optional
import time

from src.metrics.base import MetricStatus


class SignalGenerator:
    """Signal generator for the DOLF Trading Bot."""
    
    def __init__(self, thresholds: Dict[str, Dict[str, float]]):
        """Initialize the signal generator.
        
        Args:
            thresholds: Thresholds for each metric in different market conditions
        """
        self.thresholds = thresholds
        self.logger = logging.getLogger("signal_generator")
        self.last_signal_time = {}  # Track last signal time for each symbol
        
    def generate_signal(self, symbol: str, metrics_results: List[Dict[str, Any]], 
                       market_condition: str) -> Optional[Dict[str, Any]]:
        """Generate a trading signal based on metrics results.
        
        Args:
            symbol: Trading pair symbol
            metrics_results: List of metric results
            market_condition: Current market condition
            
        Returns:
            Trading signal or None if no signal is generated
        """
        # Get thresholds for the current market condition
        condition_thresholds = self.thresholds.get(market_condition, self.thresholds.get("Medium"))
        
        # Check which metrics are confirmed
        confirmed_metrics = []
        for result in metrics_results:
            # Skip metrics with fake data
            if result["status"] != MetricStatus.LIVE:
                continue
                
            metric_name = result["name"]
            threshold = condition_thresholds.get(metric_name, 0)
            
            # Different metrics have different confirmation logic
            is_confirmed = False
            if metric_name == "Open Interest Change":
                is_confirmed = abs(result["value"]) >= threshold
            elif metric_name == "Funding Rate":
                is_confirmed = abs(result["value"]) >= threshold
            elif metric_name == "Volume Spike":
                is_confirmed = result["value"] >= threshold
            elif metric_name == "Price Recovery":
                is_confirmed = result["value"] >= threshold
            elif metric_name == "Cumulative Volume Delta":
                is_confirmed = abs(result["value"]) >= threshold
            elif metric_name == "Liquidation Spike":
                is_confirmed = abs(result["value"]) >= threshold
            
            if is_confirmed:
                confirmed_metrics.append(result)
                self.logger.info(f"{result['name']} is confirmed")
        
        # Generate signal if 4 or more metrics are confirmed
        if len(confirmed_metrics) >= 4:
            # Check if we've already sent a signal for this symbol recently
            current_time = int(time.time())
            last_signal = self.last_signal_time.get(symbol, 0)
            
            # Prevent repeating signals (wait at least 4 hours between signals for the same symbol)
            if current_time - last_signal < 4 * 60 * 60:
                self.logger.info(f"Signal for {symbol} suppressed (last signal was {(current_time - last_signal) // 60} minutes ago)")
                return None
                
            signal = self._create_signal(symbol, confirmed_metrics, metrics_results, market_condition)
            
            if signal["confidence"] < 50:
                self.logger.info(f"Signal for {symbol} suppressed (confidence {signal['confidence']}% < 50%)")
                return None
            
            # Update last signal time
            self.last_signal_time[symbol] = current_time
            
            self.logger.info(f"Signal generated: {signal['direction']} {symbol} with confidence {signal['confidence']}")
            return signal
        else:
            self.logger.info(f"No signal generated. Only {len(confirmed_metrics)}/6 metrics confirmed.")
            return None
            
    def _create_signal(self, symbol: str, confirmed_metrics: List[Dict[str, Any]], 
                      all_metrics: List[Dict[str, Any]], market_condition: str) -> Dict[str, Any]:
        """Create a trading signal based on confirmed metrics.
        
        Args:
            symbol: Trading pair symbol
            confirmed_metrics: List of confirmed metric results
            all_metrics: List of all metric results
            market_condition: Current market condition
            
        Returns:
            Trading signal
        """
        # Determine signal direction
        
        has_open_interest_up = False
        has_volume_spike_up = False
        has_price_recovery = False
        has_price_breakdown = False
        has_positive_funding = False
        has_negative_funding = False
        has_positive_cvd = False
        has_negative_cvd = False
        
        for metric in all_metrics:
            if metric["name"] == "Open Interest Change" and metric["value"] > 0:
                has_open_interest_up = True
            elif metric["name"] == "Volume Spike" and metric["value"] > 0:
                has_volume_spike_up = True
            elif metric["name"] == "Price Recovery":
                if metric["value"] > 0:
                    has_price_recovery = True
                else:
                    has_price_breakdown = True
            elif metric["name"] == "Funding Rate":
                if metric["value"] > 0:
                    has_positive_funding = True
                elif metric["value"] < 0:
                    has_negative_funding = True
            elif metric["name"] == "Cumulative Volume Delta":
                if metric["value"] > 0:
                    has_positive_cvd = True
                else:
                    has_negative_cvd = True
        
        # DOLF direction determination logic
        if has_open_interest_up and has_volume_spike_up and has_price_recovery and has_positive_funding:
            direction = "LONG"
        elif has_open_interest_up and has_volume_spike_up and has_price_breakdown and has_negative_funding:
            direction = "SHORT"
        else:
            positive_count = sum([1 for m in confirmed_metrics if (
                (m["name"] == "Open Interest Change" and m["value"] > 0) or
                (m["name"] == "Funding Rate" and m["value"] < 0) or  # Negative funding is bullish
                (m["name"] == "Price Recovery" and m["value"] > 0) or
                (m["name"] == "Cumulative Volume Delta" and m["value"] > 0) or
                (m["name"] == "Liquidation Spike" and m["value"] > 0)  # More shorts liquidated than longs
            )])
            
            negative_count = len(confirmed_metrics) - positive_count
            
            direction = "LONG" if positive_count > negative_count else "SHORT"
        
        # Calculate confidence score (0-100)
        confidence = (max(positive_count, negative_count) / len(confirmed_metrics)) * 100
        
        # Generate explanation for each metric
        explanations = []
        for metric in all_metrics:
            status = "✅" if metric in confirmed_metrics else "❌"
            
            if metric["name"] == "Open Interest Change":
                direction_text = "up" if metric["value"] > 0 else "down"
                explanations.append(f"OI {direction_text} ({metric['value']:.2f}%) {status}")
            elif metric["name"] == "Funding Rate":
                direction_text = "positive" if metric["value"] > 0 else "negative"
                explanations.append(f"FR {direction_text} ({metric['value']:.4f}%) {status}")
            elif metric["name"] == "Volume Spike":
                explanations.append(f"Volume spike ({metric['value']:.2f}%) {status}")
            elif metric["name"] == "Price Recovery":
                explanations.append(f"Price recovery ({metric['value']:.2f}%) {status}")
            elif metric["name"] == "Cumulative Volume Delta":
                direction_text = "positive" if metric["value"] > 0 else "negative"
                explanations.append(f"CVD {direction_text} ({metric['value']:.2f}%) {status}")
            elif metric["name"] == "Liquidation Spike":
                liquidation_type = "shorts" if metric["value"] > 0 else "longs"
                explanations.append(f"Liquidation of {liquidation_type} ({abs(metric['value']):.2f}%) {status}")
        
        # Calculate TP and SL based on volatility
        price_metrics = [m for m in all_metrics if m["name"] == "Price Recovery"]
        volatility = 0
        current_price = 0
        
        if price_metrics and "details" in price_metrics[0]:
            details = price_metrics[0]["details"]
            if "highest_high_after_low" in details and "lowest_low" in details:
                volatility = float(details["highest_high_after_low"]) - float(details["lowest_low"])
            if "current_price" in details:
                current_price = float(details["current_price"])
        
        # Default values if we couldn't get from metrics
        if current_price <= 0:
            current_price = 30000  # Default for testing
        
        if volatility <= 0:
            volatility = current_price * 0.01  # Default 1% volatility
        
        if direction == "LONG":
            take_profit = current_price * (1 + (volatility / current_price) * 2)
            stop_loss = current_price * (1 - (volatility / current_price))
        else:
            take_profit = current_price * (1 - (volatility / current_price) * 2)
            stop_loss = current_price * (1 + (volatility / current_price))
        
        return {
            "symbol": symbol,
            "direction": direction,
            "confidence": confidence,
            "explanations": explanations,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "current_price": current_price,
            "market_condition": market_condition,
            "timestamp": int(time.time())
        }
