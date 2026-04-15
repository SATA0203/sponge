"""
Architecture Health API Endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from app.db.database import get_db
from app.arch_health.services import ArchitectureHealthService
from app.arch_health.models import (
    ArchitectureHealthSnapshot,
    ArchitectureIssue,
    ArchitectureRecommendation,
)


router = APIRouter(prefix="/api/v1/arch-health", tags=["architecture-health"])


class AnalysisRequest(BaseModel):
    """Request model for running analysis"""
    code_path: str = "."
    context: Optional[Dict[str, Any]] = None


class HealthSummary(BaseModel):
    """Summary of architecture health"""
    overall_score: float
    status: str
    total_issues: int
    critical_issues: int
    warning_issues: int
    analyzed_files: int
    analysis_duration_ms: int
    snapshot_date: str
    
    dimension_scores: Dict[str, float]
    top_issues: List[Dict[str, Any]]


@router.post("/analyze")
async def run_analysis(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Run architecture health analysis on specified code path
    
    This triggers a complete analysis of the codebase and returns results.
    Analysis runs asynchronously and may take some time for large codebases.
    """
    service = ArchitectureHealthService(db)
    
    try:
        snapshot = await service.run_analysis(
            code_path=request.code_path,
            context=request.context
        )
        
        return {
            "success": True,
            "message": "Analysis completed successfully",
            "snapshot_id": snapshot.id,
            "overall_score": snapshot.overall_score,
            "status": snapshot.status,
            "issues_found": snapshot.total_issues,
            "critical_issues": snapshot.critical_issues,
            "analysis_duration_ms": snapshot.analysis_duration_ms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/status")
def get_health_status(db: Session = Depends(get_db)):
    """Get current architecture health status (latest snapshot)"""
    service = ArchitectureHealthService(db)
    snapshot = service.get_latest_snapshot()
    
    if not snapshot:
        return {
            "status": "unknown",
            "message": "No analysis has been run yet. Use POST /analyze to run first analysis."
        }
    
    return {
        "overall_score": snapshot.overall_score,
        "status": snapshot.status,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "dimension_scores": {
            "coupling": snapshot.coupling_score,
            "quality": snapshot.quality_score,
            "dependencies": snapshot.dependencies_score,
            "maintainability": snapshot.maintainability_score,
            "runtime": snapshot.runtime_score,
        },
        "issues": {
            "total": snapshot.total_issues,
            "critical": snapshot.critical_issues,
            "warning": snapshot.warning_issues,
        },
        "metadata": {
            "analyzed_files": snapshot.analyzed_files,
            "analyzed_modules": snapshot.analyzed_modules,
            "analysis_duration_ms": snapshot.analysis_duration_ms,
        }
    }


@router.get("/summary", response_model=HealthSummary)
def get_health_summary(db: Session = Depends(get_db)):
    """Get detailed health summary with top issues"""
    service = ArchitectureHealthService(db)
    snapshot = service.get_latest_snapshot()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="No analysis found. Run analysis first.")
    
    return HealthSummary(
        overall_score=snapshot.overall_score,
        status=snapshot.status,
        total_issues=snapshot.total_issues,
        critical_issues=snapshot.critical_issues,
        warning_issues=snapshot.warning_issues,
        analyzed_files=snapshot.analyzed_files,
        analysis_duration_ms=snapshot.analysis_duration_ms,
        snapshot_date=snapshot.snapshot_date.isoformat(),
        dimension_scores={
            "coupling": snapshot.coupling_score,
            "quality": snapshot.quality_score,
            "dependencies": snapshot.dependencies_score,
            "maintainability": snapshot.maintainability_score,
            "runtime": snapshot.runtime_score,
        },
        top_issues=snapshot.top_issues or []
    )


@router.get("/trend")
def get_health_trend(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get health trend over specified number of days"""
    service = ArchitectureHealthService(db)
    snapshots = service.get_health_trend(days=days)
    
    return {
        "period_days": days,
        "data_points": len(snapshots),
        "trend": [
            {
                "date": s.snapshot_date.isoformat(),
                "score": s.overall_score,
                "status": s.status,
                "issues": s.total_issues,
            }
            for s in snapshots
        ]
    }


@router.get("/issues")
def get_issues(
    status: str = Query(default="open"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get architecture issues"""
    service = ArchitectureHealthService(db)
    
    if status == "open":
        issues = service.get_open_issues(limit=limit)
    else:
        # Query all issues with optional status filter
        from sqlalchemy import select
        query = select(ArchitectureIssue)
        if status and status != "all":
            query = query.where(ArchitectureIssue.status == status)
        query = query.order_by(ArchitectureIssue.impact_score.desc()).limit(limit)
        issues = db.execute(query).scalars().all()
    
    return {
        "count": len(issues),
        "issues": [
            {
                "id": i.id,
                "type": i.issue_type,
                "severity": i.severity,
                "title": i.title,
                "description": i.description,
                "location": i.location,
                "status": i.status,
                "impact_score": i.impact_score,
                "first_detected": i.first_detected.isoformat() if i.first_detected else None,
            }
            for i in issues
        ]
    }


@router.get("/recommendations")
def get_recommendations(
    status: str = Query(default="pending"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get architecture recommendations"""
    service = ArchitectureHealthService(db)
    
    if status == "pending":
        recommendations = service.get_pending_recommendations(limit=limit)
    else:
        from sqlalchemy import select
        query = select(ArchitectureRecommendation)
        if status and status != "all":
            query = query.where(ArchitectureRecommendation.status == status)
        query = query.order_by(ArchitectureRecommendation.priority.desc()).limit(limit)
        recommendations = db.execute(query).scalars().all()
    
    return {
        "count": len(recommendations),
        "recommendations": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "type": r.recommendation_type,
                "priority": r.priority,
                "estimated_effort": r.estimated_effort,
                "steps": r.steps,
                "status": r.status,
                "is_ai_generated": r.is_ai_generated,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recommendations
        ]
    }


@router.put("/recommendations/{rec_id}/status")
def update_recommendation_status(
    rec_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """Update recommendation status (pending, in_progress, implemented, rejected)"""
    rec = db.query(ArchitectureRecommendation).filter(
        ArchitectureRecommendation.id == rec_id
    ).first()
    
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    
    valid_statuses = ["pending", "in_progress", "implemented", "rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    rec.status = status
    if status == "implemented":
        from datetime import datetime
        rec.implemented_at = datetime.utcnow()
    
    db.commit()
    db.refresh(rec)
    
    return {
        "success": True,
        "message": f"Recommendation status updated to {status}",
        "recommendation_id": rec_id
    }


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db)
):
    """Delete a specific analysis snapshot"""
    snapshot = db.query(ArchitectureHealthSnapshot).filter(
        ArchitectureHealthSnapshot.id == snapshot_id
    ).first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    db.delete(snapshot)
    db.commit()
    
    return {"success": True, "message": "Snapshot deleted"}
