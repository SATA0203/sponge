# Sponge 开发准备指南

在正式开始编写代码之前，请仔细阅读并完成以下准备工作。这将确保开发过程顺畅，减少环境配置问题和架构理解偏差。

## 1. 核心概念与架构理解

在动手之前，必须理解 **Sponge** 的核心设计理念：

- **多 Agent 协作**：系统不是单个大模型，而是由规划、编码、审查、测试等多个专用 Agent 组成的协作网络。
- **状态驱动工作流**：所有操作基于共享状态（State），通过 LangGraph 进行状态流转和控制。
- **沙箱执行**：所有生成的代码必须在隔离的沙箱环境中运行，确保宿主机安全。
- **异步任务队列**：支持多个任务并行处理，通过消息队列解耦请求与执行。

**推荐阅读顺序**：
1. `README.md` - 了解项目宏观目标
2. `PRD_Sponge.md` - 熟悉功能需求与边界
3. `多Agent协作开发文档.md` - 理解节点交互逻辑

## 2. 环境准备清单

### 2.1 基础环境
- **Python**: >= 3.10 (推荐使用 3.11)
- **Node.js**: >= 18.0 (用于部分前端工具或 JS 沙箱)
- **Docker**: 必须安装，用于代码沙箱隔离
- **Git**: 版本控制

### 2.2 依赖安装
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装核心依赖
pip install -r requirements.txt

# 安装开发工具
pip install -r requirements-dev.txt
```

### 2.3 环境变量配置
在项目根目录创建 `.env` 文件，参考 `.env.example` 填充以下内容：

```ini
# LLM 配置
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o

# 沙箱配置
SANDBOX_TYPE=docker  # 可选: docker, local(仅调试用)
DOCKER_NETWORK=sponge_net

# 数据库配置 (状态持久化)
DATABASE_URL=sqlite+aiosqlite:///./sponge.db
# 生产环境建议使用: postgresql+asyncpg://user:pass@localhost/sponge

# Redis (任务队列与缓存)
REDIS_URL=redis://localhost:6379/0

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/sponge.log
```

## 3. 本地服务启动

开发前需确保以下基础设施服务正在运行：

### 3.1 启动 Redis
```bash
# 使用 Docker 启动
docker run -d -p 6379:6379 --name sponge-redis redis:latest
```

### 3.2 启动数据库
```bash
# 如果使用 SQLite (开发默认)，无需额外启动
# 如果使用 PostgreSQL:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=sponge --name sponge-db postgres:15
```

### 3.3 初始化数据库表结构
```bash
# 运行迁移脚本
python scripts/init_db.py
```

## 4. 开发规范约定

### 4.1 代码风格
- 遵循 **PEP 8** 规范
- 类型注解：所有函数必须包含 Type Hints
- 格式化：使用 `black` 和 `isort`
  ```bash
  black src/ tests/
  isort src/ tests/
  ```

### 4.2 提交规范
采用 Conventional Commits 格式：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档变更
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具链

示例：
```bash
git commit -m "feat(agent): 实现代码审查 Agent 的基础逻辑"
```

### 4.3 分支策略
- `main`: 主分支，仅允许合并经过测试的稳定代码
- `develop`: 开发主分支
- `feature/xxx`: 功能开发分支 (从 develop 检出)
- `fix/xxx`: 修复分支

## 5. 验证环境就绪

运行以下命令验证环境是否配置正确：

```bash
# 1. 运行单元测试
pytest tests/unit -v

# 2. 运行健康检查脚本
python scripts/health_check.py

# 3. 尝试启动服务
uvicorn src.api.main:app --reload
```

如果所有检查通过，你将看到 API 文档可用 (http://localhost:8000/docs)。

## 6. 第一个开发任务建议

如果你是第一次参与开发，建议按以下顺序入手：

1. **阅读测试用例**：查看 `tests/unit/test_planner.py` 了解 Agent 如何被调用。
2. **运行一个简单任务**：通过 API 创建一个 "Hello World" 生成任务，观察日志中的状态流转。
3. **修改一个小功能**：例如调整 Prompt 模板，观察输出变化。
4. **添加一个新工具**：参考 `src/tools/file_ops.py`，尝试添加一个简单的 `list_directory` 工具。

## 7. 常见问题排查

- **Docker 权限问题**：确保当前用户在 docker 用户组中。
- **LLM 连接失败**：检查 `.env` 中的 API Key 和 Base URL 是否正确。
- **数据库锁定**：如果使用 SQLite 遇到锁定，删除 `sponge.db` 重新初始化。
- **依赖冲突**：始终在虚拟环境中安装依赖。

---

**准备就绪后，请前往 `src/` 目录开始你的开发工作！**
