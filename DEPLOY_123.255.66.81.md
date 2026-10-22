# 部署到 123.255.66.81 快速指南

> 专为你的服务器配置的自动化部署方案

---

## 📋 服务器信息

- **地址**: 123.255.66.81:39145
- **用户**: wang_zi_wei
- **Docker**: ✅ 已安装 (v26.1.3)
- **Docker Compose**: ✅ 已安装 (v2.27.0)
- **部署目录**: /home/wang_zi_wei/splicegaip
- **API 端口**: 8800
- **UI 端口**: 8501

---

## 🚀 一键部署

### 首次部署

```bash
# 在项目根目录执行
./deploy-to-123.255.66.81.sh

# 脚本会自动完成：
# ✓ 检查服务器连接
# ✓ 验证 Docker 环境
# ✓ 上传代码文件
# ✓ 创建 .env 配置文件
# ✓ 构建并启动容器
# ✓ 验证服务健康状态
```

### 更新部署

以后每次代码更新后，只需重新运行：

```bash
./deploy-to-123.255.66.81.sh
```

脚本会自动同步文件并重启服务。

---

## ⚙️ 配置 API Keys

首次部署后，需要配置 LLM API 密钥：

```bash
# SSH 登录服务器
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81

# 编辑配置文件
vim /home/wang_zi_wei/splicegaip/.env

# 添加你的 DeepSeek API Key
DEEPSEEK_API_KEY=sk-your-actual-key-here

# 保存退出 (:wq)

# 重启服务使配置生效
cd /home/wang_zi_wei/splicegaip
docker compose restart
```

**或者在本地编辑后重新部署**：

```bash
# 在本地复制模板
cp .env.production.example .env

# 编辑 .env 文件，添加 API Key
# DEEPSEEK_API_KEY=sk-your-key

# 重新部署（会上传新的 .env）
./deploy-to-123.255.66.81.sh
```

️ **注意**: `.env` 文件包含敏感信息，不要提交到 Git！

---

## 🔍 验证部署

### 测试 API

```bash
# 从本地测试
curl http://123.255.66.81:8800/api/health

# 期望输出
{"status":"ok","version":"0.1.0"}
```

### 访问 Web UI

在浏览器中打开：
```
http://123.255.66.81:8501
```

### 查看日志

```bash
# 实时日志
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose logs -f"

# 最近 100 行
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose logs --tail 100"
```

---

## 🛠️ 常用操作

### 重启服务

```bash
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose restart"
```

### 停止服务

```bash
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose down"
```

### 查看容器状态

```bash
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose ps"
```

### 查看资源使用

```bash
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker stats splicegaip-api"
```

### 备份数据库

```bash
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && \
   docker compose exec splicegaip-api cp /data/splicegaip.sqlite3 /tmp/backup.sqlite3 && \
   docker cp splicegaip-splicegaip-api-1:/tmp/backup.sqlite3 ./backup-$(date +%Y%m%d).sqlite3"
```

---

## 🔧 故障排查

### 问题 1：端口被占用

**症状**: 部署时提示端口冲突

**解决**:
```bash
# 检查哪些进程占用了端口
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "netstat -tuln | grep -E ':(8800|8501)'"

# 修改 docker-compose.coolify.yml 中的端口映射
# 例如改为 9800:8800 和 9501:8501
```

### 问题 2：内存不足

**症状**: 容器启动后立即退出

**解决**:
```bash
# 检查内存使用
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 "free -h"

# 减少资源限制（编辑 docker-compose.coolify.yml）
deploy:
  resources:
    limits:
      memory: 4G  # 从 8G 降到 4G
```

### 问题 3：API Key 未配置

**症状**: API 返回认证错误

**解决**:
```bash
# 检查 .env 文件
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cat /home/wang_zi_wei/splicegaip/.env | grep DEEPSEEK"

# 编辑并添加正确的 API Key
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "vim /home/wang_zi_wei/splicegaip/.env"

# 重启服务
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose restart"
```

### 问题 4：健康检查失败

**症状**: 容器运行但标记为 unhealthy

**解决**:
```bash
# 手动测试健康检查
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "docker exec splicegaip-splicegaip-api-1 curl http://localhost:8800/api/health"

# 查看详细日志
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "cd /home/wang_zi_wei/splicegaip && docker compose logs splicegaip-api"
```

---

## 📊 监控和维护

### 设置定时备份（可选）

```bash
# 在服务器上创建 cron job
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81

# 编辑 crontab
crontab -e

# 添加每日凌晨 2 点备份
0 2 * * * cd /home/wang_zi_wei/splicegaip && docker compose exec splicegaip-api cp /data/splicegaip.sqlite3 /tmp/backup-$(date +\%Y\%m\%d).sqlite3
```

### 磁盘空间监控

```bash
# 检查 Docker 占用
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "du -sh /var/lib/docker && df -h /home/wang_zi_wei"

# 清理旧镜像
sshpass -p 'qazedctgb' ssh -p 39145 wang_zi_wei@123.255.66.81 \
  "docker image prune -f"
```

---

## 🔐 安全建议

1. **修改默认密码**: 尽快更改服务器密码
   ```bash
   passwd
   ```

2. **配置防火墙**: 只开放必要端口
   ```bash
   # 请管理员配置 iptables 或 ufw
   sudo ufw allow 39145/tcp  # SSH
   sudo ufw allow 8800/tcp   # API
   sudo ufw allow 8501/tcp   # UI
   ```

3. **使用 HTTPS**: 如果需要通过公网访问，建议配置 Nginx + SSL
   - 参考 `nginx.conf` 文件
   - 或使用 Let's Encrypt 免费证书

4. **定期更新**: 每月检查一次 SpliceGAIP 和 Docker 镜像更新

---

## 📞 需要帮助？

- 查看完整文档: [DEPLOY_NO_ROOT.md](DEPLOY_NO_ROOT.md)
- 查看 Coolify 方案: [DEPLOY_COOLIFY.md](DEPLOY_COOLIFY.md)
- 查看测试指南: [TESTING.md](TESTING.md)

---

**祝你部署顺利！** 
