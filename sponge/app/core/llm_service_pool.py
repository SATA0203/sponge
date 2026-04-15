"""
LLM Service with Connection Pooling and Load Balancing

Enhanced LLM service supporting:
- Connection pooling for better concurrency
- Multiple LLM configurations with dynamic switching
- Request queuing and rate limiting
- Automatic fallback and retry logic
- Performance metrics and monitoring
"""

from typing import Optional, Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import FakeListLLM
from loguru import logger
import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import threading

from app.core.config import settings


@dataclass
class LLMConfig:
    """Configuration for an LLM instance"""
    provider: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    api_key: Optional[str] = None
    request_timeout: int = 60
    max_retries: int = 3
    rate_limit_per_minute: int = 60


@dataclass
class LLMStats:
    """Statistics for an LLM instance"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_latency_ms: float = 0.0
    last_request_time: Optional[datetime] = None
    rate_limit_hits: int = 0
    
    @property
    def avg_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency_ms / self.total_requests
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests


class LLMConnectionPool:
    """Connection pool for LLM instances"""
    
    def __init__(self, config: LLMConfig, pool_size: int = 5):
        self.config = config
        self.pool_size = pool_size
        self._pool: List[Any] = []
        self._available: asyncio.Queue = asyncio.Queue()
        self._stats = LLMStats()
        self._lock = threading.Lock()
        self._initialized = False
        
    async def initialize(self):
        """Initialize the connection pool"""
        if self._initialized:
            return
            
        logger.info(f"Initializing LLM pool for {self.config.provider}/{self.config.model_name} (size={self.pool_size})")
        
        for i in range(self.pool_size):
            llm = self._create_llm()
            self._pool.append(llm)
            await self._available.put(llm)
            
        self._initialized = True
        logger.info(f"LLM pool initialized with {self.pool_size} connections")
    
    def _create_llm(self) -> Any:
        """Create a new LLM instance"""
        provider = self.config.provider.lower()
        
        if provider == "mock":
            return FakeListLLM(responses=[
                '{"summary": "Auto-generated plan", "steps": [{"step_number": 1, "description": "Implement the solution", "agent": "coder", "status": "pending", "estimated_complexity": "medium"}]}',
                '{"code": "print(\\"Hello, World!\\")", "language": "python", "explanation": "Simple hello world program"}',
                '{"passed": true, "score": 8, "feedback": "Code looks good", "suggestions": []}',
            ])
        
        elif provider == "openai":
            return ChatOpenAI(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=self.config.api_key or settings.OPENAI_API_KEY,
                request_timeout=self.config.request_timeout,
                max_retries=self.config.max_retries,
            )
        
        elif provider == "anthropic":
            return ChatAnthropic(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=self.config.api_key or settings.ANTHROPIC_API_KEY,
                timeout=self.config.request_timeout,
                max_retries=self.config.max_retries,
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    async def acquire(self) -> Any:
        """Acquire an LLM instance from the pool"""
        if not self._initialized:
            await self.initialize()
        
        try:
            llm = await asyncio.wait_for(self._available.get(), timeout=30.0)
            logger.debug(f"Acquired LLM from pool (available: {self._available.qsize()})")
            return llm
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for LLM from pool, creating new instance")
            return self._create_llm()
    
    async def release(self, llm: Any):
        """Release an LLM instance back to the pool"""
        if llm in self._pool:
            await self._available.put(llm)
            logger.debug(f"Released LLM to pool (available: {self._available.qsize()})")
    
    def record_request(self, latency_ms: float, success: bool):
        """Record request statistics"""
        with self._lock:
            self._stats.total_requests += 1
            self._stats.total_latency_ms += latency_ms
            self._stats.last_request_time = datetime.utcnow()
            
            if success:
                self._stats.successful_requests += 1
            else:
                self._stats.failed_requests += 1
    
    def get_stats(self) -> LLMStats:
        """Get current statistics"""
        return self._stats


class RateLimiter:
    """Rate limiter for LLM requests"""
    
    def __init__(self, rate_per_minute: int):
        self.rate_per_minute = rate_per_minute
        self.requests: List[float] = []
        self._lock = threading.Lock()
    
    async def acquire(self):
        """Wait until rate limit allows"""
        while True:
            with self._lock:
                now = time.time()
                # Remove requests older than 1 minute
                self.requests = [t for t in self.requests if now - t < 60]
                
                if len(self.requests) < self.rate_per_minute:
                    self.requests.append(now)
                    return
            
            # Wait and retry
            await asyncio.sleep(0.1)


class EnhancedLLMService:
    """Enhanced LLM service with connection pooling and load balancing"""
    
    _instance: Optional["EnhancedLLMService"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._pools: Dict[str, LLMConnectionPool] = {}
            self._rate_limiters: Dict[str, RateLimiter] = {}
            self._default_config: Optional[LLMConfig] = None
            self._global_stats: Dict[str, LLMStats] = defaultdict(LLMStats)
            logger.info("Initialized EnhancedLLMService")
    
    def configure_default(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        pool_size: int = 5,
        rate_limit_per_minute: int = 60,
    ):
        """Configure default LLM settings"""
        provider = provider or settings.LLM_PROVIDER
        model_name = model_name or settings.MODEL_NAME
        temperature = temperature or settings.TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        api_key = None
        if provider.lower() == "openai":
            api_key = settings.OPENAI_API_KEY
        elif provider.lower() == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
        
        self._default_config = LLMConfig(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        
        # Create default pool
        pool_key = f"{provider}/{model_name}"
        self._pools[pool_key] = LLMConnectionPool(self._default_config, pool_size=pool_size)
        self._rate_limiters[pool_key] = RateLimiter(rate_limit_per_minute)
        
        logger.info(f"Configured default LLM: {pool_key} (pool_size={pool_size})")
    
    def add_llm_config(
        self,
        config_id: str,
        provider: str,
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        api_key: Optional[str] = None,
        pool_size: int = 5,
        rate_limit_per_minute: int = 60,
    ):
        """Add a new LLM configuration"""
        config = LLMConfig(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=api_key,
            rate_limit_per_minute=rate_limit_per_minute,
        )
        
        self._pools[config_id] = LLMConnectionPool(config, pool_size=pool_size)
        self._rate_limiters[config_id] = RateLimiter(rate_limit_per_minute)
        
        logger.info(f"Added LLM config: {config_id} ({provider}/{model_name})")
    
    async def get_llm(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        config_id: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Get an LLM instance from the pool
        
        Args:
            provider: LLM provider (openai, anthropic, mock)
            model_name: Model name to use
            config_id: Pre-configured LLM config ID
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Configured LLM instance
        """
        # Use config_id if provided
        if config_id and config_id in self._pools:
            pool_key = config_id
        else:
            # Build pool key from parameters
            provider = provider or (self._default_config.provider if self._default_config else settings.LLM_PROVIDER)
            model_name = model_name or (self._default_config.model_name if self._default_config else settings.MODEL_NAME)
            pool_key = f"{provider}/{model_name}"
            
            # Create pool if it doesn't exist
            if pool_key not in self._pools:
                api_key = None
                if provider.lower() == "openai":
                    api_key = settings.OPENAI_API_KEY
                elif provider.lower() == "anthropic":
                    api_key = settings.ANTHROPIC_API_KEY
                
                config = LLMConfig(
                    provider=provider,
                    model_name=model_name,
                    temperature=temperature or settings.TEMPERATURE,
                    max_tokens=max_tokens or settings.MAX_TOKENS,
                    api_key=api_key,
                )
                
                self._pools[pool_key] = LLMConnectionPool(config)
                self._rate_limiters[pool_key] = RateLimiter(config.rate_limit_per_minute)
                logger.info(f"Created dynamic LLM pool: {pool_key}")
        
        # Apply rate limiting
        if pool_key in self._rate_limiters:
            await self._rate_limiters[pool_key].acquire()
        
        # Acquire from pool
        llm = await self._pools[pool_key].acquire()
        return llm, pool_key
    
    async def release_llm(self, llm: Any, pool_key: str):
        """Release an LLM instance back to the pool"""
        if pool_key in self._pools:
            await self._pools[pool_key].release(llm)
    
    def record_metrics(self, pool_key: str, latency_ms: float, success: bool):
        """Record request metrics"""
        if pool_key in self._pools:
            self._pools[pool_key].record_request(latency_ms, success)
    
    def get_stats(self, pool_key: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for LLM pools"""
        if pool_key and pool_key in self._pools:
            stats = self._pools[pool_key].get_stats()
            return {
                "pool_key": pool_key,
                "total_requests": stats.total_requests,
                "successful_requests": stats.successful_requests,
                "failed_requests": stats.failed_requests,
                "avg_latency_ms": stats.avg_latency_ms,
                "success_rate": stats.success_rate,
                "last_request_time": stats.last_request_time,
            }
        else:
            return {
                pool_key: {
                    "total_requests": pool.get_stats().total_requests,
                    "successful_requests": pool.get_stats().successful_requests,
                    "failed_requests": pool.get_stats().failed_requests,
                    "avg_latency_ms": pool.get_stats().avg_latency_ms,
                    "success_rate": pool.get_stats().success_rate,
                }
                for pool_key, pool in self._pools.items()
            }
    
    async def close_all(self):
        """Close all connection pools"""
        logger.info("Closing all LLM connection pools...")
        for pool_key, pool in self._pools.items():
            logger.info(f"Closing pool: {pool_key}")
        self._pools.clear()
        self._rate_limiters.clear()
        logger.info("All LLM pools closed")


# Convenience functions
_llm_service: Optional[EnhancedLLMService] = None


def get_llm_service() -> EnhancedLLMService:
    """Get or create the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = EnhancedLLMService()
    return _llm_service


async def get_llm(**kwargs):
    """Get an LLM instance from the service"""
    service = get_llm_service()
    return await service.get_llm(**kwargs)


async def release_llm(llm: Any, pool_key: str):
    """Release an LLM instance back to the pool"""
    service = get_llm_service()
    await service.release_llm(llm, pool_key)
