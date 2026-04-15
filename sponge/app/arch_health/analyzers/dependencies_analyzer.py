"""
Dependencies Analyzer - Measures dependency health
"""

import time
from pathlib import Path
from typing import Dict, List, Any

from .base import BaseAnalyzer, AnalyzerResult, MetricResult


class DependenciesAnalyzer(BaseAnalyzer):
    """Analyzes dependency health and management"""
    
    @property
    def dimension(self) -> str:
        return "dependencies"
    
    async def analyze(self, context: Dict[str, Any]) -> AnalyzerResult:
        """Analyze dependency metrics"""
        start_time = time.time()
        
        code_path = context.get("code_path", ".")
        metrics = []
        issues = []
        recommendations = []
        
        # Analyze requirements.txt or pyproject.toml
        deps_info = self._analyze_dependencies(code_path)
        
        # 1. Total dependencies count
        total_deps = deps_info.get("total_dependencies", 0)
        metrics.append(MetricResult(
            name="total_dependencies",
            value=min(100, total_deps),
            threshold=50.0,
            status=self.get_metric_status(total_deps, 50.0, 100.0),
            description="Total number of direct dependencies"
        ))
        
        if total_deps > 50:
            issues.append({
                "type": "dependency_bloat",
                "severity": "warning",
                "title": f"Too many dependencies: {total_deps}",
                "description": "Consider auditing and removing unused dependencies",
                "evidence": {"count": total_deps}
            })
            recommendations.append({
                "type": "cleanup",
                "title": "Audit and reduce dependencies",
                "description": "Review all dependencies and remove unused ones",
                "priority": "medium",
                "steps": [
                    "Use tools like deptry or pipreqs to identify unused dependencies",
                    "Check for duplicate functionality across packages",
                    "Consider replacing multiple small packages with alternatives",
                    "Document why each critical dependency is needed"
                ]
            })
        
        # 2. Outdated dependencies
        outdated_count = deps_info.get("outdated_count", 0)
        outdated_ratio = (outdated_count / total_deps * 100) if total_deps > 0 else 0
        
        metrics.append(MetricResult(
            name="outdated_dependencies_ratio",
            value=outdated_ratio,
            threshold=20.0,
            status=self.get_metric_status(outdated_ratio, 20.0, 50.0),
            description="Percentage of outdated dependencies"
        ))
        
        if outdated_ratio > 20:
            issues.append({
                "type": "outdated_dependencies",
                "severity": "warning" if outdated_ratio < 50 else "critical",
                "title": f"{outdated_count} outdated dependencies ({outdated_ratio:.1f}%)",
                "description": "Many dependencies are behind latest versions",
                "evidence": {"outdated": deps_info.get("outdated_list", [])[:10]}
            })
            recommendations.append({
                "type": "upgrade",
                "title": "Update outdated dependencies",
                "description": "Create a plan to update dependencies systematically",
                "priority": "high" if outdated_ratio > 50 else "medium",
                "steps": [
                    "Run 'pip list --outdated' to see all outdated packages",
                    "Update minor versions first (patch updates)",
                    "Test thoroughly after each major version update",
                    "Use dependabot or similar for automated updates",
                    "Pin versions in requirements files for reproducibility"
                ]
            })
        
        # 3. Dependency depth
        max_depth = deps_info.get("max_depth", 0)
        metrics.append(MetricResult(
            name="dependency_depth",
            value=float(max_depth),
            threshold=10.0,
            status=self.get_metric_status(max_depth, 10.0, 15.0),
            description="Maximum dependency tree depth"
        ))
        
        if max_depth > 10:
            issues.append({
                "type": "deep_dependency_tree",
                "severity": "info",
                "title": f"Deep dependency tree: {max_depth} levels",
                "description": "Deep trees increase build time and potential conflicts",
                "evidence": {"depth": max_depth}
            })
        
        # 4. Security vulnerabilities (if available from context)
        vulnerabilities = context.get("security_vulnerabilities", [])
        vuln_count = len(vulnerabilities)
        
        metrics.append(MetricResult(
            name="security_vulnerabilities",
            value=float(vuln_count),
            threshold=0.0,
            status="critical" if vuln_count > 0 else "ok",
            description="Number of known security vulnerabilities"
        ))
        
        if vuln_count > 0:
            issues.append({
                "type": "security_vulnerabilities",
                "severity": "critical",
                "title": f"{vuln_count} security vulnerabilities found",
                "description": "Immediate action required to address security issues",
                "evidence": {"vulnerabilities": vulnerabilities[:5]}
            })
            recommendations.append({
                "type": "security",
                "title": "Fix security vulnerabilities immediately",
                "description": "Update vulnerable packages to patched versions",
                "priority": "critical",
                "steps": [
                    "Run 'pip-audit' or 'safety check' to identify vulnerabilities",
                    "Prioritize fixing critical and high severity issues",
                    "Update to secure versions immediately",
                    "Set up automated security scanning in CI/CD",
                    "Subscribe to security advisories for critical dependencies"
                ]
            })
        
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
    
    def _analyze_dependencies(self, code_path: str) -> Dict[str, Any]:
        """Analyze project dependencies"""
        result = {
            "total_dependencies": 0,
            "outdated_count": 0,
            "outdated_list": [],
            "max_depth": 0,
            "direct_deps": [],
            "transitive_deps": []
        }
        
        root = Path(code_path)
        
        # Look for requirements.txt
        req_file = root / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    lines = f.readlines()
                
                deps = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        # Extract package name
                        pkg_name = line.split('==')[0].split('>')[0].split('<')[0].split('[')[0]
                        if pkg_name:
                            deps.append(pkg_name)
                
                result["total_dependencies"] = len(deps)
                result["direct_deps"] = deps
                
                # Try to get dependency tree depth using pip
                try:
                    import subprocess
                    proc = subprocess.run(
                        ["pip", "deptree", "--json-tree"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if proc.returncode == 0:
                        import json
                        tree = json.loads(proc.stdout)
                        result["max_depth"] = self._calculate_max_depth(tree)
                except Exception:
                    # Estimate depth
                    result["max_depth"] = min(5, len(deps) // 10 + 1)
                    
            except Exception:
                pass
        
        # Look for pyproject.toml
        pyproject = root / "pyproject.toml"
        if pyproject.exists() and result["total_dependencies"] == 0:
            try:
                import tomli
                with open(pyproject, 'rb') as f:
                    data = tomli.load(f)
                
                deps = []
                project = data.get("project", {})
                dependencies = project.get("dependencies", [])
                optional = project.get("optional-dependencies", {})
                
                for dep in dependencies:
                    pkg_name = dep.split('==')[0].split('>')[0].split('<')[0].split('[')[0]
                    if pkg_name:
                        deps.append(pkg_name)
                
                for opt_deps in optional.values():
                    for dep in opt_deps:
                        pkg_name = dep.split('==')[0].split('>')[0].split('<')[0].split('[')[0]
                        if pkg_name:
                            deps.append(pkg_name)
                
                result["total_dependencies"] = len(deps)
                result["direct_deps"] = deps
                
            except Exception:
                pass
        
        # Check for outdated packages (best effort)
        try:
            import subprocess
            proc = subprocess.run(
                ["pip", "list", "--outdated", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if proc.returncode == 0:
                import json
                outdated = json.loads(proc.stdout)
                result["outdated_count"] = len(outdated)
                result["outdated_list"] = [
                    {"name": pkg["name"], "current": pkg["version"], "latest": pkg["latest_version"]}
                    for pkg in outdated[:10]
                ]
        except Exception:
            pass
        
        return result
    
    def _calculate_max_depth(self, tree: List[Dict], current_depth: int = 1) -> int:
        """Calculate maximum depth of dependency tree"""
        if not tree:
            return current_depth
        
        max_child_depth = current_depth
        for node in tree:
            children = node.get("dependencies", [])
            if children:
                child_depth = self._calculate_max_depth(children, current_depth + 1)
                max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
