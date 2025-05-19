"""
Market condition detector for the DOLF Trading Bot.
"""
import logging
from typing import Dict, Any, List, Optional
import statistics


class MarketConditionDetector:
    """Market condition detector for the DOLF Trading Bot."""
    
    def __init__(self):
        """Initialize the market condition detector."""
        self.logger = logging.getLogger("market_condition")
        
    def detect_condition(self, metrics_results: List[Dict[str, Any]]) -> str:
        """Detect the current market condition based on metrics results.
        
        Args:
            metrics_results: List of metric results
            
        Returns:
            Market condition string ("Calm", "Medium", or "Aggressive")
        """
        # Extract volatility indicators from metrics
        volatility_indicators = []
        
        for result in metrics_results:
            if result["name"] == "Volume Spike":
                volatility_indicators.append(result["value"])
            elif result["name"] == "Price Recovery":
                volatility_indicators.append(result["value"])
            elif result["name"] == "Liquidation Spike":
                volatility_indicators.append(abs(result["value"]))
        
        # Calculate average volatility
        if volatility_indicators:
            avg_volatility = statistics.mean(volatility_indicators)
            
            # Determine market condition based on average volatility
            if avg_volatility < 50:
                condition = "Calm"
            elif avg_volatility < 150:
                condition = "Medium"
            else:
                condition = "Aggressive"
                
            self.logger.info(f"Market condition detected: {condition} (volatility: {avg_volatility:.2f})")
            return condition
        else:
            # Default to Medium if no volatility indicators are available
            self.logger.warning("No volatility indicators available, defaulting to Medium condition")
            return "Medium"
