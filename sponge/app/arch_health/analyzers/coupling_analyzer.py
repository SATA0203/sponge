"""
Coupling Analyzer - Measures module coupling and dependencies
"""

import os
import ast
import time
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict

from .base import BaseAnalyzer, AnalyzerResult, MetricResult


class CouplingAnalyzer(BaseAnalyzer):
    """Analyzes code coupling and module dependencies"""
    
    @property
    def dimension(self) -> str:
        return "coupling"
    
    async def analyze(self, context: Dict[str, Any]) -> AnalyzerResult:
        """Analyze coupling metrics"""
        start_time = time.time()
        
        code_path = context.get("code_path", ".")
        excluded_paths = context.get("excluded_paths", ["__pycache__", ".git", "node_modules", "venv"])
        
        # Discover Python files
        python_files = self._discover_files(code_path, excluded_paths)
        
        # Build dependency graph
        dependencies = self._build_dependency_graph(python_files, code_path)
        
        # Calculate metrics
        metrics = []
        issues = []
        recommendations = []
        
        # 1. Coupling Index (average dependencies per module)
        coupling_index = self._calculate_coupling_index(dependencies)
        metrics.append(MetricResult(
            name="coupling_index",
            value=coupling_index,
            threshold=10.0,
            status=self.get_metric_status(coupling_index, 10.0, 15.0),
            description="Average number of dependencies per module"
        ))
        
        # 2. Circular Dependencies
        circular_deps = self._detect_circular_dependencies(dependencies)
        circular_count = len(circular_deps)
        metrics.append(MetricResult(
            name="circular_dependencies",
            value=float(circular_count),
            threshold=0.0,
            status="critical" if circular_count > 0 else "ok",
            description="Number of circular dependency cycles"
        ))
        
        if circular_count > 0:
            for cycle in circular_deps[:5]:  # Top 5 cycles
                issues.append({
                    "type": "circular_dependency",
                    "severity": "critical",
                    "title": f"Circular dependency detected: {' -> '.join(cycle)}",
                    "location": cycle[0],
                    "affected_components": cycle,
                    "evidence": {"cycle": cycle}
                })
                recommendations.append({
                    "type": "refactor",
                    "title": "Break circular dependency",
                    "description": f"Refactor modules to break the cycle: {' -> '.join(cycle)}",
                    "priority": "critical",
                    "steps": [
                        "Identify shared functionality causing the cycle",
                        "Extract common code to a new utility module",
                        "Use dependency injection or interfaces",
                        "Update imports to use the new structure"
                    ]
                })
        
        # 3. God Modules (modules with too many dependents)
        god_modules = self._detect_god_modules(dependencies, threshold=10)
        metrics.append(MetricResult(
            name="god_modules",
            value=float(len(god_modules)),
            threshold=0.0,
            status=self.get_metric_status(len(god_modules), 2.0, 5.0),
            description="Modules with excessive dependents"
        ))
        
        for module, dependents in god_modules.items():
            issues.append({
                "type": "god_module",
                "severity": "warning",
                "title": f"God module detected: {module}",
                "location": module,
                "affected_components": [module] + list(dependents)[:10],
                "evidence": {"dependent_count": len(dependents), "dependents": list(dependents)[:10]}
            })
            recommendations.append({
                "type": "refactor",
                "title": f"Decompose god module: {module}",
                "description": f"Module {module} has {len(dependents)} dependents. Consider splitting responsibilities.",
                "priority": "high",
                "steps": [
                    "Identify distinct responsibilities within the module",
                    "Group related functions/classes together",
                    "Create separate modules for each responsibility",
                    "Update imports in dependent modules gradually"
                ]
            })
        
        # 4. Layer Violations (if layer structure is defined)
        layer_violations = context.get("layer_violations", [])
        if layer_violations:
            metrics.append(MetricResult(
                name="layer_violations",
                value=float(len(layer_violations)),
                threshold=0.0,
                status=self.get_metric_status(len(layer_violations), 3.0, 10.0),
                description="Architecture layer violations"
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
        """Discover all Python files in the given path"""
        files = []
        root = Path(root_path)
        
        for path in root.rglob("*.py"):
            # Check if any excluded path is in the path
            if any(excl in str(path) for excl in excluded):
                continue
            files.append(path)
        
        return files
    
    def _build_dependency_graph(self, files: List[Path], base_path: str) -> Dict[str, Set[str]]:
        """Build a dependency graph from Python files"""
        dependencies = defaultdict(set)
        base = Path(base_path)
        
        for file_path in files:
            try:
                module_name = self._path_to_module(file_path, base)
                imports = self._extract_imports(file_path)
                
                for imp in imports:
                    # Resolve relative imports
                    if imp.startswith('.'):
                        resolved = self._resolve_relative_import(file_path, imp, base)
                        if resolved:
                            dependencies[module_name].add(resolved)
                    else:
                        # Only track internal dependencies
                        if self._is_internal_module(imp, files, base):
                            dependencies[module_name].add(imp)
            except Exception:
                continue
        
        return dict(dependencies)
    
    def _path_to_module(self, path: Path, base: Path) -> str:
        """Convert file path to module name"""
        try:
            rel_path = path.relative_to(base)
            parts = list(rel_path.parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1][:-3]  # Remove .py
            
            return ".".join(parts) if parts else ""
        except ValueError:
            return path.stem
    
    def _extract_imports(self, file_path: Path) -> List[str]:
        """Extract import statements from a Python file"""
        imports = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:
                            # Relative import
                            imports.append('.' * node.level + node.module)
                        else:
                            imports.append(node.module)
        except Exception:
            pass
        
        return imports
    
    def _resolve_relative_import(self, current_file: Path, import_str: str, base: Path) -> str:
        """Resolve relative import to absolute module path"""
        parts = current_file.relative_to(base).parts[:-1]  # Exclude filename
        
        # Count leading dots
        level = 0
        for char in import_str:
            if char == '.':
                level += 1
            else:
                break
        
        # Go up directories based on level
        if level > len(parts):
            return None
        
        base_parts = parts[:-(level-1)] if level > 1 else parts
        
        # Get the module part after dots
        module_part = import_str[level:]
        
        if not base_parts:
            return module_part
        
        return ".".join(base_parts) + "." + module_part if module_part else ".".join(base_parts)
    
    def _is_internal_module(self, module_name: str, files: List[Path], base: Path) -> bool:
        """Check if a module is internal (part of the project)"""
        # Simple heuristic: check if module path matches any file
        module_path = module_name.replace('.', '/')
        
        for f in files:
            rel_path = str(f.relative_to(base))[:-3]  # Remove .py
            if rel_path == module_path or rel_path.endswith("/" + module_path):
                return True
        
        return False
    
    def _calculate_coupling_index(self, dependencies: Dict[str, Set[str]]) -> float:
        """Calculate average coupling index"""
        if not dependencies:
            return 0.0
        
        total_deps = sum(len(deps) for deps in dependencies.values())
        return total_deps / len(dependencies)
    
    def _detect_circular_dependencies(self, dependencies: Dict[str, Set[str]]) -> List[List[str]]:
        """Detect circular dependencies using DFS"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def _detect_god_modules(self, dependencies: Dict[str, Set[str]], threshold: int = 10) -> Dict[str, Set[str]]:
        """Detect modules with too many dependents"""
        # Reverse the dependency graph
        dependents = defaultdict(set)
        
        for module, deps in dependencies.items():
            for dep in deps:
                dependents[dep].add(module)
        
        # Find modules with many dependents
        return {
            module: deps 
            for module, deps in dependents.items() 
            if len(deps) >= threshold
        }
