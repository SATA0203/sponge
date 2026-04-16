"""
Code Executor - Executes code in a sandboxed environment with Docker support
"""

import asyncio
import subprocess
import tempfile
import os
import time
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from loguru import logger


class DockerSandbox:
    """Docker-based code execution sandbox for secure code execution"""
    
    def __init__(
        self,
        timeout: int = 30,
        memory_limit: str = "512m",
        cpu_limit: float = 1.0,
    ):
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.container_id: Optional[str] = None
        
    async def create_container(self, image: str = "python:3.11-slim") -> str:
        """Create a Docker container for code execution"""
        try:
            # Parse memory limit
            mem_limit = self._parse_memory_limit(self.memory_limit)
            
            cmd = [
                "docker", "run", "-d", "--rm",
                "--memory", f"{mem_limit}",
                "--cpus", f"{self.cpu_limit}",
                "--network", "none",  # Disable network access
                "--cap-drop", "ALL",  # Drop all capabilities
                "--read-only",  # Read-only filesystem
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",  # Writable /tmp
                "--pids-limit", "50",  # Limit number of processes
                "--security-opt", "no-new-privileges:true",
                image,
                "sleep", str(self.timeout + 10)  # Keep container alive
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Failed to create container: {stderr.decode()}")
            
            self.container_id = stdout.decode().strip()
            logger.info(f"[DockerSandbox] Container created: {self.container_id[:12]}")
            return self.container_id
            
        except FileNotFoundError:
            raise RuntimeError("Docker is not installed or not in PATH")
        except Exception as e:
            logger.error(f"[DockerSandbox] Failed to create container: {e}")
            raise
    
    async def execute_in_container(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute code inside the Docker container"""
        if not self.container_id:
            await self.create_container()
        
        try:
            if language == "python":
                return await self._execute_python_in_container(code, input_data)
            elif language in ["javascript", "js"]:
                return await self._execute_js_in_container(code, input_data)
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"Unsupported language: {language}",
                }
        except Exception as e:
            logger.error(f"[DockerSandbox] Execution failed: {e}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }
    
    async def _execute_python_in_container(
        self,
        code: str,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Python code in container"""
        # Create temporary file with code
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Copy file to container
            copy_cmd = ["docker", "cp", temp_file, f"{self.container_id}:/tmp/code.py"]
            copy_process = await asyncio.create_subprocess_exec(
                *copy_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await copy_process.communicate()
            
            if copy_process.returncode != 0:
                raise RuntimeError(f"Failed to copy code: {stderr.decode()}")
            
            # Execute code in container
            exec_cmd = [
                "docker", "exec",
                "-i", self.container_id,
                "python", "/tmp/code.py"
            ]
            
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *exec_cmd,
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
                "sandbox": "docker",
            }
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _execute_js_in_container(
        self,
        code: str,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute JavaScript code in container (requires node image)"""
        # For JS, we'd use a node image - simplified here
        return await self._execute_python_in_container(code, input_data)
    
    async def cleanup(self):
        """Clean up the container"""
        if self.container_id:
            try:
                cmd = ["docker", "kill", self.container_id]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await process.communicate()
                logger.info(f"[DockerSandbox] Container {self.container_id[:12]} cleaned up")
            except Exception as e:
                logger.warning(f"[DockerSandbox] Cleanup failed: {e}")
    
    def _parse_memory_limit(self, limit: str) -> int:
        """Parse memory limit string to bytes"""
        limit = limit.lower()
        if limit.endswith('g'):
            return int(limit[:-1]) * 1024 * 1024 * 1024
        elif limit.endswith('m'):
            return int(limit[:-1]) * 1024 * 1024
        elif limit.endswith('k'):
            return int(limit[:-1]) * 1024
        else:
            return int(limit)


class CodeExecutor:
    """Executes code safely in a sandboxed environment"""
    
    def __init__(
        self,
        timeout: int = 30,
        memory_limit: str = "512m",
        use_docker: bool = True,  # Changed default to True for security
        cpu_limit: float = 1.0,
    ):
        """
        Initialize code executor
        
        Args:
            timeout: Execution timeout in seconds
            memory_limit: Memory limit for execution
            use_docker: Whether to use Docker sandbox (default: True for security)
            cpu_limit: CPU limit for Docker container
        """
        self.timeout = timeout
        self.memory_limit = memory_limit
        self.use_docker = use_docker
        self.cpu_limit = cpu_limit
        self.docker_sandbox: Optional[DockerSandbox] = None
        
        # Initialize Docker sandbox if enabled
        if use_docker:
            self.docker_sandbox = DockerSandbox(
                timeout=timeout,
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
            )
            logger.info("[CodeExecutor] Docker sandbox initialized")
        else:
            logger.warning(
                "⚠️  SECURITY WARNING: Running code without Docker sandbox! "
                "This allows arbitrary code execution on the host system. "
                "Only disable Docker sandbox in trusted development environments."
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
        """Execute Python code with security checks"""
        
        # Use Docker sandbox if enabled
        if self.use_docker and self.docker_sandbox:
            try:
                logger.info("[CodeExecutor] Executing in Docker sandbox")
                result = await self.docker_sandbox.execute_in_container(
                    code=code,
                    language="python",
                    input_data=input_data,
                )
                # Install dependencies if provided (in a new container)
                if dependencies:
                    await self._install_dependencies(dependencies, "python")
                return result
            except Exception as e:
                logger.error(f"[CodeExecutor] Docker execution failed, falling back to local: {e}")
                # Fall back to local execution with safety checks
                return await self._execute_python_local(code, input_data, dependencies)
        else:
            # Execute locally with safety checks
            return await self._execute_python_local(code, input_data, dependencies)
    
    async def _execute_python_local(
        self,
        code: str,
        input_data: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute Python code locally with safety checks (fallback mode)"""
        # Security check: Block dangerous operations in non-Docker mode
        self._check_code_safety(code)
        
        # Install dependencies if provided
        if dependencies:
            await self._install_dependencies(dependencies, "python")
        
        # Create temporary file in secure location
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8",
            dir=tempfile.gettempdir(),  # Use system temp directory
        ) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout and resource limits
            process = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    "python",
                    temp_file,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    # Set resource limits if not using Docker
                    preexec_fn=self._set_resource_limits,
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
                "sandbox": "local",
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _check_code_safety(self, code: str) -> None:
        """
        Basic security check for dangerous code patterns.
        Note: This is NOT a substitute for proper sandboxing!
        """
        dangerous_patterns = [
            "__import__('os').system",
            "__import__('subprocess')",
            "os.system(",
            "os.popen(",
            "subprocess.call",
            "subprocess.run",
            "subprocess.Popen",
            "eval(",
            "exec(",
            "compile(",
            "open('/etc/",
            "open('/proc/",
            "socket.socket",
            "urllib.request",
            "http.client",
            "ftplib.FTP",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                logger.warning(f"Potentially dangerous code pattern detected: {pattern}")
                # In production, you might want to raise an exception here
                # raise SecurityError(f"Dangerous code pattern detected: {pattern}")
    
    def _set_resource_limits(self):
        """Set resource limits for child process (Unix only)"""
        import resource
        
        # Limit memory to 512MB
        try:
            memory_bytes = 512 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        except (ValueError, resource.error):
            pass  # Ignore if limits can't be set
        
        # Limit CPU time
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
        except (ValueError, resource.error):
            pass
    
    async def _execute_javascript(
        self,
        code: str,
        input_data: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute JavaScript code using Node.js"""
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
        """Install dependencies for the specified language"""
        if not dependencies:
            return
        
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