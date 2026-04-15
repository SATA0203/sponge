"""
Base analyzer interface and utilities
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MetricResult:
    """Result of a single metric calculation"""
    name: str
    value: float
    threshold: Optional[float] = None
    status: str = "ok"  # ok, warning, critical
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzerResult:
    """Result from an analyzer run"""
    analyzer_name: str
    dimension: str
    score: float  # 0-100
    metrics: List[MetricResult] = field(default_factory=list)
    issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    execution_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "analyzer_name": self.analyzer_name,
            "dimension": self.dimension,
            "score": self.score,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "threshold": m.threshold,
                    "status": m.status,
                    "description": m.description,
                    "metadata": m.metadata
                }
                for m in self.metrics
            ],
            "issues": self.issues,
            "recommendations": self.recommendations,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat()
        }


class BaseAnalyzer(ABC):
    """Base class for all architecture analyzers"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
    
    @property
    @abstractmethod
    def dimension(self) -> str:
        """Return the dimension this analyzer measures"""
        pass
    
    @abstractmethod
    async def analyze(self, context: Dict[str, Any]) -> AnalyzerResult:
        """
        Perform analysis and return results
        
        Args:
            context: Analysis context containing code paths, metrics, etc.
            
        Returns:
            AnalyzerResult with scores, metrics, issues, and recommendations
        """
        pass
    
    def get_metric_status(self, value: float, warning_threshold: float, critical_threshold: float) -> str:
        """Determine metric status based on thresholds"""
        if value <= critical_threshold:
            return "critical"
        elif value <= warning_threshold:
            return "warning"
        return "ok"
    
    def calculate_score(self, metrics: List[MetricResult], weights: Optional[Dict[str, float]] = None) -> float:
        """
        Calculate overall score from metrics (0-100)
        
        Default implementation averages all metric values, 
        assuming they're already normalized to 0-100 scale.
        """
        if not metrics:
            return 100.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for metric in metrics:
            weight = weights.get(metric.name, 1.0) if weights else 1.0
            # Normalize value to 0-100 if needed
            normalized_value = min(100.0, max(0.0, metric.value))
            weighted_sum += normalized_value * weight
            total_weight += weight
        
        if total_weight == 0:
            return 100.0
            
        return weighted_sum / total_weight
