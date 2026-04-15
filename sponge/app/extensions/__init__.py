"""
Sponge Extensions Library - 独立扩展库管理模块

提供模型、扩展、工具、技能的注册、管理和发现功能
扩展库独立于系统架构，任务可在需要时动态连接并获取资源
"""

from typing import Dict, List, Any, Optional, Callable
from pydantic import BaseModel, Field
from datetime import datetime
import importlib
import inspect


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    name: str
    provider: str  # openai, anthropic, local, etc.
    model_name: str
    description: str = ""
    capabilities: List[str] = []  # chat, completion, embedding, etc.
    max_tokens: int = 4096
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class ExtensionInfo(BaseModel):
    """扩展信息"""
    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    dependencies: List[str] = []
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class ToolInfo(BaseModel):
    """工具信息"""
    id: str
    name: str
    description: str = ""
    category: str = ""  # code, file, network, etc.
    parameters: Dict[str, Any] = {}
    return_type: str = "any"
    is_async: bool = False
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class SkillInfo(BaseModel):
    """技能信息"""
    id: str
    name: str
    description: str = ""
    category: str = ""  # planning, coding, testing, etc.
    triggers: List[str] = []  # keywords that trigger this skill
    priority: int = 1
    is_active: bool = True
    metadata: Dict[str, Any] = {}


class ExtensionLibrary:
    """
    扩展库管理器
    
    独立于系统架构的扩展库，提供：
    - 模型管理：LLM 模型注册和发现
    - 扩展管理：插件式扩展加载
    - 工具管理：可用工具注册和调用
    - 技能管理：Agent 技能注册和匹配
    """
    
    _instance: Optional["ExtensionLibrary"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._models: Dict[str, ModelInfo] = {}
            self._extensions: Dict[str, ExtensionInfo] = {}
            self._tools: Dict[str, ToolInfo] = {}
            self._tool_functions: Dict[str, Callable] = {}
            self._skills: Dict[str, SkillInfo] = {}
            self._skill_functions: Dict[str, Callable] = {}
            
            # 注册默认资源
            self._register_defaults()
    
    def _register_defaults(self):
        """注册默认资源"""
        # 默认模型
        self.register_model(ModelInfo(
            id="default-openai",
            name="OpenAI GPT-4",
            provider="openai",
            model_name="gpt-4",
            description="OpenAI GPT-4 模型",
            capabilities=["chat", "completion"],
            max_tokens=8192,
        ))
        
        self.register_model(ModelInfo(
            id="default-anthropic",
            name="Anthropic Claude",
            provider="anthropic",
            model_name="claude-3-sonnet-20240229",
            description="Anthropic Claude 3 Sonnet 模型",
            capabilities=["chat", "completion"],
            max_tokens=4096,
        ))
        
        # 默认工具
        from app.tools.file_tools import FileTools
        from app.tools.code_executor import CodeExecutor
        
        self.register_tool(ToolInfo(
            id="file-read",
            name="Read File",
            description="读取文件内容",
            category="file",
            parameters={"path": {"type": "string", "required": True}},
            return_type="string",
        ))
        self._tool_functions["file-read"] = getattr(FileTools, 'read_file', lambda **kwargs: None)
        
        self.register_tool(ToolInfo(
            id="file-write",
            name="Write File",
            description="写入文件内容",
            category="file",
            parameters={
                "path": {"type": "string", "required": True},
                "content": {"type": "string", "required": True}
            },
            return_type="boolean",
        ))
        self._tool_functions["file-write"] = getattr(FileTools, 'write_file', lambda **kwargs: None)
        
        self.register_tool(ToolInfo(
            id="code-execute",
            name="Execute Code",
            description="执行 Python 代码",
            category="code",
            parameters={
                "code": {"type": "string", "required": True},
                "language": {"type": "string", "default": "python"}
            },
            return_type="dict",
            is_async=True,
        ))
        self._tool_functions["code-execute"] = getattr(CodeExecutor, 'execute', lambda **kwargs: None)
        
        # 默认技能
        self.register_skill(SkillInfo(
            id="skill-planning",
            name="Task Planning",
            description="任务规划和分解技能",
            category="planning",
            triggers=["plan", "design", "architecture", "structure"],
            priority=10,
        ))
        
        self.register_skill(SkillInfo(
            id="skill-coding",
            name="Code Generation",
            description="代码生成技能",
            category="coding",
            triggers=["code", "implement", "function", "class", "module"],
            priority=10,
        ))
        
        self.register_skill(SkillInfo(
            id="skill-testing",
            name="Testing",
            description="测试用例生成和执行技能",
            category="testing",
            triggers=["test", "verify", "validate", "check"],
            priority=8,
        ))
        
        self.register_skill(SkillInfo(
            id="skill-review",
            name="Code Review",
            description="代码审查技能",
            category="review",
            triggers=["review", "audit", "quality", "improve"],
            priority=8,
        ))
    
    # ========== 模型管理 ==========
    
    def register_model(self, model: ModelInfo):
        """注册模型"""
        self._models[model.id] = model
    
    def unregister_model(self, model_id: str):
        """注销模型"""
        if model_id in self._models:
            del self._models[model_id]
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self._models.get(model_id)
    
    def list_models(self, provider: Optional[str] = None, active_only: bool = True) -> List[ModelInfo]:
        """列出模型"""
        models = list(self._models.values())
        if active_only:
            models = [m for m in models if m.is_active]
        if provider:
            models = [m for m in models if m.provider == provider]
        return models
    
    # ========== 扩展管理 ==========
    
    def register_extension(self, extension: ExtensionInfo):
        """注册扩展"""
        self._extensions[extension.id] = extension
    
    def unregister_extension(self, extension_id: str):
        """注销扩展"""
        if extension_id in self._extensions:
            del self._extensions[extension_id]
    
    def get_extension(self, extension_id: str) -> Optional[ExtensionInfo]:
        """获取扩展信息"""
        return self._extensions.get(extension_id)
    
    def list_extensions(self, active_only: bool = True) -> List[ExtensionInfo]:
        """列出扩展"""
        extensions = list(self._extensions.values())
        if active_only:
            extensions = [e for e in extensions if e.is_active]
        return extensions
    
    def load_extension(self, module_path: str) -> Optional[ExtensionInfo]:
        """动态加载扩展模块"""
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, "register"):
                ext_info = module.register(self)
                if ext_info:
                    self.register_extension(ext_info)
                    return ext_info
        except Exception as e:
            print(f"Failed to load extension {module_path}: {e}")
        return None
    
    # ========== 工具管理 ==========
    
    def register_tool(self, tool: ToolInfo, func: Optional[Callable] = None):
        """注册工具"""
        self._tools[tool.id] = tool
        if func:
            self._tool_functions[tool.id] = func
    
    def unregister_tool(self, tool_id: str):
        """注销工具"""
        if tool_id in self._tools:
            del self._tools[tool_id]
        if tool_id in self._tool_functions:
            del self._tool_functions[tool_id]
    
    def get_tool(self, tool_id: str) -> Optional[ToolInfo]:
        """获取工具信息"""
        return self._tools.get(tool_id)
    
    def list_tools(self, category: Optional[str] = None, active_only: bool = True) -> List[ToolInfo]:
        """列出工具"""
        tools = list(self._tools.values())
        if active_only:
            tools = [t for t in tools if t.is_active]
        if category:
            tools = [t for t in tools if t.category == category]
        return tools
    
    def call_tool(self, tool_id: str, **kwargs) -> Any:
        """调用工具函数"""
        if tool_id not in self._tool_functions:
            raise ValueError(f"Tool {tool_id} not found")
        func = self._tool_functions[tool_id]
        return func(**kwargs)
    
    async def call_tool_async(self, tool_id: str, **kwargs) -> Any:
        """异步调用工具函数"""
        if tool_id not in self._tool_functions:
            raise ValueError(f"Tool {tool_id} not found")
        func = self._tool_functions[tool_id]
        if inspect.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return func(**kwargs)
    
    # ========== 技能管理 ==========
    
    def register_skill(self, skill: SkillInfo, func: Optional[Callable] = None):
        """注册技能"""
        self._skills[skill.id] = skill
        if func:
            self._skill_functions[skill.id] = func
    
    def unregister_skill(self, skill_id: str):
        """注销技能"""
        if skill_id in self._skills:
            del self._skills[skill_id]
        if skill_id in self._skill_functions:
            del self._skill_functions[skill_id]
    
    def get_skill(self, skill_id: str) -> Optional[SkillInfo]:
        """获取技能信息"""
        return self._skills.get(skill_id)
    
    def list_skills(self, category: Optional[str] = None, active_only: bool = True) -> List[SkillInfo]:
        """列出技能"""
        skills = list(self._skills.values())
        if active_only:
            skills = [s for s in skills if s.is_active]
        if category:
            skills = [s for s in skills if s.category == category]
        return skills
    
    def match_skills(self, query: str, top_k: int = 5) -> List[SkillInfo]:
        """根据查询匹配技能"""
        query_lower = query.lower()
        matched = []
        
        for skill in self._skills.values():
            if not skill.is_active:
                continue
            
            score = 0
            # 检查触发词匹配
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 1
            
            # 检查名称和描述匹配
            if skill.name.lower() in query_lower:
                score += 2
            if any(word.lower() in query_lower for word in skill.description.lower().split()):
                score += 1
            
            if score > 0:
                matched.append((score * skill.priority, skill))
        
        # 按得分排序
        matched.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in matched[:top_k]]
    
    def get_skill_function(self, skill_id: str) -> Optional[Callable]:
        """获取技能函数"""
        return self._skill_functions.get(skill_id)
    
    # ========== 统计信息 ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取扩展库统计信息"""
        return {
            "models": {
                "total": len(self._models),
                "active": sum(1 for m in self._models.values() if m.is_active),
                "by_provider": self._count_by_field(self._models, "provider"),
            },
            "extensions": {
                "total": len(self._extensions),
                "active": sum(1 for e in self._extensions.values() if e.is_active),
            },
            "tools": {
                "total": len(self._tools),
                "active": sum(1 for t in self._tools.values() if t.is_active),
                "by_category": self._count_by_field(self._tools, "category"),
            },
            "skills": {
                "total": len(self._skills),
                "active": sum(1 for s in self._skills.values() if s.is_active),
                "by_category": self._count_by_field(self._skills, "category"),
            },
        }
    
    def _count_by_field(self, items: Dict, field: str) -> Dict[str, int]:
        """按字段统计"""
        counts = {}
        for item in items.values():
            value = getattr(item, field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts


# 全局实例
def get_extension_library() -> ExtensionLibrary:
    """获取扩展库实例"""
    return ExtensionLibrary()
