"""
扩展库 API 路由

提供模型、扩展、工具、技能的查询和管理接口
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional

from app.extensions import get_extension_library, ModelInfo, ExtensionInfo, ToolInfo, SkillInfo

router = APIRouter(prefix="/api/v1/extensions", tags=["extensions"])


@router.get("/statistics")
async def get_statistics():
    """获取扩展库统计信息"""
    library = get_extension_library()
    return library.get_statistics()


# ========== 模型管理 ==========

@router.get("/models", response_model=List[ModelInfo])
async def list_models(
    provider: Optional[str] = None,
    active_only: bool = True,
):
    """列出所有可用模型"""
    library = get_extension_library()
    return library.list_models(provider=provider, active_only=active_only)


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """获取指定模型信息"""
    library = get_extension_library()
    model = library.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    return model


# ========== 扩展管理 ==========

@router.get("/extensions", response_model=List[ExtensionInfo])
async def list_extensions(active_only: bool = True):
    """列出所有已加载的扩展"""
    library = get_extension_library()
    return library.list_extensions(active_only=active_only)


@router.get("/extensions/{extension_id}", response_model=ExtensionInfo)
async def get_extension(extension_id: str):
    """获取指定扩展信息"""
    library = get_extension_library()
    extension = library.get_extension(extension_id)
    if not extension:
        raise HTTPException(status_code=404, detail=f"Extension {extension_id} not found")
    return extension


# ========== 工具管理 ==========

@router.get("/tools", response_model=List[ToolInfo])
async def list_tools(
    category: Optional[str] = None,
    active_only: bool = True,
):
    """列出所有可用工具"""
    library = get_extension_library()
    return library.list_tools(category=category, active_only=active_only)


@router.get("/tools/{tool_id}", response_model=ToolInfo)
async def get_tool(tool_id: str):
    """获取指定工具信息"""
    library = get_extension_library()
    tool = library.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    return tool


# ========== 技能管理 ==========

@router.get("/skills", response_model=List[SkillInfo])
async def list_skills(
    category: Optional[str] = None,
    active_only: bool = True,
):
    """列出所有可用技能"""
    library = get_extension_library()
    return library.list_skills(category=category, active_only=active_only)


@router.get("/skills/{skill_id}", response_model=SkillInfo)
async def get_skill(skill_id: str):
    """获取指定技能信息"""
    library = get_extension_library()
    skill = library.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")
    return skill


@router.get("/skills/match")
async def match_skills(query: str, top_k: int = 5):
    """根据查询匹配相关技能"""
    library = get_extension_library()
    return library.match_skills(query, top_k=top_k)
