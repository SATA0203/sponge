# 🚀 Sponge 快速启动指南

## 方式一：Docker 部署 (推荐)

### 1. 配置环境变量

```bash
cd /workspace/sponge
cp docker/.env.example .env
# 编辑 .env 文件，设置 LLM_API_KEY
```

### 2. 一键启动

```bash
docker-compose -f docker/docker-compose.yml up -d
```

### 3. 访问服务

- **前端界面**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs
- **默认账号**: admin / admin123

---

## 方式二：本地开发部署

### 1. 安装依赖

```bash
# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
pip install -r frontend/requirements.txt
```

### 2. 启动 Redis

```bash
# Docker 方式
docker run -d -p 6379:6379 --name sponge-redis redis:7-alpine

# 或本地安装
redis-server
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，至少配置 LLM_API_KEY
```

### 4. 初始化数据库

```bash
alembic upgrade head
```

### 5. 启动服务

**终端 1 - 启动 API:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**终端 2 - 启动 Celery Worker:**
```bash
celery -A app.celery_app worker --loglevel=info --pool=solo
```

**终端 3 - 启动前端:**
```bash
streamlit run frontend/app.py --server.port 8501
```

### 6. 访问服务

- **前端界面**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs

---

## ✅ 验证安装

```bash
# 检查 API 健康状态
curl http://localhost:8000/api/health

# 预期输出:
# {"status": "healthy", "service": "sponge-api", ...}
```

---

## 📝 下一步

1. **登录系统**: 使用 admin/admin123 登录前端
2. **创建任务**: 输入任务描述，选择编程语言
3. **查看结果**: 查看多智能体协作生成的代码和测试

---

## 🆘 常见问题

**Q: 无法连接 Redis?**
```bash
# 检查 Redis 是否运行
docker ps | grep redis
# 或
redis-cli ping
```

**Q: LLM API 调用失败？**
- 检查 `.env` 中的 `LLM_API_KEY` 是否正确
- 确认网络连接正常
- 查看 API 日志：`docker-compose logs api`

**Q: 端口被占用？**
修改 `docker-compose.yml` 中的端口映射或使用不同端口。

---

## 📚 更多文档

- [完整文档](docs/README.md)
- [API 参考](docs/API_REFERENCE.md)
- [架构说明](docs/ARCHITECTURE.md)
- [Docker 部署指南](docker/README.md)
