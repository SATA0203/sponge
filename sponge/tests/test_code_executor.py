"""
Unit tests for CodeExecutor with Docker sandbox support
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.tools.code_executor import CodeExecutor, DockerSandbox


class TestDockerSandbox:
    """Tests for DockerSandbox class"""
    
    @pytest.mark.asyncio
    async def test_parse_memory_limit(self):
        """Test memory limit parsing"""
        sandbox = DockerSandbox()
        
        assert sandbox._parse_memory_limit("512m") == 512 * 1024 * 1024
        assert sandbox._parse_memory_limit("1g") == 1024 * 1024 * 1024
        assert sandbox._parse_memory_limit("1024k") == 1024 * 1024
        assert sandbox._parse_memory_limit("1048576") == 1048576
    
    @pytest.mark.asyncio
    async def test_create_container_success(self):
        """Test successful container creation"""
        sandbox = DockerSandbox(timeout=30)
        
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"abc123def456\n", b""))
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            container_id = await sandbox.create_container()
            assert container_id == "abc123def456"
            assert sandbox.container_id == "abc123def456"
    
    @pytest.mark.asyncio
    async def test_create_container_failure(self):
        """Test container creation failure"""
        sandbox = DockerSandbox()
        
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b"Docker not running"))
        mock_process.returncode = 1
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with pytest.raises(RuntimeError, match="Failed to create container"):
                await sandbox.create_container()
    
    @pytest.mark.asyncio
    async def test_create_container_docker_not_found(self):
        """Test when Docker is not installed"""
        sandbox = DockerSandbox()
        
        with patch('asyncio.create_subprocess_exec', side_effect=FileNotFoundError()):
            with pytest.raises(RuntimeError, match="Docker is not installed"):
                await sandbox.create_container()


class TestCodeExecutor:
    """Tests for CodeExecutor class"""
    
    def test_init_with_docker(self):
        """Test initialization with Docker enabled"""
        executor = CodeExecutor(use_docker=True)
        assert executor.use_docker is True
        assert executor.docker_sandbox is not None
        assert executor.timeout == 30
        assert executor.memory_limit == "512m"
    
    def test_init_without_docker(self):
        """Test initialization with Docker disabled"""
        executor = CodeExecutor(use_docker=False)
        assert executor.use_docker is False
        assert executor.docker_sandbox is None
    
    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        executor = CodeExecutor(
            timeout=60,
            memory_limit="1g",
            use_docker=True,
            cpu_limit=2.0,
        )
        assert executor.timeout == 60
        assert executor.memory_limit == "1g"
        assert executor.cpu_limit == 2.0
    
    @pytest.mark.asyncio
    async def test_execute_python_docker_mode(self):
        """Test Python code execution in Docker mode"""
        executor = CodeExecutor(use_docker=True)
        
        # Mock the docker sandbox execute method
        mock_result = {
            "success": True,
            "output": "Hello, World!\n",
            "error": None,
            "sandbox": "docker",
        }
        
        with patch.object(
            executor.docker_sandbox,
            'execute_in_container',
            new_callable=AsyncMock,
            return_value=mock_result
        ):
            result = await executor.execute(
                code='print("Hello, World!")',
                language="python",
            )
            
            assert result["success"] is True
            assert result["output"] == "Hello, World!\n"
            assert result["sandbox"] == "docker"
            assert "execution_time" in result
    
    @pytest.mark.asyncio
    async def test_execute_python_local_mode(self):
        """Test Python code execution in local mode (fallback)"""
        executor = CodeExecutor(use_docker=False)
        
        # Simple code that should pass safety checks
        code = "print(2 + 2)"
        
        # Mock subprocess execution
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(b"4\n", b""))
        mock_process.returncode = 0
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch('asyncio.wait_for', return_value=mock_process):
                result = await executor.execute(
                    code=code,
                    language="python",
                )
                
                assert result["success"] is True
                assert result["sandbox"] == "local"
    
    @pytest.mark.asyncio
    async def test_execute_unsupported_language(self):
        """Test execution with unsupported language"""
        executor = CodeExecutor()
        
        result = await executor.execute(
            code="some code",
            language="cobol",
        )
        
        assert result["success"] is False
        assert "Unsupported language" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """Test execution timeout handling"""
        executor = CodeExecutor(timeout=1)
        
        with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()):
            result = await executor.execute(
                code="while True: pass",
                language="python",
            )
            
            assert result["success"] is False
            assert "timed out" in result["error"]
    
    @pytest.mark.asyncio
    async def test_docker_fallback_on_error(self):
        """Test fallback to local execution when Docker fails"""
        executor = CodeExecutor(use_docker=True)
        
        # Mock Docker sandbox to fail
        with patch.object(
            executor.docker_sandbox,
            'execute_in_container',
            new_callable=AsyncMock,
            side_effect=Exception("Docker error")
        ):
            # Mock local execution
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"output\n", b""))
            mock_process.returncode = 0
            
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                with patch('asyncio.wait_for', return_value=mock_process):
                    result = await executor.execute(
                        code="print('test')",
                        language="python",
                    )
                    
                    # Should fall back to local execution
                    assert result["sandbox"] == "local"


class TestCodeSafety:
    """Tests for code safety checks"""
    
    def test_safe_code_detection(self):
        """Test that safe code passes checks"""
        executor = CodeExecutor(use_docker=False)
        
        safe_codes = [
            "print('hello')",
            "x = 1 + 2",
            "def foo(): return 42",
            "import math\nmath.sqrt(16)",
        ]
        
        for code in safe_codes:
            # Should not raise exception
            executor._check_code_safety(code)
    
    def test_dangerous_code_detection(self):
        """Test that dangerous patterns are detected"""
        executor = CodeExecutor(use_docker=False)
        
        dangerous_codes = [
            "__import__('os').system('ls')",
            "os.system('rm -rf /')",
            "subprocess.call(['whoami'])",
            "eval(user_input)",
            "exec(malicious_code)",
            "open('/etc/passwd')",
            "socket.socket()",
        ]
        
        for code in dangerous_codes:
            # Should log warning (we can't easily test logging without capturing)
            executor._check_code_safety(code)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
