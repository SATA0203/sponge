# Sponge 文档索引

欢迎使用 Sponge 多智能体协作代码开发系统！本文档索引帮助你快速找到所需信息。

---

## 📚 文档导航

### 入门指南

| 文档 | 描述 | 适合人群 |
|------|------|----------|
| [README](../README.md) | 项目概述和快速开始 | 所有人 |
| [GET_STARTED](../GET_STARTED.md) | 环境准备和安装指南 | 新开发者 |
| [开发指南](./DEVELOPMENT_GUIDE.md) | 完整的开发流程和规范 | 开发者 |

### 技术文档

| 文档 | 描述 | 适合人群 |
|------|------|----------|
| [架构设计](./ARCHITECTURE.md) | 系统架构和技术栈详解 | 架构师、高级开发者 |
| [API 参考](./API_REFERENCE.md) | REST API 完整文档 | API 使用者 |
| [多智能体指南](./MULTI_AGENT_GUIDE.md) | Agent 协作机制说明 | AI/ML 工程师 |

### 项目文档

| 文档 | 描述 | 适合人群 |
|------|------|----------|
| [PRD](../PRD_SpongeCodeAgent.md) | 产品需求文档 | 产品经理、开发者 |
| [开发进度](../PROGRESS.md) | 当前开发状态 | 项目成员 |

---

## 🚀 快速路径

### 我是新手，想快速了解 Sponge

1. 阅读 [README](../README.md) 了解项目概况
2. 按照 [GET_STARTED](../GET_STARTED.md) 搭建环境
3. 查看 [API 参考](./API_REFERENCE.md) 了解功能
4. 运行示例任务体验系统

### 我是开发者，想贡献代码

1. 阅读 [开发指南](./DEVELOPMENT_GUIDE.md)
2. 了解 [代码规范](./DEVELOPMENT_GUIDE.md#代码规范)
3. 查看 [架构设计](./ARCHITECTURE.md) 理解系统
4. Fork 项目并创建功能分支

### 我是架构师，想评估技术方案

1. 详细阅读 [架构设计](./ARCHITECTURE.md)
2. 查看 [多智能体指南](./MULTI_AGENT_GUIDE.md) 了解 AI 协作
3. 审查技术栈和依赖
4. 评估扩展性和性能

### 我是测试人员，想了解测试方法

1. 查看 [开发指南 - 测试章节](./DEVELOPMENT_GUIDE.md#测试指南)
2. 了解 [多智能体指南 - Tester Agent](./MULTI_AGENT_GUIDE.md#4-tester-agent 测试员)
3. 运行现有测试套件
4. 编写新的测试用例

---

## 📖 按主题查找

### 环境配置

- [环境变量设置](./DEVELOPMENT_GUIDE.md#环境配置)
- [Docker 部署](./DEVELOPMENT_GUIDE.md#docker-部署)
- [本地开发设置](./DEVELOPMENT_GUIDE.md#本地开发设置)

### API 使用

- [创建任务](./API_REFERENCE.md#1-创建任务)
- [查询状态](./API_REFERENCE.md#3-获取任务详情)
- [文件操作](./API_REFERENCE.md#文件管理接口)
- [WebSocket 通知](./API_REFERENCE.md#websocket-实时通知)

### Agent 开发

- [Agent 角色说明](./MULTI_AGENT_GUIDE.md#agent-角色)
- [添加新 Agent](./DEVELOPMENT_GUIDE.md#2-添加新的-agent)
- [自定义工作流](./MULTI_AGENT_GUIDE.md#自定义工作流)
- [Agent 通信协议](./MULTI_AGENT_GUIDE.md#agent-通信协议)

### 调试与排错

- [日志记录](./DEVELOPMENT_GUIDE.md#日志记录)
- [常见问题](./DEVELOPMENT_GUIDE.md#常见问题)
- [调试技巧](./DEVELOPMENT_GUIDE.md#调试技巧)

---

## 🔧 常用命令速查

### 启动服务

```bash
# Docker Compose（推荐）
docker-compose up -d

# 本地开发
uvicorn app.main:app --reload
celery -A app.celery_app worker --loglevel=info
```

### 运行测试

```bash
# 所有测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=app --cov-report=html
```

### 查看日志

```bash
# API 日志
docker-compose logs -f api

# Worker 日志
docker-compose logs -f worker

# 全部日志
docker-compose logs -f
```

### 数据库操作

```bash
# 进入数据库
docker-compose exec postgres psql -U sponge -d sponge_db

# 迁移
alembic upgrade head
```

---

## 📊 文档更新记录

| 日期 | 文档 | 变更 |
|------|------|------|
| 2024-01 | API_REFERENCE.md | 初始版本 |
| 2024-01 | ARCHITECTURE.md | 初始版本 |
| 2024-01 | DEVELOPMENT_GUIDE.md | 初始版本 |
| 2024-01 | MULTI_AGENT_GUIDE.md | 初始版本 |

---

## 💡 提示与建议

### 文档阅读顺序建议

**第一次接触 Sponge：**
```
README → GET_STARTED → API_REFERENCE → DEVELOPMENT_GUIDE
```

**深入开发：**
```
ARCHITECTURE → MULTI_AGENT_GUIDE → 源码
```

**问题排查：**
```
DEVELOPMENT_GUIDE (故障排除章节) → GitHub Issues
```

### 文档改进

发现文档问题或有改进建议？

1. 在 GitHub 创建 Issue
2. 提交 Pull Request 修改文档
3. 在讨论区提出建议

---

## 🔗 外部资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Celery 文档](https://docs.celeryq.dev/)
- [Docker 文档](https://docs.docker.com/)

---

## 📞 获取帮助

- 📖 **文档**: 当前文档站
- 🐛 **Bug 报告**: GitHub Issues
- 💬 **讨论**: GitHub Discussions
- 📧 **联系**: 查看项目 README

---

**Sponge** - Absorbing complexity, expelling code. 🧽
