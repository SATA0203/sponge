"""
Celery tasks for architecture health monitoring

These tasks enable scheduled and asynchronous analysis.
"""

from celery import shared_task
from sqlalchemy.orm import Session
import asyncio

from app.db.database import SessionLocal
from app.arch_health.services import ArchitectureHealthService


@shared_task(bind=True, max_retries=3)
def run_architecture_analysis(self, code_path: str = ".", context: dict = None):
    """
    Celery task to run architecture health analysis asynchronously
    
    Args:
        code_path: Path to codebase to analyze
        context: Optional context dictionary for analyzers
    """
    db = SessionLocal()
    try:
        service = ArchitectureHealthService(db)
        
        # Run async analysis in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            snapshot = loop.run_until_complete(
                service.run_analysis(code_path=code_path, context=context)
            )
        finally:
            loop.close()
        
        return {
            "success": True,
            "snapshot_id": snapshot.id,
            "overall_score": snapshot.overall_score,
            "status": snapshot.status,
            "issues_found": snapshot.total_issues,
            "critical_issues": snapshot.critical_issues,
        }
        
    except Exception as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    finally:
        db.close()


@shared_task
def schedule_periodic_analysis():
    """
    Scheduled task to run periodic architecture analysis
    
    This should be configured in Celery beat schedule.
    """
    return run_architecture_analysis.delay(code_path=".", context=None)


@shared_task
def cleanup_old_snapshots(days_to_keep: int = 90):
    """
    Clean up old analysis snapshots to save database space
    
    Args:
        days_to_keep: Number of days to retain snapshots
    """
    from datetime import datetime, timedelta
    from app.arch_health.models import ArchitectureHealthSnapshot
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = db.query(ArchitectureHealthSnapshot).filter(
            ArchitectureHealthSnapshot.snapshot_date < cutoff_date
        ).delete(synchronize_session=False)
        
        db.commit()
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "message": f"Deleted {deleted_count} snapshots older than {days_to_keep} days"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        db.close()
