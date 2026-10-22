# SpliceGAIP Coolify 部署指南

> **Coolify** = 开源的自托管 PaaS 平台，让你在自己的服务器上享受类似 Vercel/Coze 的一键部署体验

---

##  前置要求

### 服务器配置

| 资源 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 2 核 | 4 核 |
| RAM | 4 GB | 8 GB |
| 磁盘 | 50 GB | 100 GB SSD |
| 操作系统 | Ubuntu 22.04+ / Debian 11+ | Ubuntu 24.04 LTS |
| 网络 | 公网 IP + 域名 | 已配置 DNS A 记录 |

### 域名准备

```bash
# 在域名服务商处添加 A 记录
# 示例：splicegaip.your-domain.com → 你的服务器IP
```

---

## 🚀 第一步：安装 Coolify（5 分钟）

### 1.1 SSH 登录到你的服务器

```bash
ssh root@your-server-ip
```

### 1.2 一键安装 Coolify

```bash
# 下载安装脚本
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash

# 等待安装完成（约 3-5 分钟）
```

### 1.3 访问 Coolify 管理界面

```
https://your-server-ip:8000
或
https://coolify.your-domain.com  # 如果配置了域名
```

**首次登录**：
- 使用安装时显示的邮箱和密码
- 或点击 "Create Account" 注册新账户

---

## 🔧 第二步：配置项目（10 分钟）

### 2.1 连接 GitHub 仓库

1. 登录 Coolify 控制台
2. 点击 **"Sources"** → **"Add Source"**
3. 选择 **"GitHub"**
4. 授权访问你的 SpliceGAIP 仓库

### 2.2 创建新项目

1. 点击 **"Projects"** → **"Add Project"**
2. 填写信息：
   - **Name**: `SpliceGAIP`
   - **Description**: AI-driven Alternative Splicing Analysis Platform
   - **Source**: 选择刚才连接的 GitHub 仓库
   - **Branch**: `main` (或你的生产分支)

### 2.3 配置环境变量

在项目设置中，点击 **"Environment Variables"**，添加以下变量：

```bash
# LLM API Keys（必填）
DEEPSEEK_API_KEY=sk-your-actual-key-here

# 可选：其他 LLM 提供商
MOONSHOT_API_KEY=sk-moonshot-key
DASHSCOPE_API_KEY=sk-dashscope-key

# 应用配置
SPLICEGAIP_HOST=0.0.0.0
SPLICEGAIP_PORT=8800
SPLICEGAIP_ENABLE_PUBMED=true

# 安全配置（强烈建议）
SPLICEGAIP_API_KEY=generate-a-random-secret-key
SPLICEGAIP_CORS_ORIGINS=https://splicegaip.your-domain.com

# 日志配置
SPLICEGAIP_LOG_LEVEL=INFO
SPLICEGAIP_JSON_LOGGING=true
```

**生成安全的 API Key**：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.4 配置 Docker Compose

1. 点击 **"Deployments"** → **"Configuration"**
2. 选择 **"Docker Compose"** 模式
3. 上传或粘贴 `docker-compose.coolify.yml` 内容

或者更简单的方式：

```bash
# 在你的本地项目中执行
git add docker-compose.coolify.yml .env.production.example nginx.conf
git commit -m "Add Coolify deployment configuration"
git push origin main
```

Coolify 会自动检测到这些文件！

---

## 🎯 第三步：首次部署（5 分钟）

### 3.1 触发部署

有两种方式：

**方式 A：手动部署**
1. 在 Coolify 项目页面点击 **"Deploy"**
2. 选择分支和版本
3. 点击 **"Start Deployment"**

**方式 B：自动部署（推荐）**
- 每次 `git push` 到主分支后，Coolify 自动拉取并部署
- 无需手动操作！

### 3.2 监控部署过程

在 Coolify 界面中可以看到：
- 📊 实时构建日志
-  Docker 镜像构建进度
- ✅ 健康检查状态
- 🌐 分配的 URL

### 3.3 验证部署成功

```bash
# 测试 API 端点
curl https://splicegaip.your-domain.com/api/health

# 期望输出
{"status": "ok", "version": "0.1.0"}
```

访问 Web UI：
```
https://splicegaip.your-domain.com
```

---

## 🔐 第四步：配置 SSL 和域名（自动）

Coolify 会自动处理 SSL 证书！

### 4.1 配置自定义域名

1. 在项目设置中点击 **"Domains"**
2. 添加你的域名：`splicegaip.your-domain.com`
3. Coolify 自动申请 Let's Encrypt 证书
4. 等待 1-2 分钟，HTTPS 自动生效

### 4.2 验证 SSL

```bash
# 检查证书
curl -I https://splicegaip.your-domain.com

# 应该看到
HTTP/2 200
strict-transport-security: max-age=31536000
```

---

## 📊 第五步：日常运维

### 查看日志

```bash
# 在 Coolify Web UI 中
Projects → SpliceGAIP → Logs

# 或通过命令行
docker logs -f splicegaip-api --tail 100
```

### 更新部署

```bash
# 本地修改代码后
git add .
git commit -m "Update analysis logic"
git push origin main

# Coolify 自动检测并重新部署！
```

### 查看资源使用

在 Coolify 仪表板中可以看到：
- CPU 使用率
- 内存占用
- 磁盘空间
- 网络流量

### 备份数据

```bash
# 备份 SQLite 数据库
docker exec splicegaip-api cp /data/splicegaip.sqlite3 /tmp/backup.sqlite3
docker cp splicegaip-api:/tmp/backup.sqlite3 ./backup-$(date +%Y%m%d).sqlite3

# 或使用 Coolify 的自动备份功能
Projects → SpliceGAIP → Backups → Enable Automatic Backup
```

### 重启服务

```bash
# 在 Coolify UI 中点击 "Restart"
# 或通过命令行
docker restart splicegaip-api
```

---

## 🛠️ 故障排查

### 问题 1：部署失败

**症状**：构建日志显示错误

**解决**：
```bash
# 查看详细日志
docker compose -f docker-compose.coolify.yml logs --tail 200

# 常见问题：
# - API Key 未配置 → 检查环境变量
# - 端口冲突 → 修改 ports 映射
# - 磁盘空间不足 → df -h 检查
```

### 问题 2：健康检查失败

**症状**：容器运行但标记为 unhealthy

**解决**：
```bash
# 手动测试健康检查
docker exec splicegaip-api python -c "import urllib.request; urllib.request.urlopen('http://localhost:8800/api/health')"

# 检查 API 是否启动
docker exec splicegaip-api curl http://localhost:8800/api/health
```

### 问题 3：API 返回 502 Bad Gateway

**原因**：Nginx 无法连接到后端

**解决**：
```bash
# 检查后端服务
docker ps | grep splicegaip-api

# 检查网络连接
docker network inspect splicegaip-network

# 重启 Nginx
docker restart splicegaip-nginx
```

### 问题 4：数据库锁定

**症状**：分析任务卡住

**解决**：
```bash
# 检查 NFS 兼容性（已在代码中处理）
docker exec splicegaip-api ls -la /data/

# 如果仍有问题，迁移到本地临时目录
# 在环境变量中添加
SPLICEGAIP_RUNTIME_ROOT=/tmp/splicegaip-runtime
```

---

## 🎨 高级配置

### 多环境部署

```yaml
# 创建不同环境的配置文件
docker-compose.dev.yml      # 开发环境
docker-compose.staging.yml  # 测试环境
docker-compose.prod.yml     # 生产环境
```

在 Coolify 中创建多个项目实例，分别对应不同环境。

### 性能调优

```bash
# 调整资源限制（docker-compose.coolify.yml）
deploy:
  resources:
    limits:
      cpus: '8'        # 增加 CPU
      memory: 16G      # 增加内存
```

### 监控集成

```bash
# 添加 Prometheus 指标端点
# 在环境变量中启用
SPLICEGAIP_METRICS_ENABLED=true
SPLICEGAIP_METRICS_PORT=9090
```

然后在 Coolify 中配置 Grafana 面板。

---

## 📚 相关文档

- [Coolify 官方文档](https://coolify.io/docs/)
- [SpliceGAIP 测试指南](TESTING.md)
- [SpliceGAIP API 文档](API_CONFIG.md)
- [Docker 最佳实践](DOCKER_USAGE.md)

---

## 💡 提示

1. **首次部署后**：立即备份 `.env.production` 文件到安全位置
2. **定期更新**：每月检查一次 Coolify 和 SpliceGAIP 更新
3. **监控告警**：在 Coolify 中配置邮件/Slack 通知
4. **成本控制**：根据实际使用情况调整资源限制

---

**祝你部署顺利！** 🎉

如有问题，请查看：
- Coolify 社区：https://github.com/coollabsio/coolify/discussions
- SpliceGAIP Issues：https://github.com/yourname/splicegaip/issues
