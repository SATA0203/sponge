"""
Agent Factory Module - Dynamic agent creation and management

Supports:
- Factory pattern for creating agents
- Agent registration and discovery
- Configuration-based agent instantiation
- Agent pooling for better resource utilization
"""

from typing import Dict, Type, Optional, Any, List
from dataclasses import dataclass, field
from enum import Enum
import importlib
from loguru import logger

from app.agents.base_agent import BaseAgent
from app.core.llm_service_pool import get_llm_service


class AgentType(str, Enum):
    """Enumeration of available agent types"""
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"
    EXECUTOR = "executor"


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    agent_type: AgentType
    name: str
    role: str
    system_prompt: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    pool_size: int = 3
    custom_params: Dict[str, Any] = field(default_factory=dict)


class AgentFactory:
    """Factory for creating and managing agent instances"""
    
    _instance: Optional["AgentFactory"] = None
    _agent_classes: Dict[AgentType, Type[BaseAgent]] = {}
    _agent_configs: Dict[str, AgentConfig] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._agent_pools: Dict[str, List[BaseAgent]] = {}
            self._llm_service = get_llm_service()
            logger.info("Initialized AgentFactory")
    
    @classmethod
    def register_agent(cls, agent_type: AgentType, agent_class: Type[BaseAgent]):
        """Register an agent class with the factory"""
        cls._agent_classes[agent_type] = agent_class
        logger.info(f"Registered agent class: {agent_type.value} -> {agent_class.__name__}")
    
    def register_config(self, config_id: str, config: AgentConfig):
        """Register an agent configuration"""
        self._agent_configs[config_id] = config
        logger.info(f"Registered agent config: {config_id} ({config.agent_type.value})")
        
        # Initialize agent pool for this config
        self._agent_pools[config_id] = []
    
    async def create_agent(
        self,
        agent_type: AgentType,
        name: Optional[str] = None,
        role: Optional[str] = None,
        system_prompt: Optional[str] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        config_id: Optional[str] = None,
        **kwargs,
    ) -> BaseAgent:
        """
        Create a new agent instance
        
        Args:
            agent_type: Type of agent to create
            name: Agent name (default from config or type)
            role: Agent role description
            system_prompt: Custom system prompt
            llm_provider: LLM provider to use
            llm_model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            config_id: Pre-configured agent config ID
            **kwargs: Additional parameters passed to agent constructor
            
        Returns:
            Configured agent instance
        """
        # Use config if provided
        if config_id and config_id in self._agent_configs:
            config = self._agent_configs[config_id]
            agent_type = config.agent_type
            name = name or config.name
            role = role or config.role
            system_prompt = system_prompt or config.system_prompt
            llm_provider = llm_provider or config.llm_provider
            llm_model = llm_model or config.llm_model
            temperature = temperature or config.temperature
            max_tokens = max_tokens or config.max_tokens
            kwargs.update(config.custom_params)
        
        # Get agent class
        if agent_type not in self._agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent_class = self._agent_classes[agent_type]
        
        # Set defaults
        name = name or agent_type.value.capitalize()
        role = role or f"{agent_type.value} agent"
        
        # Get LLM instance
        llm, pool_key = await self._llm_service.get_llm(
            provider=llm_provider,
            model_name=llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        logger.info(f"Creating agent: {name} ({agent_type.value}) with LLM {llm_provider}/{llm_model}")
        
        # Create agent instance
        try:
            agent = agent_class(
                llm=llm,
                name=name,
                role=role,
                system_prompt=system_prompt,
                **kwargs,
            )
            
            # Store pool key for later release
            agent._llm_pool_key = pool_key
            
            return agent
            
        except Exception as e:
            logger.error(f"Failed to create agent {name}: {e}")
            # Release LLM back to pool
            await self._llm_service.release_llm(llm, pool_key)
            raise
    
    async def create_agent_from_config(self, config_id: str, **overrides) -> BaseAgent:
        """Create an agent from a registered configuration with optional overrides"""
        if config_id not in self._agent_configs:
            raise ValueError(f"Unknown agent config: {config_id}")
        
        config = self._agent_configs[config_id]
        
        # Apply overrides
        params = {
            "agent_type": config.agent_type,
            "name": config.name,
            "role": config.role,
            "system_prompt": config.system_prompt,
            "llm_provider": config.llm_provider,
            "llm_model": config.llm_model,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        params.update(config.custom_params)
        params.update(overrides)
        
        return await self.create_agent(**params)
    
    async def acquire_from_pool(self, config_id: str) -> BaseAgent:
        """Acquire an agent from the pool"""
        if config_id not in self._agent_pools:
            logger.warning(f"No pool found for config {config_id}, creating new agent")
            return await self.create_agent_from_config(config_id)
        
        pool = self._agent_pools[config_id]
        
        if pool:
            agent = pool.pop()
            logger.debug(f"Acquired agent from pool {config_id} (remaining: {len(pool)})")
            return agent
        else:
            logger.debug(f"Pool {config_id} empty, creating new agent")
            return await self.create_agent_from_config(config_id)
    
    async def release_to_pool(self, config_id: str, agent: BaseAgent):
        """Release an agent back to the pool"""
        if config_id not in self._agent_pools:
            self._agent_pools[config_id] = []
        
        pool = self._agent_pools[config_id]
        config = self._agent_configs.get(config_id)
        
        # Only reuse if pool size limit not reached
        if config and len(pool) < config.pool_size:
            # Clear agent history before reusing
            agent.clear_history()
            pool.append(agent)
            logger.debug(f"Released agent to pool {config_id} (size: {len(pool)}/{config.pool_size})")
        else:
            logger.debug(f"Pool {config_id} full or no config, not reusing agent")
            # Cleanup LLM if not reusing
            if hasattr(agent, '_llm_pool_key'):
                await self._llm_service.release_llm(agent.llm, agent._llm_pool_key)
    
    async def close_all(self):
        """Close all agent pools and release resources"""
        logger.info("Closing all agent pools...")
        
        for config_id, pool in self._agent_pools.items():
            for agent in pool:
                if hasattr(agent, '_llm_pool_key'):
                    await self._llm_service.release_llm(agent.llm, agent._llm_pool_key)
            pool.clear()
            logger.info(f"Cleared pool: {config_id}")
        
        self._agent_pools.clear()
        logger.info("All agent pools closed")


# Global factory instance
_agent_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """Get or create the global agent factory instance"""
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory()
    return _agent_factory


# Convenience functions
async def create_agent(agent_type: AgentType, **kwargs) -> BaseAgent:
    """Create a new agent instance"""
    factory = get_agent_factory()
    return await factory.create_agent(agent_type, **kwargs)


async def create_agent_from_config(config_id: str, **overrides) -> BaseAgent:
    """Create an agent from a registered configuration"""
    factory = get_agent_factory()
    return await factory.create_agent_from_config(config_id, **overrides)
