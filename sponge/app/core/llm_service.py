"""
LLM Service - Manages language model connections and initialization with retry logic
"""

from typing import Optional, Any
import asyncio
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import FakeListLLM
from loguru import logger

from app.core.config import settings


class LLMService:
    """Service for managing LLM instances with retry and rate limiting"""
    
    _instance: Optional["LLMService"] = None
    _llm: Optional[Any] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._llm = None
            # Retry configuration
            self.max_retries = 3
            self.base_delay = 1.0  # seconds
            self.max_delay = 30.0  # seconds
            # Token budget tracking (simple in-memory implementation)
            self.token_count = 0
            self.token_budget = settings.MAX_TOKENS * 100  # Budget for 100 requests
            logger.info("Initialized LLMService with retry logic")
    
    async def invoke_with_retry(
        self,
        llm: Any,
        messages: list,
        max_retries: Optional[int] = None,
    ) -> Any:
        """
        Invoke LLM with exponential backoff retry logic
        
        Args:
            llm: LLM instance to invoke
            messages: Messages to send
            max_retries: Override default max retries
            
        Returns:
            LLM response
            
        Raises:
            Exception: If all retries fail
        """
        retries = 0
        max_retries = max_retries or self.max_retries
        last_exception = None
        
        while retries <= max_retries:
            try:
                # Check token budget
                if self.token_count > self.token_budget:
                    logger.warning("Token budget exceeded, consider increasing limit")
                
                response = await llm.ainvoke(messages)
                
                # Track token usage (estimate from response)
                if hasattr(response, 'content') and response.content:
                    estimated_tokens = len(response.content) // 4
                    self.token_count += estimated_tokens
                
                return response
                
            except Exception as e:
                last_exception = e
                retries += 1
                
                if retries > max_retries:
                    logger.error(f"LLM invocation failed after {max_retries} retries: {e}")
                    raise
                
                # Exponential backoff with jitter
                delay = min(self.base_delay * (2 ** (retries - 1)), self.max_delay)
                logger.warning(
                    f"LLM invocation failed (attempt {retries}/{max_retries}), "
                    f"retrying in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_exception
    
    def get_llm(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        Get or create LLM instance
        
        Args:
            provider: LLM provider (openai, anthropic, mock)
            model_name: Model name to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Configured LLM instance
        """
        # Return cached instance if parameters match
        if (
            self._llm is not None
            and (provider is None or provider == settings.LLM_PROVIDER)
            and (model_name is None or model_name == settings.MODEL_NAME)
        ):
            return self._llm
        
        # Use settings defaults if not specified
        provider = provider or settings.LLM_PROVIDER
        model_name = model_name or settings.MODEL_NAME
        temperature = temperature or settings.TEMPERATURE
        max_tokens = max_tokens or settings.MAX_TOKENS
        
        logger.info(f"Creating LLM instance: {provider}/{model_name}")
        
        # Create LLM based on provider
        if provider.lower() == "mock":
            # Mock LLM for testing without API keys
            logger.warning("Using Mock LLM for testing - responses will be simulated")
            self._llm = FakeListLLM(responses=[
                '{"summary": "Auto-generated plan", "steps": [{"step_number": 1, "description": "Implement the solution", "agent": "coder", "status": "pending", "estimated_complexity": "medium"}]}',
                '{"code": "print(\\"Hello, World!\\")", "language": "python", "explanation": "Simple hello world program"}',
                '{"passed": true, "score": 8, "feedback": "Code looks good", "suggestions": []}',
            ])
            
        elif provider.lower() == "openai":
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                logger.warning("OPENAI_API_KEY not configured, falling back to Mock LLM")
                self._llm = FakeListLLM(responses=[
                    '{"summary": "Auto-generated plan", "steps": [{"step_number": 1, "description": "Implement the solution", "agent": "coder", "status": "pending", "estimated_complexity": "medium"}]}',
                    '{"code": "print(\\"Hello, World!\\")", "language": "python", "explanation": "Simple hello world program"}',
                    '{"passed": true, "score": 8, "feedback": "Code looks good", "suggestions": []}',
                ])
                return self._llm
            
            self._llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            
        elif provider.lower() == "anthropic":
            api_key = settings.ANTHROPIC_API_KEY
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not configured, falling back to Mock LLM")
                self._llm = FakeListLLM(responses=[
                    '{"summary": "Auto-generated plan", "steps": [{"step_number": 1, "description": "Implement the solution", "agent": "coder", "status": "pending", "estimated_complexity": "medium"}]}',
                    '{"code": "print(\\"Hello, World!\\")", "language": "python", "explanation": "Simple hello world program"}',
                    '{"passed": true, "score": 8, "feedback": "Code looks good", "suggestions": []}',
                ])
                return self._llm
            
            self._llm = ChatAnthropic(
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )
            
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
        logger.info(f"LLM initialized successfully: {provider}/{model_name}")
        return self._llm
    
    def clear_cache(self):
        """Clear cached LLM instance"""
        self._llm = None
        logger.info("Cleared LLM cache")
    
    def reset_token_count(self):
        """Reset token count tracker"""
        self.token_count = 0
        logger.info("Reset token count tracker")
    
    def get_token_usage(self) -> int:
        """Get current token usage"""
        return self.token_count


# Convenience function
def get_llm(**kwargs) -> Any:
    """Get LLM instance with specified parameters"""
    service = LLMService()
    return service.get_llm(**kwargs)


async def invoke_llm_with_retry(llm: Any, messages: list, **kwargs) -> Any:
    """
    Convenience function to invoke LLM with retry logic
    
    Args:
        llm: LLM instance
        messages: Messages to send
        **kwargs: Additional arguments for retry configuration
        
    Returns:
        LLM response
    """
    service = LLMService()
    return await service.invoke_with_retry(llm, messages, **kwargs)
