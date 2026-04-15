"""
Sponge - Multi-Agent Collaborative Code Development System

## Overview

**Sponge** is an intelligent code development system that leverages multiple AI agents working collaboratively to analyze requirements, write code, review implementations, run tests, and deploy applications.

## Key Features

- 🤖 **Multi-Agent Collaboration**: Specialized agents for planning, coding, reviewing, testing, and deployment
- 🔄 **Automated Workflows**: LangGraph-powered state machines for complex task orchestration
- 🛡️ **Secure Execution**: Docker-based sandbox for safe code execution
- ⚡ **Async Processing**: Celery-based task queue for parallel agent operations
- 📊 **Real-time Monitoring**: Comprehensive logging and status tracking
- 🔌 **Extensible Architecture**: Easy to add new agents, tools, and workflows

## Quick Start

### 🚀 快速部署 (推荐)

**方式一：Docker 一键启动**

```bash
cd /workspace/sponge

# 配置环境变量
cp docker/.env.example .env
# 编辑 .env，设置 LLM_API_KEY

# 启动所有服务
docker-compose -f docker/docker-compose.yml up -d

# 访问前端界面
open http://localhost:8501
```

**方式二：本地开发部署**

详见 [QUICKSTART.md](QUICKSTART.md)

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Redis (for Celery)

# Start infrastructure services
docker-compose up -d postgres redis

# Run API server
uvicorn app.main:app --reload

# Run Celery worker
celery -A app.celery_app worker --loglevel=info
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
└────────────────────┬────────────────────────────────┘
                     │ REST API / WebSocket
┌────────────────────▼────────────────────────────────┐
│                  FastAPI Server                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Tasks   │  │  Files   │  │  Health  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Celery Task Queue                      │
│         (Async Agent Coordination)                   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              LangGraph Workflow Engine               │
│  ┌──────────────────────────────────────────────┐   │
│  │  Planner → Coder → Reviewer → Tester        │   │
│  │       ↑                              ↓       │   │
│  │       └────────── Iteration ──────────┘      │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                Tools & Sandboxes                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Files   │  │  Code    │  │  Docker  │          │
│  │  Tools   │  │ Executor │  │ Sandbox │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
sponge/
├── app/
│   ├── main.py              # FastAPI application
│   ├── celery_app.py        # Celery configuration
│   ├── core/                # Core settings & config
│   ├── schemas/             # Pydantic models
│   ├── agents/              # Agent implementations
│   ├── tools/               # Utility tools
│   ├── workflow/            # LangGraph workflows
│   └── api/                 # API routers
├── tests/                   # Test suite
├── docker-compose.yml       # Service orchestration
├── requirements.txt         # Python dependencies
└── DEVELOPMENT.md           # Development guide
```

## API Endpoints

### Tasks
- `POST /api/v1/tasks/` - Create new task
- `GET /api/v1/tasks/` - List tasks
- `GET /api/v1/tasks/{id}` - Get task details
- `POST /api/v1/tasks/{id}/cancel` - Cancel task
- `DELETE /api/v1/tasks/{id}` - Delete task

### Files
- `GET /api/v1/files/` - List files
- `GET /api/v1/files/content` - Get file content
- `POST /api/v1/files/update` - Update file
- `GET /api/v1/files/exists` - Check file exists

### Health
- `GET /health/` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Documentation

### Quick Start
- [Getting Started](GET_STARTED.md) - Environment setup and installation
- [Development Guide](DEVELOPMENT.md) - Development workflow and best practices

### Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete REST API documentation
- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [Multi-Agent Guide](docs/MULTI_AGENT_GUIDE.md) - Agent collaboration details
- [Documentation Index](docs/README.md) - Navigate all documentation

### Project Documents
- [PRD](PRD_SpongeCodeAgent.md) - Product requirements document
- [Progress](PROGRESS.md) - Current development status

## Technology Stack

- **Backend**: FastAPI, Python 3.11
- **Workflow**: LangGraph, LangChain
- **Task Queue**: Celery, Redis
- **Database**: PostgreSQL
- **Sandbox**: Docker
- **LLM**: OpenAI GPT-4, Anthropic Claude

## Roadmap

### Phase 1 (MVP) - Current
- [x] Project scaffolding
- [x] Core configuration
- [x] API structure
- [x] File tools
- [ ] Agent implementations
- [ ] Workflow engine
- [ ] Code executor

### Phase 2
- [ ] Database integration
- [ ] Advanced code analysis
- [ ] Test generation
- [ ] CI/CD integration

### Phase 3
- [ ] Web UI
- [ ] Plugin system
- [ ] Multi-language support
- [ ] Team collaboration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: Report bugs and feature requests
- Documentation: Check DEVELOPMENT.md and other docs

---

**Sponge** - Absorbing complexity, expelling code.

## 📚 文档导航

| 文档 | 说明 |
|------|------|
| [🚀 快速启动](QUICKSTART.md) | 5 分钟快速部署指南 |
| [📖 API 参考](docs/API_REFERENCE.md) | 完整的 REST API 文档 |
| [🏗️ 架构说明](docs/ARCHITECTURE.md) | 系统架构和设计原理 |
| [🛠️ 开发指南](docs/DEVELOPMENT_GUIDE.md) | 开发者完整指南 |
| [🤖 多智能体指南](docs/MULTI_AGENT_GUIDE.md) | Agent 协作机制详解 |
| [🐳 Docker 部署](docker/README.md) | 容器化部署指南 |

## 🎯 核心功能

### 多智能体协作

- **📋 Planner Agent**: 需求分析和任务规划
- **💻 Coder Agent**: 代码生成和实现
- **🔍 Reviewer Agent**: 代码审查和质量保证
- **🧪 Tester Agent**: 测试用例生成和验证

### 技术特性

- **LangGraph 工作流**: 状态机驱动的智能体编排
- **Celery 异步任务**: 分布式任务队列支持
- **JWT 认证**: 安全的 API 访问控制
- **数据库持久化**: SQLAlchemy + SQLite/PostgreSQL
- **实时前端**: Streamlit 交互式界面

## 📊 项目结构

```
sponge/
├── app/                    # 核心应用代码
│   ├── agents/            # 智能体实现
│   ├── api/               # REST API 端点
│   ├── core/              # 核心配置和服务
│   ├── db/                # 数据库模型和管理
│   ├── tools/             # 工具函数
│   ├── workflow/          # 工作流定义
│   └── main.py            # 应用入口
├── frontend/              # Streamlit 前端
│   ├── app.py            # 前端主程序
│   └── requirements.txt  # 前端依赖
├── docker/                # Docker 配置
│   ├── docker-compose.yml
│   ├── Dockerfile.api
│   └── Dockerfile.frontend
├── docs/                  # 项目文档
├── tests/                 # 测试用例
└── QUICKSTART.md         # 快速启动指南
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_sponge.py -v

# 查看测试覆盖率
pytest --cov=app tests/
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

感谢以下开源项目:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Streamlit](https://streamlit.io/)
- [Celery](https://docs.celeryq.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)

---

**🎉 开始使用 Sponge，体验多智能体协作的代码生成！**
