"""
Code Executor - Executes code in a sandboxed environment
"""

import asyncio
import subprocess
import tempfile
import os
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger


class CodeExecutor:
    """Executes code safely in a sandboxed environment"""
    
    def __init__(
        self,
        timeout: int = 30,
        memory_limit: str = "512m",
        use_docker: bool = True,  # Changed default to True for security
    ):
        """
        Initialize code executor
        
        Args:
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for execution
            use_docker: Whether to use Docker sandbox (default: True for security)
        """
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.use_docker = use_docker
        
        if not self.use_docker:
            logger.warning(
                "⚠️  SECURITY WARNING: Running code WITHOUT Docker sandbox! "
                "This allows arbitrary code execution on the host system. "
                "Set use_docker=True for production use."
            )
        
        logger.info(f"Initialized CodeExecutor (timeout={timeout}s, docker={use_docker})")
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute code and return results
        
        Args:
            code: Code to execute
            language: Programming language
            input_data: Optional input to pass to the code
            dependencies: Optional list of dependencies to install
            
        Returns:
            Dictionary with execution results
        """
        start_time = time.time()
        
        try:
            if language.lower() == "python":
                result = await self._execute_python(code, input_data, dependencies)
            elif language.lower() in ["javascript", "js"]:
                result = await self._execute_javascript(code, input_data, dependencies)
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Unsupported language: {language}",
                    "execution_time": 0,
                }
            
            execution_time = time.time() - start_time
            result["execution_time"] = execution_time
            
            logger.info(f"Code execution completed in {execution_time:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "output": "",
                "error": f"Execution timed out after {self.timeout} seconds",
                "execution_time": self.timeout,
            }
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "execution_time": time.time() - start_time,
            }
    
    async def _execute_python(
        self,
        code: str,
        input_data: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute Python code with security restrictions"""
        # Security check: Block dangerous operations when not using Docker
        if not self.use_docker:
            dangerous_patterns = [
                'os.system', 'subprocess', 'eval(', 'exec(', 
                '__import__', 'open(', 'importlib', 'pickle'
            ]
            for pattern in dangerous_patterns:
                if pattern in code:
                    logger.warning(f"Blocked potentially dangerous code: {pattern}")
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Security violation: Use of '{pattern}' is not allowed without Docker sandbox",
                        "execution_time": 0,
                    }
        
        # Install dependencies if provided
        if dependencies:
            await self._install_dependencies(dependencies, "python")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "python",
                    temp_file,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=self.timeout,
            )
            
            # Send input data if provided
            stdin_data = input_data.encode() if input_data else None
            stdout, stderr = await process.communicate(input=stdin_data)
            
            success = process.returncode == 0
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            error = stderr.decode("utf-8", errors="replace") if stderr and not success else ""
            
            return {
                "success": success,
                "output": output,
                "error": error if not success else None,
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _execute_javascript(
        self,
        code: str,
        input_data: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute JavaScript code using Node.js with security restrictions"""
        # Security check: Block dangerous operations when not using Docker
        if not self.use_docker:
            dangerous_patterns = [
                'require(', 'eval(', 'Function(', 'vm.', 
                'child_process', 'fs.', 'exec', 'spawn'
            ]
            for pattern in dangerous_patterns:
                if pattern in code:
                    logger.warning(f"Blocked potentially dangerous code: {pattern}")
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Security violation: Use of '{pattern}' is not allowed without Docker sandbox",
                        "execution_time": 0,
                    }
        
        # Install dependencies if provided
        if dependencies:
            await self._install_dependencies(dependencies, "javascript")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".js",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "node",
                    temp_file,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=self.timeout,
            )
            
            stdin_data = input_data.encode() if input_data else None
            stdout, stderr = await process.communicate(input=stdin_data)
            
            success = process.returncode == 0
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            error = stderr.decode("utf-8", errors="replace") if stderr and not success else ""
            
            return {
                "success": success,
                "output": output,
                "error": error if not success else None,
            }
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _install_dependencies(
        self,
        dependencies: List[str],
        language: str,
    ):
        """Install dependencies for the specified language with security restrictions"""
        if not dependencies:
            return
        
        # Security check: Block dependency installation when not using Docker
        if not self.use_docker:
            logger.warning(
                "⚠️  SECURITY WARNING: Installing dependencies without Docker sandbox! "
                "This could install malicious packages on the host system."
            )
            # Limit the number of dependencies to prevent abuse
            if len(dependencies) > 5:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Security violation: Cannot install more than 5 dependencies without Docker sandbox (requested: {len(dependencies)})",
                    "execution_time": 0,
                }
        
        try:
            if language == "python":
                # Install Python packages with pip
                cmd = ["pip", "install", "--quiet"] + dependencies
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                
            elif language == "javascript":
                # Install npm packages
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Create package.json
                    pkg_json = {"dependencies": {dep: "latest" for dep in dependencies}}
                    import json
                    with open(os.path.join(tmpdir, "package.json"), "w") as f:
                        json.dump(pkg_json, f)
                    
                    # Run npm install
                    process = await asyncio.create_subprocess_exec(
                        "npm",
                        "install",
                        cwd=tmpdir,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await process.communicate()
                    
        except Exception as e:
            logger.warning(f"Failed to install dependencies: {e}")
            # Continue anyway - dependencies might already be installed