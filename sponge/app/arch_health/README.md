# Architecture Health Monitoring System

## Overview

This module provides comprehensive architecture health monitoring and recommendation capabilities for the Sponge code agent system. It continuously analyzes your codebase to identify architectural issues and provides actionable recommendations for improvement.

## Features

### Five Key Dimensions

1. **Coupling Analysis** (25% weight)
   - Module dependency tracking
   - Circular dependency detection
   - God module identification
   - Layer violation detection

2. **Code Quality** (20% weight)
   - Cyclomatic complexity analysis
   - Maintainability index
   - Test coverage estimation
   - Code duplication detection

3. **Dependency Management** (15% weight)
   - Dependency freshness
   - Dependency depth analysis
   - Security vulnerability detection
   - Transitive dependency explosion

4. **Maintainability** (20% weight)
   - Module cohesion measurement
   - Change stability analysis
   - Knowledge concentration detection
   - Refactoring opportunities

5. **Runtime Health** (20% weight)
   - Service availability
   - Response time monitoring
   - Error rate tracking
   - Resource utilization

## API Endpoints

### Run Analysis
```bash
POST /api/v1/arch-health/analyze
{
  "code_path": ".",
  "context": {}
}
```

### Get Current Status
```bash
GET /api/v1/arch-health/status
```

### Get Detailed Summary
```bash
GET /api/v1/arch-health/summary
```

### Get Health Trend
```bash
GET /api/v1/arch-health/trend?days=30
```

### Get Issues
```bash
GET /api/v1/arch-health/issues?status=open&limit=50
```

### Get Recommendations
```bash
GET /api/v1/arch-health/recommendations?status=pending&limit=50
```

### Update Recommendation Status
```bash
PUT /api/v1/arch-health/recommendations/{id}/status?status=implemented
```

## Celery Tasks

### Run Analysis Asynchronously
```python
from app.arch_health.tasks import run_architecture_analysis

# Queue analysis task
task = run_architecture_analysis.delay(code_path=".", context=None)
```

### Scheduled Analysis
Configure in Celery beat:
```python
beat_schedule = {
    "daily-arch-analysis": {
        "task": "app.arch_health.tasks.schedule_periodic_analysis",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "cleanup-old-snapshots": {
        "task": "app.arch_health.tasks.cleanup_old_snapshots",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly on Sunday
        "kwargs": {"days_to_keep": 90},
    },
}
```

## Health Score Calculation

The overall health score (0-100) is calculated as a weighted average of dimension scores:

```
Overall Score = Σ(dimension_score × dimension_weight)
```

Default weights:
- Coupling: 25%
- Quality: 20%
- Dependencies: 15%
- Maintainability: 20%
- Runtime: 20%

### Status Thresholds

- **Healthy**: Score ≥ 70
- **Warning**: 50 ≤ Score < 70
- **Critical**: Score < 50

## Database Models

- `ArchitectureHealthSnapshot`: Overall health snapshot
- `DimensionScore`: Individual dimension scores
- `ArchitectureIssue`: Detected issues
- `ArchitectureRecommendation`: Improvement recommendations
- `AnalysisConfig`: Analysis configuration

## Extending the System

### Adding New Analyzers

1. Create a new analyzer class inheriting from `BaseAnalyzer`
2. Implement the `dimension` property and `analyze()` method
3. Register the analyzer in the service

Example:
```python
from app.arch_health.analyzers.base import BaseAnalyzer, AnalyzerResult

class MyCustomAnalyzer(BaseAnalyzer):
    @property
    def dimension(self) -> str:
        return "custom_dimension"
    
    async def analyze(self, context: dict) -> AnalyzerResult:
        # Your analysis logic here
        pass
```

### Customizing Thresholds

Modify `AnalysisConfig` to adjust:
- Dimension weights
- Warning/critical thresholds
- Enabled analyzers
- Excluded paths

## Best Practices

1. **Run analysis regularly**: Schedule daily or weekly analysis
2. **Track trends**: Focus on improvement over time, not perfect scores
3. **Prioritize critical issues**: Address critical issues first
4. **Review recommendations**: Not all recommendations may apply to your context
5. **Clean up old data**: Regularly clean snapshots older than 90 days

## Integration

The system integrates seamlessly with:
- FastAPI for REST endpoints
- Celery for async task execution
- SQLAlchemy for data persistence
- Existing Sponge agents and workflows

## Example Usage

```python
from app.db.database import SessionLocal
from app.arch_health.services import ArchitectureHealthService

# Create session
db = SessionLocal()

# Initialize service
service = ArchitectureHealthService(db)

# Run analysis
snapshot = await service.run_analysis(code_path="/path/to/code")

# Check results
print(f"Overall Score: {snapshot.overall_score}")
print(f"Status: {snapshot.status}")
print(f"Issues Found: {snapshot.total_issues}")

# Get recommendations
recommendations = service.get_pending_recommendations(limit=10)
for rec in recommendations:
    print(f"- {rec.title} ({rec.priority})")
```
