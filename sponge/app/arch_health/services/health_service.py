"""
Architecture Health Service - Main orchestration service
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.arch_health.analyzers import (
    BaseAnalyzer,
    AnalyzerResult,
    CouplingAnalyzer,
    QualityAnalyzer,
    DependenciesAnalyzer,
)
from app.arch_health.models import (
    ArchitectureHealthSnapshot,
    DimensionScore,
    ArchitectureIssue,
    ArchitectureRecommendation,
    AnalysisConfig,
    HealthStatusEnum,
)


class ArchitectureHealthService:
    """Main service for architecture health monitoring and recommendations"""
    
    def __init__(self, db_session: Session, config: Optional[AnalysisConfig] = None):
        self.db = db_session
        self.config = config or self._get_default_config()
        self.analyzers: List[BaseAnalyzer] = []
        self._initialize_analyzers()
    
    def _get_default_config(self) -> AnalysisConfig:
        """Get default analysis configuration"""
        return AnalysisConfig(
            config_name="default",
            coupling_weight=0.25,
            quality_weight=0.20,
            dependencies_weight=0.15,
            maintainability_weight=0.20,
            runtime_weight=0.20,
            warning_threshold=70.0,
            critical_threshold=50.0,
            enabled_analyzers=["coupling", "quality", "dependencies"],
            excluded_paths=["__pycache__", ".git", "node_modules", "venv", ".venv"],
        )
    
    def _initialize_analyzers(self):
        """Initialize analyzers based on config"""
        self.analyzers = []
        
        enabled = self.config.enabled_analyzers or ["coupling", "quality", "dependencies"]
        
        if "coupling" in enabled:
            self.analyzers.append(CouplingAnalyzer())
        if "quality" in enabled:
            self.analyzers.append(QualityAnalyzer())
        if "dependencies" in enabled:
            self.analyzers.append(DependenciesAnalyzer())
    
    async def run_analysis(self, code_path: str, context: Optional[Dict[str, Any]] = None) -> ArchitectureHealthSnapshot:
        """
        Run complete architecture analysis
        
        Args:
            code_path: Path to codebase to analyze
            context: Additional context for analyzers
            
        Returns:
            ArchitectureHealthSnapshot with results
        """
        start_time = time.time()
        
        # Prepare analysis context
        analysis_context = {
            "code_path": code_path,
            "excluded_paths": self.config.excluded_paths or [],
            **(context or {})
        }
        
        # Run all analyzers
        analyzer_results: List[AnalyzerResult] = []
        for analyzer in self.analyzers:
            try:
                result = await analyzer.analyze(analysis_context)
                analyzer_results.append(result)
            except Exception as e:
                print(f"Analyzer {analyzer.name} failed: {e}")
        
        # Calculate dimension scores
        dimension_scores_map = {}
        for result in analyzer_results:
            dimension_scores_map[result.dimension] = {
                "score": result.score,
                "metrics": [m.__dict__ for m in result.metrics],
                "weight": self._get_dimension_weight(result.dimension)
            }
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_scores_map)
        
        # Determine status
        status = self._determine_status(overall_score)
        
        # Collect all issues and recommendations
        all_issues = []
        all_recommendations = []
        critical_count = 0
        warning_count = 0
        
        for result in analyzer_results:
            for issue in result.issues:
                all_issues.append(issue)
                if issue.get("severity") == "critical":
                    critical_count += 1
                elif issue.get("severity") == "warning":
                    warning_count += 1
            
            all_recommendations.extend(result.recommendations)
        
        # Create snapshot in database
        snapshot = ArchitectureHealthSnapshot(
            snapshot_date=datetime.utcnow(),
            overall_score=overall_score,
            coupling_score=dimension_scores_map.get("coupling", {}).get("score", 0),
            quality_score=dimension_scores_map.get("quality", {}).get("score", 0),
            dependencies_score=dimension_scores_map.get("dependencies", {}).get("score", 0),
            maintainability_score=dimension_scores_map.get("maintainability", {}).get("score", 0),
            runtime_score=dimension_scores_map.get("runtime", {}).get("score", 0),
            status=status,
            total_issues=len(all_issues),
            critical_issues=critical_count,
            warning_issues=warning_count,
            analyzed_files=context.get("file_count", 0),
            analyzed_modules=context.get("module_count", 0),
            analysis_duration_ms=int((time.time() - start_time) * 1000),
            metrics_summary={
                dim: data["metrics"] for dim, data in dimension_scores_map.items()
            },
            top_issues=all_issues[:10],  # Top 10 issues
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        # Save dimension scores
        for dim, data in dimension_scores_map.items():
            dim_score = DimensionScore(
                snapshot_id=snapshot.id,
                dimension=dim,
                score=data["score"],
                weight=data["weight"],
                metrics=data["metrics"]
            )
            self.db.add(dim_score)
        
        # Save issues
        for issue_data in all_issues:
            issue = ArchitectureIssue(
                snapshot_id=snapshot.id,
                issue_type=issue_data.get("type", "unknown"),
                severity=issue_data.get("severity", "info"),
                dimension=self._get_dimension_for_issue(issue_data.get("type", "")),
                title=issue_data.get("title", "Unknown issue"),
                description=issue_data.get("description", ""),
                location=issue_data.get("location", ""),
                affected_components=issue_data.get("affected_components", []),
                impact_score=issue_data.get("impact_score", 5.0),
                evidence=issue_data.get("evidence", {})
            )
            self.db.add(issue)
        
        # Save recommendations
        for rec_data in all_recommendations:
            recommendation = ArchitectureRecommendation(
                snapshot_id=snapshot.id,
                title=rec_data.get("title", "Unnamed recommendation"),
                description=rec_data.get("description", ""),
                recommendation_type=rec_data.get("type", "general"),
                priority=rec_data.get("priority", "medium"),
                steps=rec_data.get("steps", []),
                is_ai_generated=False
            )
            self.db.add(recommendation)
        
        self.db.commit()
        
        return snapshot
    
    def _get_dimension_weight(self, dimension: str) -> float:
        """Get weight for a dimension from config"""
        weights = {
            "coupling": self.config.coupling_weight,
            "quality": self.config.quality_weight,
            "dependencies": self.config.dependencies_weight,
            "maintainability": self.config.maintainability_weight,
            "runtime": self.config.runtime_weight,
        }
        return weights.get(dimension, 0.2)
    
    def _calculate_overall_score(self, dimension_scores: Dict[str, Dict]) -> float:
        """Calculate weighted overall score"""
        if not dimension_scores:
            return 100.0
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for dim, data in dimension_scores.items():
            weight = data.get("weight", 0.2)
            score = data.get("score", 100.0)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 100.0
        
        return weighted_sum / total_weight
    
    def _determine_status(self, score: float) -> str:
        """Determine health status based on score"""
        if score >= self.config.warning_threshold:
            return "healthy"
        elif score >= self.config.critical_threshold:
            return "warning"
        else:
            return "critical"
    
    def _get_dimension_for_issue(self, issue_type: str) -> str:
        """Map issue type to dimension"""
        mapping = {
            "circular_dependency": "coupling",
            "god_module": "coupling",
            "high_complexity": "quality",
            "low_test_coverage": "quality",
            "outdated_dependencies": "dependencies",
            "security_vulnerabilities": "dependencies",
            "dependency_bloat": "dependencies",
        }
        return mapping.get(issue_type, "quality")
    
    def get_latest_snapshot(self) -> Optional[ArchitectureHealthSnapshot]:
        """Get the most recent health snapshot"""
        return self.db.query(ArchitectureHealthSnapshot).order_by(
            ArchitectureHealthSnapshot.snapshot_date.desc()
        ).first()
    
    def get_health_trend(self, days: int = 30) -> List[ArchitectureHealthSnapshot]:
        """Get health trend over specified days"""
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(ArchitectureHealthSnapshot).filter(
            ArchitectureHealthSnapshot.snapshot_date >= cutoff_date
        ).order_by(ArchitectureHealthSnapshot.snapshot_date.asc()).all()
    
    def get_open_issues(self, limit: int = 50) -> List[ArchitectureIssue]:
        """Get open issues"""
        return self.db.query(ArchitectureIssue).filter(
            ArchitectureIssue.status == "open"
        ).order_by(
            ArchitectureIssue.severity.desc(),
            ArchitectureIssue.impact_score.desc()
        ).limit(limit).all()
    
    def get_pending_recommendations(self, limit: int = 50) -> List[ArchitectureRecommendation]:
        """Get pending recommendations"""
        return self.db.query(ArchitectureRecommendation).filter(
            ArchitectureRecommendation.status == "pending"
        ).order_by(
            ArchitectureRecommendation.priority.desc()
        ).limit(limit).all()
