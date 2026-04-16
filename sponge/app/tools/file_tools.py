"""
File manipulation tools for Sponge agents
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger


class FileTools:
    """Tools for file operations in the sandbox environment"""
    
    def __init__(self, workspace_root: str = "/tmp/sponge_workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def _safe_path(self, file_path: str) -> Path:
        """Ensure the path is within the workspace root"""
        full_path = (self.workspace_root / file_path).resolve()
        if not str(full_path).startswith(str(self.workspace_root.resolve())):
            raise ValueError(f"Path traversal detected: {file_path}")
        return full_path
    
    def read_file(self, file_path: str) -> str:
        """Read content of a file"""
        try:
            safe_path = self._safe_path(file_path)
            if not safe_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            with open(safe_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            raise
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file"""
        try:
            safe_path = self._safe_path(file_path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully wrote to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            raise
    
    def append_file(self, file_path: str, content: str) -> bool:
        """Append content to a file"""
        try:
            safe_path = self._safe_path(file_path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(safe_path, 'a', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Successfully appended to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error appending file {file_path}: {e}")
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file"""
        try:
            safe_path = self._safe_path(file_path)
            if safe_path.exists():
                safe_path.unlink()
                logger.info(f"Successfully deleted {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            raise
    
    def list_files(self, directory: str = "", recursive: bool = False) -> List[Dict[str, Any]]:
        """List files in a directory"""
        try:
            safe_path = self._safe_path(directory) if directory else self.workspace_root
            
            if not safe_path.exists():
                return []
            
            files = []
            if recursive:
                for path in safe_path.rglob("*"):
                    if path.is_file():
                        rel_path = path.relative_to(self.workspace_root)
                        files.append({
                            "path": str(rel_path),
                            "name": path.name,
                            "size": path.stat().st_size,
                            "type": "file"
                        })
            else:
                for path in safe_path.iterdir():
                    rel_path = path.relative_to(self.workspace_root)
                    files.append({
                        "path": str(rel_path),
                        "name": path.name,
                        "size": path.stat().st_size if path.is_file() else 0,
                        "type": "file" if path.is_file() else "directory"
                    })
            
            return sorted(files, key=lambda x: x["path"])
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {e}")
            return []
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        try:
            safe_path = self._safe_path(file_path)
            return safe_path.exists() and safe_path.is_file()
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            safe_path = self._safe_path(file_path)
            if not safe_path.exists():
                return None
            
            stat = safe_path.stat()
            return {
                "path": file_path,
                "name": safe_path.name,
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "modified_at": stat.st_mtime,
                "is_file": safe_path.is_file(),
                "is_directory": safe_path.is_dir()
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def create_directory(self, dir_path: str) -> bool:
        """Create a directory"""
        try:
            safe_path = self._safe_path(dir_path)
            safe_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Successfully created directory {dir_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating directory {dir_path}: {e}")
            raise
    
    def copy_file(self, src_path: str, dest_path: str) -> bool:
        """Copy a file"""
        try:
            safe_src = self._safe_path(src_path)
            safe_dest = self._safe_path(dest_path)
            
            if not safe_src.exists():
                raise FileNotFoundError(f"Source file not found: {src_path}")
            
            safe_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(safe_src, safe_dest)
            
            logger.info(f"Successfully copied {src_path} to {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            raise
    
    def search_files(self, pattern: str, directory: str = "") -> List[str]:
        """Search for files matching a pattern"""
        try:
            safe_path = self._safe_path(directory) if directory else self.workspace_root
            
            if not safe_path.exists():
                return []
            
            matches = []
            for path in safe_path.rglob(pattern):
                if path.is_file():
                    rel_path = path.relative_to(self.workspace_root)
                    matches.append(str(rel_path))
            
            return sorted(matches)
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return []


class StateAwareFileTools(FileTools):
    """
    Enhanced FileTools with state awareness for Orchestrator-Worker architecture.
    
    Provides methods to read/write task state files (spec.md, history.jsonl, etc.)
    and ensures all operations are logged to the task history for continuity.
    """
    
    def __init__(self, workspace_root: str = "/tmp/sponge_workspace", task_id: Optional[str] = None):
        super().__init__(workspace_root)
        self.task_id = task_id
        self.state_dir = self.workspace_root / (task_id or "default") / ".state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    def write_spec(self, content: str) -> bool:
        """Write immutable task specification (spec.md)"""
        spec_path = self.state_dir / "spec.md"
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"[Task {self.task_id}] Spec written to {spec_path}")
        return True
    
    def read_spec(self) -> Optional[str]:
        """Read task specification"""
        spec_path = self.state_dir / "spec.md"
        if not spec_path.exists():
            return None
        with open(spec_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def append_to_history(self, entry: Dict[str, Any]) -> bool:
        """Append entry to history.jsonl (append-only, preserves reasoning chain)"""
        import json
        history_path = self.state_dir / "history.jsonl"
        entry['timestamp'] = datetime.utcnow().isoformat()
        entry['task_id'] = self.task_id
        
        with open(history_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        logger.debug(f"[Task {self.task_id}] History entry added: {entry.get('action', 'unknown')}")
        return True
    
    def read_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Read recent history entries"""
        import json
        history_path = self.state_dir / "history.jsonl"
        if not history_path.exists():
            return []
        
        entries = []
        with open(history_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        
        return entries[-limit:]
    
    def update_current_status(self, status: Dict[str, Any]) -> bool:
        """Update current status (overwrite)"""
        import json
        status_path = self.state_dir / "current_status.json"
        status['updated_at'] = datetime.utcnow().isoformat()
        status['task_id'] = self.task_id
        
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2)
        
        logger.debug(f"[Task {self.task_id}] Status updated: {status.get('phase', 'unknown')}")
        return True
    
    def get_current_status(self) -> Optional[Dict[str, Any]]:
        """Get current status"""
        import json
        status_path = self.state_dir / "current_status.json"
        if not status_path.exists():
            return None
        
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def add_known_issue(self, issue: str, context: Optional[str] = None) -> bool:
        """Add known issue to avoid repeating mistakes (append-only)"""
        import json
        issues_path = self.state_dir / "known_issues.json"
        
        issues = []
        if issues_path.exists():
            with open(issues_path, 'r', encoding='utf-8') as f:
                issues = json.load(f)
        
        issues.append({
            'issue': issue,
            'context': context,
            'added_at': datetime.utcnow().isoformat(),
            'task_id': self.task_id
        })
        
        with open(issues_path, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2)
        
        logger.warning(f"[Task {self.task_id}] Known issue added: {issue[:50]}...")
        return True
    
    def get_known_issues(self) -> List[Dict[str, Any]]:
        """Get all known issues"""
        import json
        issues_path = self.state_dir / "known_issues.json"
        if not issues_path.exists():
            return []
        
        with open(issues_path, 'r', encoding='utf-8') as f:
            return json.load(f)
