"""
Base Agent Module - Abstract base class for all agents
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from loguru import logger


class BaseAgent(ABC):
    """Abstract base class for all Sponge agents"""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        name: str,
        role: str,
        system_prompt: Optional[str] = None,
    ):
        """
        Initialize base agent
        
        Args:
            llm: Language model instance
            name: Agent name
            role: Agent role description
            system_prompt: Optional system prompt override
        """
        self.llm = llm
        self.name = name
        self.role = role
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.message_history: List[Any] = []
        
        logger.info(f"Initialized agent: {name} ({role})")
    
    @abstractmethod
    def _default_system_prompt(self) -> str:
        """Return default system prompt for this agent type"""
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent's main logic
        
        Args:
            input_data: Input data for the agent
            
        Returns:
            Dictionary containing agent's output
        """
        pass
    
    async def _invoke_llm(self, messages: List[Any]) -> str:
        """
        Invoke LLM with messages and retry logic
        
        Args:
            messages: List of messages to send to LLM
            
        Returns:
            LLM response as string
        """
        from app.core.llm_service import invoke_llm_with_retry
        
        try:
            # Use retry wrapper for better fault tolerance
            response = await invoke_llm_with_retry(self.llm, messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM invocation failed for {self.name} after retries: {e}")
            raise
    
    def _build_messages(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """
        Build message list for LLM
        
        Args:
            user_input: User's input text
            context: Optional context dictionary
            
        Returns:
            List of messages for LLM
        """
        messages = [SystemMessage(content=self.system_prompt)]
        
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            messages.append(HumanMessage(content=f"Context:\n{context_str}\n\nTask: {user_input}"))
        else:
            messages.append(HumanMessage(content=user_input))
        
        return messages
    
    def clear_history(self):
        """Clear agent's message history"""
        self.message_history = []
        logger.debug(f"Cleared message history for {self.name}")
