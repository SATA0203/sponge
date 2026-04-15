"""
API Router for File Operations
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from app.schemas import (
    UpdateFileRequest,
    FileListResponse,
    FileContentResponse,
)
from app.tools.file_tools import FileTools

router = APIRouter()

# Initialize file tools with workspace root
file_tools = FileTools(workspace_root="/tmp/sponge_workspace")


@router.get("/", response_model=FileListResponse)
async def list_files(
    task_id: str = Query(..., description="Task ID"),
    directory: str = Query("", description="Directory path"),
    recursive: bool = Query(False, description="List files recursively"),
):
    """List files in a task workspace"""
    # In production, use task_id to determine workspace path
    files = file_tools.list_files(directory=directory, recursive=recursive)
    
    return FileListResponse(files=files, total=len(files))


@router.get("/content", response_model=FileContentResponse)
async def get_file_content(
    task_id: str = Query(..., description="Task ID"),
    path: str = Query(..., description="File path"),
):
    """Get content of a specific file"""
    try:
        content = file_tools.read_file(path)
        
        # Determine language from file extension
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".txt": "text",
        }
        
        import os
        ext = os.path.splitext(path)[1].lower()
        language = ext_map.get(ext)
        
        return FileContentResponse(
            file_path=path,
            content=content,
            language=language,
            size=len(content),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}",
        )


@router.post("/update")
async def update_file(
    task_id: str = Query(..., description="Task ID"),
    request: UpdateFileRequest = None,
):
    """Update a file (write, append, or delete)"""
    try:
        if request.operation == "write":
            success = file_tools.write_file(request.file_path, request.content)
        elif request.operation == "append":
            success = file_tools.append_file(request.file_path, request.content)
        elif request.operation == "delete":
            success = file_tools.delete_file(request.file_path)
        else:
            raise ValueError(f"Unknown operation: {request.operation}")
        
        if success:
            return {
                "message": f"Successfully {request.operation}d file {request.file_path}"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating file: {str(e)}",
        )


@router.get("/exists")
async def check_file_exists(
    task_id: str = Query(..., description="Task ID"),
    path: str = Query(..., description="File path"),
):
    """Check if a file exists"""
    exists = file_tools.file_exists(path)
    return {"exists": exists, "path": path}
