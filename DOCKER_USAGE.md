# SpliceGAIP Docker 使用指南

## 快速开始

### Windows 用户（推荐）

1. **安装 Docker Desktop**
   - 下载：https://www.docker.com/products/docker-desktop
   - 启动 Docker Desktop

2. **配置 API 密钥**
   ```bash
   # 编辑 .env 文件，填入 DeepSeek API 密钥
   notepad .env
   ```

3. **一键启动**
   ```bash
   docker-start.bat
   ```

4. **访问应用**
   - Web UI: http://localhost:8800/
   - API: http://localhost:8800/api/health

### Linux/Mac 用户

```bash
# 配置环境变量
export MODEL_API_KEY=sk-your-key-here

# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 管理命令

使用 `docker-run.bat` 管理容器：

```bash
docker-run.bat start      # 启动
docker-run.bat stop       # 停止
docker-run.bat restart    # 重启
docker-run.bat logs       # 查看日志
docker-run.bat status     # 查看状态
docker-run.bat rebuild    # 重新构建
docker-run.bat clean      # 清理所有数据
```

## 配置说明

### 方式一：使用 .env 文件（推荐）

在项目根目录创建 `.env` 文件：

```env
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
MODEL_API_KEY=sk-your-api-key-here
MODEL_THINKING=auto
MODEL_REASONING_EFFORT=low
```

### 方式二：通过 docker-compose.yml 环境变量

编辑 `docker-compose.yml` 中的 `environment` 部分。

### 方式三：运行时传入

```bash
MODEL_API_KEY=sk-xxx docker-compose up -d
```

## 数据持久化

Docker 卷会自动保存以下数据：

- SQLite 数据库（分析结果、文献库）
- 运行时状态
- 用户上传的文件

数据存储在名为 `splicegaip-data` 的 Docker 卷中。

## 端口映射

| 容器端口 | 主机端口 | 用途 |
|---------|---------|------|
| 8800    | 8800    | API 服务器 + Web UI |
| 8501    | 8501    | Streamlit UI（可选） |

如需修改端口，编辑 `docker-compose.yml` 中的 `ports` 部分。

## 资源限制

默认配置：
- CPU: 2-4 核心
- 内存: 4-8 GB

可根据需要调整 `docker-compose.yml` 中的 `deploy.resources` 部分。

## 健康检查

容器每30秒自动检查一次健康状态：

```bash
# 查看健康状态
docker inspect --format='{{.State.Health.Status}}' splicegaip
```

## 常见问题

### Q: 容器启动失败？

```bash
# 查看详细日志
docker-compose logs

# 检查 Docker 是否运行
docker info
```

### Q: 如何更新到最新版本？

```bash
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Q: 如何备份数据？

```bash
# 导出数据库卷
docker run --rm -v splicegaip-data:/data -v %cd%:/backup alpine tar czf /backup/splicegaip-backup.tar.gz /data
```

### Q: AI 功能未启用？

检查 `.env` 文件中是否正确配置了 `MODEL_API_KEY`：

```bash
docker-compose exec splicegaip python -c "import os; print(os.getenv('MODEL_API_KEY', 'NOT SET')[:10] + '****')"
```

## 高级用法

### 自定义配置文件

挂载本地配置目录：

```yaml
volumes:
  - ./config:/app/config:ro
```

### 使用自定义网络

```bash
docker network create my-network
docker-compose --network my-network up -d
```

### 多实例部署

```bash
# 复制 docker-compose.yml 并修改项目名称
COMPOSE_PROJECT_NAME=splicegaip-prod docker-compose up -d
COMPOSE_PROJECT_NAME=splicegaip-dev docker-compose -f docker-compose.dev.yml up -d
```

## 安全建议

1. **不要将 `.env` 文件提交到 Git**（已在 `.gitignore` 中）
2. **定期轮换 API 密钥**
3. **使用 HTTPS 反向代理**（生产环境）
4. **限制容器资源**防止 DoS 攻击

## 技术支持

遇到问题？查看日志：

```bash
docker-compose logs -f splicegaip
```

或查看完整文档：`API_CONFIG.md`
