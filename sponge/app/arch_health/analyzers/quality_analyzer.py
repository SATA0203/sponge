"""
Quality Analyzer - Measures code quality metrics
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Any

from .base import BaseAnalyzer, AnalyzerResult, MetricResult


class QualityAnalyzer(BaseAnalyzer):
    """Analyzes code quality metrics"""
    
    @property
    def dimension(self) -> str:
        return "quality"
    
    async def analyze(self, context: Dict[str, Any]) -> AnalyzerResult:
        """Analyze quality metrics"""
        start_time = time.time()
        
        code_path = context.get("code_path", ".")
        excluded_paths = context.get("excluded_paths", ["__pycache__", ".git", "node_modules", "venv"])
        
        metrics = []
        issues = []
        recommendations = []
        
        # Try to use radon for complexity analysis if available
        try:
            from radon.complexity import cc_visit
            from radon.metrics import h_visit
            
            complexity_data = self._analyze_complexity(code_path, excluded_paths, cc_visit)
            
            # Average Cyclomatic Complexity
            avg_complexity = complexity_data.get("avg_complexity", 0)
            metrics.append(MetricResult(
                name="avg_cyclomatic_complexity",
                value=avg_complexity,
                threshold=10.0,
                status=self.get_metric_status(avg_complexity, 10.0, 20.0),
                description="Average cyclomatic complexity across all functions"
            ))
            
            if avg_complexity > 10:
                issues.append({
                    "type": "high_complexity",
                    "severity": "warning",
                    "title": f"High average complexity: {avg_complexity:.2f}",
                    "description": "Functions are too complex on average",
                    "evidence": complexity_data.get("hotspots", [])[:5]
                })
                recommendations.append({
                    "type": "refactor",
                    "title": "Reduce code complexity",
                    "description": "Break down complex functions into smaller, focused functions",
                    "priority": "high",
                    "steps": [
                        "Identify functions with complexity > 10",
                        "Extract logical blocks into separate functions",
                        "Use early returns to reduce nesting",
                        "Apply single responsibility principle"
                    ]
                })
            
            # Maintainability Index
            maintainability_index = complexity_data.get("maintainability_index", 100)
            metrics.append(MetricResult(
                name="maintainability_index",
                value=maintainability_index,
                threshold=65.0,
                status=self.get_metric_status(100 - maintainability_index, 35.0, 50.0),
                description="Maintainability index (higher is better)"
            ))
            
        except ImportError:
            # Fallback: basic file-based metrics
            python_files = self._discover_files(code_path, excluded_paths)
            
            # File count and size metrics
            total_lines = 0
            total_files = len(python_files)
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        total_lines += len(lines)
                except Exception:
                    continue
            
            avg_file_size = total_lines / total_files if total_files > 0 else 0
            
            metrics.append(MetricResult(
                name="avg_file_size_lines",
                value=min(100, avg_file_size / 10),  # Normalize to 0-100
                threshold=30.0,
                status=self.get_metric_status(avg_file_size, 300.0, 500.0),
                description="Average file size in lines"
            ))
            
            maintainability_index = 70.0  # Default estimate
        
        # Test coverage (if available from context)
        test_coverage = context.get("test_coverage", None)
        if test_coverage is not None:
            metrics.append(MetricResult(
                name="test_coverage",
                value=test_coverage,
                threshold=80.0,
                status=self.get_metric_status(test_coverage, 80.0, 60.0),
                description="Test coverage percentage"
            ))
            
            if test_coverage < 80:
                issues.append({
                    "type": "low_test_coverage",
                    "severity": "warning" if test_coverage >= 60 else "critical",
                    "title": f"Low test coverage: {test_coverage:.1f}%",
                    "description": "Insufficient test coverage detected",
                    "evidence": {"coverage": test_coverage}
                })
                recommendations.append({
                    "type": "testing",
                    "title": "Improve test coverage",
                    "description": f"Increase test coverage from {test_coverage:.1f}% to at least 80%",
                    "priority": "high" if test_coverage < 60 else "medium",
                    "steps": [
                        "Identify untested modules and functions",
                        "Write unit tests for core business logic",
                        "Add integration tests for critical paths",
                        "Set up coverage reporting in CI/CD"
                    ]
                })
        else:
            # Estimate based on test file presence
            test_ratio = self._estimate_test_coverage(code_path)
            metrics.append(MetricResult(
                name="estimated_test_ratio",
                value=test_ratio,
                threshold=30.0,
                status="ok" if test_ratio >= 30 else "warning",
                description="Estimated test-to-code ratio"
            ))
        
        # Code duplication estimate
        duplication_rate = context.get("duplication_rate", None)
        if duplication_rate is not None:
            metrics.append(MetricResult(
                name="code_duplication",
                value=duplication_rate,
                threshold=5.0,
                status=self.get_metric_status(duplication_rate, 5.0, 10.0),
                description="Percentage of duplicated code"
            ))
        
        # Calculate overall score
        score = self.calculate_score(metrics)
        
        execution_time = int((time.time() - start_time) * 1000)
        
        return AnalyzerResult(
            analyzer_name=self.name,
            dimension=self.dimension,
            score=score,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations,
            execution_time_ms=execution_time
        )
    
    def _discover_files(self, root_path: str, excluded: List[str]) -> List[Path]:
        """Discover all Python files"""
        files = []
        root = Path(root_path)
        
        for path in root.rglob("*.py"):
            if any(excl in str(path) for excl in excluded):
                continue
            files.append(path)
        
        return files
    
    def _analyze_complexity(self, code_path: str, excluded: List[str], cc_visit) -> Dict[str, Any]:
        """Analyze code complexity using radon"""
        complexities = []
        maintainability_scores = []
        hotspots = []
        
        root = Path(code_path)
        
        for path in root.rglob("*.py"):
            if any(excl in str(path) for excl in excluded):
                continue
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Cyclomatic complexity
                results = cc_visit(content)
                for result in results:
                    complexities.append(result.complexity)
                    if result.complexity > 10:
                        hotspots.append({
                            "file": str(path),
                            "name": result.name,
                            "complexity": result.complexity,
                            "line": result.lineno
                        })
                
                # Maintainability
                from radon.metrics import mi_visit
                mi = mi_visit(content, multi=True)
                if mi:
                    maintainability_scores.extend([v for v in mi.values() if v is not None])
                    
            except Exception:
                continue
        
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0
        avg_mi = sum(maintainability_scores) / len(maintainability_scores) if maintainability_scores else 100
        
        # Sort hotspots by complexity
        hotspots.sort(key=lambda x: x["complexity"], reverse=True)
        
        return {
            "avg_complexity": avg_complexity,
            "maintainability_index": avg_mi,
            "hotspots": hotspots[:10]
        }
    
    def _estimate_test_coverage(self, code_path: str) -> float:
        """Estimate test coverage based on test file presence"""
        root = Path(code_path)
        
        py_files = list(root.rglob("*.py"))
        test_files = list(root.rglob("test_*.py")) + list(root.rglob("*_test.py"))
        
        # Filter out test files from total
        non_test_files = [f for f in py_files if not any(x in str(f) for x in ["test_", "_test"])]
        
        if not non_test_files:
            return 100.0
        
        # Simple ratio estimation
        ratio = (len(test_files) / len(non_test_files)) * 100 if non_test_files else 0
        return min(100.0, ratio)
