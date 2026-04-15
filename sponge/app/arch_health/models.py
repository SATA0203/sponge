"""
Data models for architecture health monitoring
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.database import Base


class HealthStatusEnum(str, enum.Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


class DimensionEnum(str, enum.Enum):
    """Architecture health dimensions"""
    COUPLING = "coupling"
    QUALITY = "quality"
    DEPENDENCIES = "dependencies"
    MAINTAINABILITY = "maintainability"
    RUNTIME = "runtime"


class ArchitectureHealthSnapshot(Base):
    """Snapshot of overall architecture health at a point in time"""
    __tablename__ = "arch_health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Overall scores
    overall_score = Column(Float, nullable=False)  # 0-100
    coupling_score = Column(Float, default=0.0)
    quality_score = Column(Float, default=0.0)
    dependencies_score = Column(Float, default=0.0)
    maintainability_score = Column(Float, default=0.0)
    runtime_score = Column(Float, default=0.0)
    
    # Status
    status = Column(String(50), default="unknown")
    total_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    warning_issues = Column(Integer, default=0)
    
    # Metadata
    analyzed_files = Column(Integer, default=0)
    analyzed_modules = Column(Integer, default=0)
    analysis_duration_ms = Column(Integer, default=0)
    
    # Detailed data
    metrics_summary = Column(JSON, default=dict)
    top_issues = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dimension_scores = relationship("DimensionScore", back_populates="snapshot", cascade="all, delete-orphan")
    issues = relationship("ArchitectureIssue", back_populates="snapshot", cascade="all, delete-orphan")
    recommendations = relationship("ArchitectureRecommendation", back_populates="snapshot", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ArchitectureHealthSnapshot(id={self.id}, score={self.overall_score}, date={self.snapshot_date})>"


class DimensionScore(Base):
    """Detailed scores for each health dimension"""
    __tablename__ = "arch_dimension_scores"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("arch_health_snapshots.id"), nullable=False)
    
    dimension = Column(String(50), nullable=False)  # coupling, quality, etc.
    score = Column(Float, nullable=False)  # 0-100
    weight = Column(Float, default=0.2)  # Weight in overall calculation
    
    # Metric breakdown
    metrics = Column(JSON, default=dict)  # {metric_name: {value, threshold, status}}
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    snapshot = relationship("ArchitectureHealthSnapshot", back_populates="dimension_scores")

    def __repr__(self):
        return f"<DimensionScore(dimension={self.dimension}, score={self.score})>"


class ArchitectureIssue(Base):
    """Specific architecture issues detected"""
    __tablename__ = "arch_issues"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("arch_health_snapshots.id"), nullable=False)
    
    issue_type = Column(String(100), nullable=False)  # circular_dependency, god_class, etc.
    severity = Column(String(50), default="warning")  # info, warning, critical
    dimension = Column(String(50), nullable=False)
    
    # Issue details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(512), nullable=True)  # file path, module name
    affected_components = Column(JSON, default=list)
    
    # Metrics
    impact_score = Column(Float, default=0.0)  # 0-10
    effort_to_fix = Column(String(50), default="medium")  # low, medium, high
    
    # Tracking
    first_detected = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(50), default="open")  # open, acknowledged, resolved, ignored
    
    # Additional context
    evidence = Column(JSON, default=dict)  # Code snippets, dependency graphs, etc.
    issue_metadata = Column(JSON, default=dict)  # Renamed from metadata (reserved word)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    snapshot = relationship("ArchitectureHealthSnapshot", back_populates="issues")
    recommendations = relationship("ArchitectureRecommendation", back_populates="issue")

    def __repr__(self):
        return f"<ArchitectureIssue(type={self.issue_type}, severity={self.severity}, title='{self.title}')>"


class ArchitectureRecommendation(Base):
    """Recommendations for improving architecture"""
    __tablename__ = "arch_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("arch_health_snapshots.id"), nullable=True)
    issue_id = Column(Integer, ForeignKey("arch_issues.id"), nullable=True)
    
    # Recommendation content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    recommendation_type = Column(String(100), nullable=False)  # refactor, upgrade, optimize, etc.
    
    # Action details
    priority = Column(String(50), default="medium")  # low, medium, high, critical
    estimated_effort = Column(String(50), default="medium")  # hours/days
    expected_benefit = Column(String(255), nullable=True)
    
    # Implementation guidance
    steps = Column(JSON, default=list)  # Step-by-step instructions
    code_examples = Column(JSON, default=list)  # Before/after examples
    related_issues = Column(JSON, default=list)  # Issue IDs this addresses
    
    # Tracking
    status = Column(String(50), default="pending")  # pending, in_progress, implemented, rejected
    implemented_at = Column(DateTime, nullable=True)
    
    # AI-generated content flag
    is_ai_generated = Column(Boolean, default=False)
    ai_model = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    snapshot = relationship("ArchitectureHealthSnapshot", back_populates="recommendations")
    issue = relationship("ArchitectureIssue", back_populates="recommendations")

    def __repr__(self):
        return f"<ArchitectureRecommendation(title='{self.title}', priority={self.priority})>"


class AnalysisConfig(Base):
    """Configuration for architecture analysis"""
    __tablename__ = "arch_analysis_config"

    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(100), unique=True, nullable=False)
    
    # Weights for dimensions
    coupling_weight = Column(Float, default=0.25)
    quality_weight = Column(Float, default=0.20)
    dependencies_weight = Column(Float, default=0.15)
    maintainability_weight = Column(Float, default=0.20)
    runtime_weight = Column(Float, default=0.20)
    
    # Thresholds
    warning_threshold = Column(Float, default=70.0)  # Below this = warning
    critical_threshold = Column(Float, default=50.0)  # Below this = critical
    
    # Analysis settings
    enabled_analyzers = Column(JSON, default=list)
    excluded_paths = Column(JSON, default=list)  # Paths to exclude from analysis
    max_file_size_kb = Column(Integer, default=1024)  # Skip files larger than this
    
    # Scheduling
    auto_analysis_enabled = Column(Boolean, default=True)
    analysis_interval_hours = Column(Integer, default=24)
    
    # Notifications
    notify_on_critical = Column(Boolean, default=True)
    notification_channels = Column(JSON, default=list)  # email, slack, webhook
    
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AnalysisConfig(name={self.config_name}, active={self.active})>"
