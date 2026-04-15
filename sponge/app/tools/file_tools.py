"""
File manipulation tools for Sponge agents
"""

import os
import shutil
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
