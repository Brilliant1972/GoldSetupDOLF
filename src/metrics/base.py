"""
Base class for all DOLF metrics.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Tuple, Optional, List


class MetricStatus(str, Enum):
    """Status of the metric data source."""
    LIVE = "LIVE"
    FAKE = "FAKE"


class BaseMetric(ABC):
    """Base class for all DOLF metrics."""
    
    def __init__(self, name: str):
        """Initialize the metric.
        
        Args:
            name: Name of the metric
        """
        self.name = name
        self._value = None
        self._status = MetricStatus.FAKE
        self._details = {}
    
    @property
    def value(self) -> Optional[float]:
        """Get the current value of the metric."""
        return self._value
    
    @property
    def status(self) -> MetricStatus:
        """Get the status of the metric data source."""
        return self._status
    
    @property
    def details(self) -> Dict[str, Any]:
        """Get additional details about the metric."""
        return self._details
    
    def get_result(self) -> Dict[str, Any]:
        """Get the metric result in a standardized format.
        
        Returns:
            Dict containing metric name, value, status, and details
        """
        return {
            "name": self.name,
            "value": self.value,
            "status": self.status,
            "details": self.details
        }
    
    @abstractmethod
    async def calculate(self, symbol: str, **kwargs) -> Dict[str, Any]:
        """Calculate the metric value.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            **kwargs: Additional parameters for calculation
            
        Returns:
            Dict containing metric name, value, status, and details
        """
        pass
    
    def _set_result(self, value: float, status: MetricStatus, details: Dict[str, Any] = None):
        """Set the metric result.
        
        Args:
            value: Calculated metric value
            status: Status of the data source (LIVE or FAKE)
            details: Additional details about the calculation
        """
        self._value = value
        self._status = status
        self._details = details or {}
