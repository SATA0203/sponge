# 🐳 Docker 部署指南

本文档介绍如何使用 Docker 部署 Sponge 多智能体协作系统。

## 📋 前置要求

- Docker >= 20.10
- Docker Compose >= 2.0
- (可选) LLM API Key (OpenAI 或其他兼容服务)

## 🚀 快速启动

### 1. 克隆项目并进入目录

```bash
cd /workspace/sponge
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp docker/.env.example .env

# 编辑 .env 文件，配置 LLM API Key
# vi .env 或 nano .env
```

**必须配置的变量:**
- `LLM_API_KEY`: 您的 LLM 服务 API Key
- `SECRET_KEY`: 随机生成的密钥 (生产环境)

### 3. 启动所有服务

```bash
# 使用 docker-compose 启动
docker-compose -f docker/docker-compose.yml up -d

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f
```

### 4. 访问服务

- **前端界面**: http://localhost:8501
- **API 服务**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **Redis**: localhost:6379

### 5. 默认登录账号

- 用户名：`admin`
- 密码：`admin123`

## 🛠️ 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| frontend | 8501 | Streamlit 前端界面 |
| api | 8000 | FastAPI 后端服务 |
| worker | - | Celery 异步任务处理 |
| beat | - | Celery 定时任务调度 |
| redis | 6379 | Redis 消息队列 |
| postgres | 5432 | PostgreSQL 数据库 (可选) |

## 🔧 常用命令

### 启动/停止服务

```bash
# 启动所有服务
docker-compose -f docker/docker-compose.yml up -d

# 停止所有服务
docker-compose -f docker/docker-compose.yml down

# 停止并删除数据卷
docker-compose -f docker/docker-compose.yml down -v
```

### 查看服务状态

```bash
# 查看所有服务状态
docker-compose -f docker/docker-compose.yml ps

# 查看特定服务日志
docker-compose -f docker/docker-compose.yml logs api
docker-compose -f docker/docker-compose.yml logs worker
docker-compose -f docker/docker-compose.yml logs frontend
```

### 重启服务

```bash
# 重启单个服务
docker-compose -f docker/docker-compose.yml restart api
docker-compose -f docker/docker-compose.yml restart worker

# 重建并重启
docker-compose -f docker/docker-compose.yml up -d --build
```

### 进入容器

```bash
# 进入 API 容器
docker exec -it sponge-api bash

# 进入 Worker 容器
docker exec -it sponge-worker bash

# 进入 Frontend 容器
docker exec -it sponge-frontend bash
```

## 📊 监控与维护

### 健康检查

```bash
# 检查 API 健康状态
curl http://localhost:8000/api/health

# 检查 Redis 连接
docker exec sponge-redis redis-cli ping
```

### 数据库备份

```bash
# SQLite 备份
docker cp sponge-api:/app/sponge.db ./backup/sponge.db.$(date +%Y%m%d)

# PostgreSQL 备份
docker exec sponge-postgres pg_dump -U sponge sponge > backup.sql
```

### 日志管理

```bash
# 查看实时日志
docker-compose -f docker/docker-compose.yml logs -f

# 查看最近 100 行日志
docker-compose -f docker/docker-compose.yml logs --tail=100

# 导出日志到文件
docker-compose -f docker/docker-compose.yml logs > logs.txt
```

## 🔐 生产环境配置

### 1. 修改默认密钥

```bash
# 生成随机密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 在 .env 中设置
SECRET_KEY=<生成的密钥>
```

### 2. 使用 PostgreSQL 数据库

编辑 `docker/docker-compose.yml`:

```yaml
services:
  api:
    environment:
      - DATABASE_URL=postgresql://sponge:sponge123@postgres:5432/sponge
    depends_on:
      postgres:
        condition: service_healthy
```

### 3. 配置 HTTPS

使用 Nginx 反向代理:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8501;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. 资源限制

在 `docker-compose.yml` 中添加:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## ❓ 故障排除

### 常见问题

**1. 容器无法启动**

```bash
# 查看详细日志
docker-compose -f docker/docker-compose.yml logs <service_name>

# 检查端口占用
lsof -i :8000
lsof -i :8501
lsof -i :6379
```

**2. Redis 连接失败**

```bash
# 检查 Redis 容器状态
docker ps | grep redis

# 测试 Redis 连接
docker exec sponge-redis redis-cli ping
```

**3. 数据库迁移问题**

```bash
# 进入 API 容器
docker exec -it sponge-api bash

# 运行数据库迁移
alembic upgrade head
```

**4. Celery Worker 不工作**

```bash
# 检查 Worker 日志
docker-compose -f docker/docker-compose.yml logs worker

# 重启 Worker
docker-compose -f docker/docker-compose.yml restart worker
```

### 重置环境

```bash
# 完全重置 (删除所有数据和容器)
docker-compose -f docker/docker-compose.yml down -v
rm -rf sponge.db data/
docker-compose -f docker/docker-compose.yml up -d
```

## 📈 性能优化

### 1. 增加 Worker 并发数

编辑 `docker/docker-compose.yml`:

```yaml
worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=8
```

### 2. 使用 Redis 持久化

编辑 `docker/docker-compose.yml`:

```yaml
redis:
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### 3. 数据库连接池

在 `.env` 中配置:

```bash
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

## 📝 更新部署

```bash
# 拉取最新代码
git pull

# 重建并重启服务
docker-compose -f docker/docker-compose.yml up -d --build

# 运行数据库迁移
docker exec sponge-api alembic upgrade head
```

## 🆘 获取帮助

如遇问题，请查看:

1. [官方文档](../docs/)
2. [GitHub Issues](https://github.com/your-repo/sponge/issues)
3. 项目日志: `docker-compose -f docker/docker-compose.yml logs`
