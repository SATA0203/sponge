# 🔌 Sponge 扩展库功能

## 概述

Sponge 扩展库是一个独立于系统架构的组件，提供模型、扩展、工具、技能的注册、管理和发现功能。任务可以在需要时动态连接扩展库并获取所需资源。

## 核心特性

- **独立架构**: 扩展库独立于主系统架构，可以单独部署和使用
- **动态加载**: 支持运行时动态注册和注销资源
- **分类管理**: 按类别组织模型、工具、技能等资源
- **智能匹配**: 根据查询自动匹配相关技能
- **API 接口**: 提供完整的 RESTful API 供前端调用

## 功能模块

### 1. 模型管理 (Models)

管理 LLM 模型信息，包括：
- 模型 ID、名称、提供商
- 模型能力（chat, completion, embedding 等）
- 最大 token 数限制
- 激活状态

**默认模型:**
- OpenAI GPT-4
- Anthropic Claude

### 2. 扩展管理 (Extensions)

管理系统扩展插件：
- 扩展版本和依赖
- 作者信息
- 激活状态

### 3. 工具管理 (Tools)

管理可用工具函数：
- 文件操作：读取、写入文件
- 代码执行：运行 Python 代码
- 代码分析：质量检查

**默认工具:**
- Read File (文件读取)
- Write File (文件写入)
- Execute Code (代码执行)

### 4. 技能管理 (Skills)

管理 Agent 技能：
- 技能分类（planning, coding, testing, review）
- 触发词匹配
- 优先级设置
- 智能匹配查询

**默认技能:**
- Task Planning (任务规划)
- Code Generation (代码生成)
- Testing (测试)
- Code Review (代码审查)

## API 接口

### 统计信息
```
GET /api/v1/extensions/statistics
```

### 模型接口
```
GET /api/v1/extensions/models              # 列出所有模型
GET /api/v1/extensions/models/{model_id}   # 获取指定模型
```

### 扩展接口
```
GET /api/v1/extensions/extensions              # 列出所有扩展
GET /api/v1/extensions/extensions/{extension_id} # 获取指定扩展
```

### 工具接口
```
GET /api/v1/extensions/tools              # 列出所有工具
GET /api/v1/extensions/tools/{tool_id}    # 获取指定工具
```

### 技能接口
```
GET /api/v1/extensions/skills              # 列出所有技能
GET /api/v1/extensions/skills/{skill_id}   # 获取指定技能
GET /api/v1/extensions/skills/match?query=xxx&top_k=5  # 匹配技能
```

## 前端界面

前端新增"扩展库"页面，包含：

1. **统计卡片**: 显示模型、扩展、工具、技能的数量
2. **选项卡展示**: 
   - 🤖 模型标签页
   - 🔧 扩展标签页
   - 🛠️ 工具标签页
   - 💡 技能标签页
3. **技能匹配测试**: 输入查询语句，实时匹配相关技能

## 使用示例

### Python 代码使用

```python
from app.extensions import get_extension_library

# 获取扩展库实例
lib = get_extension_library()

# 列出所有模型
models = lib.list_models()

# 列出所有工具
tools = lib.list_tools(category="code")

# 列出所有技能
skills = lib.list_skills(category="coding")

# 匹配技能
matched = lib.match_skills("我需要创建一个新函数", top_k=3)

# 调用工具
result = lib.call_tool("file-read", path="/path/to/file.py")
```

### API 调用示例

```bash
# 获取统计信息
curl http://localhost:8000/api/v1/extensions/statistics

# 获取模型列表
curl http://localhost:8000/api/v1/extensions/models

# 获取工具列表
curl http://localhost:8000/api/v1/extensions/tools

# 匹配技能
curl "http://localhost:8000/api/v1/extensions/skills/match?query=create%20function&top_k=3"
```

## 扩展开发

### 注册自定义工具

```python
from app.extensions import get_extension_library, ToolInfo

lib = get_extension_library()

# 定义工具信息
tool = ToolInfo(
    id="my-custom-tool",
    name="My Custom Tool",
    description="自定义工具描述",
    category="custom",
    parameters={"param1": {"type": "string", "required": True}},
    return_type="string",
)

# 定义工具函数
def my_tool_function(param1: str) -> str:
    return f"Result: {param1}"

# 注册工具
lib.register_tool(tool, func=my_tool_function)
```

### 注册自定义技能

```python
from app.extensions import get_extension_library, SkillInfo

lib = get_extension_library()

skill = SkillInfo(
    id="my-custom-skill",
    name="My Custom Skill",
    description="自定义技能描述",
    category="custom",
    triggers=["trigger1", "trigger2"],
    priority=5,
)

lib.register_skill(skill)
```

## 架构说明

```
┌─────────────────────────────────────────────────────┐
│                  Sponge System                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐     ┌──────────────────────┐     │
│  │   Agents     │────▶│  Extension Library   │     │
│  │  (Planner,   │     │  ┌────────────────┐  │     │
│  │   Coder,     │◀────│  │    Models      │  │     │
│  │  Reviewer,   │     │  ├────────────────┤  │     │
│  │   Tester)    │     │  │  Extensions    │  │     │
│  └──────────────┘     │  ├────────────────┤  │     │
│                       │  │    Tools       │  │     │
│  ┌──────────────┐     │  ├────────────────┤  │     │
│  │   Tasks      │────▶│  │    Skills      │  │     │
│  └──────────────┘     │  └────────────────┘  │     │
│                       └──────────────────────┘     │
│                              ▲                      │
└──────────────────────────────┼──────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │   Frontend (UI)     │
                    │  - 统计卡片          │
                    │  - 分类展示          │
                    │  - 技能匹配          │
                    └─────────────────────┘
```

## 注意事项

1. 扩展库采用单例模式，确保全局唯一实例
2. 工具和技能可以动态注册，无需重启服务
3. 技能匹配基于触发词和关键词相似度
4. 所有 API 接口支持 CORS 跨域访问
