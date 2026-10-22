# 手动部署到 123.255.66.81 步骤指南

由于自动化脚本遇到网络连接问题，请按以下步骤手动部署。

---

##  第一步：打包并上传代码

### 在本地 Windows 上执行

```powershell
# 1. 进入项目目录
cd E:\SpliceGAIP

# 2. 创建部署包（排除不需要的文件）
tar czf splicegaip-deploy.tar.gz ^
  --exclude='.git' ^
  --exclude='venv' ^
  --exclude='__pycache__' ^
  --exclude='*.pyc' ^
  --exclude='.env' ^
  --exclude='node_modules' ^
  --exclude='htmlcov' ^
  --exclude='dist' ^
  --exclude='build' ^
  .

# 3. 使用 WinSCP 或 FileZilla 上传文件
# 服务器: 123.255.66.81
# 端口: 39145
# 用户: wang_zi_wei
# 密码: qazedctgb
# 目标路径: /home/wang_zi_wei/
```

**推荐工具**:
- **WinSCP**: https://winscp.net (免费，图形界面)
- **FileZilla**: https://filezilla-project.org (免费)

**WinSCP 连接设置**:
- 主机名: `123.255.66.81`
- 端口: `39145`
- 用户名: `wang_zi_wei`
- 密码: `qazedctgb`
- 协议: SFTP

---

##  第二步：SSH 登录服务器

```bash
# 使用 Git Bash、WSL 或 PuTTY
ssh -p 39145 wang_zi_wei@123.255.66.81

# 输入密码: qazedctgb
```

---

##  第三步：解压并配置

```bash
# 1. 创建部署目录
mkdir -p ~/splicegaip
cd ~/splicegaip

# 2. 解压上传的文件（假设上传到了 ~）
tar xzf ~/splicegaip-deploy.tar.gz -C ~/splicegaip/

# 3. 验证文件
ls -la
# 应该看到 Dockerfile, docker-compose.yml, requirements.txt 等

# 4. 创建环境变量文件
cp .env.production.example .env

# 5. 编辑 .env 添加 API Key
vim .env
# 或
nano .env

# 添加这一行（替换为你的真实密钥）：
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 保存退出
```

---

##  第四步：启动服务

```bash
# 确保在 splicegaip 目录
cd ~/splicegaip

# 1. 拉取最新镜像
docker compose pull

# 2. 构建并启动容器
docker compose up -d --build

# 3. 查看容器状态
docker compose ps

# 期望看到:
# NAME                STATUS
# splicegaip-api-1    Up (healthy)
```

---

##  第五步：验证部署

```bash
# 1. 等待 15 秒让服务启动
sleep 15

# 2. 测试健康检查
curl http://localhost:8800/api/health

# 期望输出:
# {"status":"ok","version":"0.1.0"}

# 3. 查看日志
docker compose logs -f

# 按 Ctrl+C 退出日志查看
```

---

##  第六步：访问应用

### 从服务器本地访问

```bash
# API
curl http://localhost:8800/api/health

# UI (需要在服务器上安装 lynx 或 links)
lynx http://localhost:8501
```

### 从你的电脑访问

**如果服务器有公网 IP 且端口已开放**：

在浏览器中打开：
```
http://123.255.66.81:8800  # API
http://123.255.66.81:8501  # UI
```

**如果端口未开放，需要配置 SSH 隧道**：

```bash
# 在本地电脑执行
ssh -L 8800:localhost:8800 -L 8501:localhost:8501 -p 39145 wang_zi_wei@123.255.66.81

# 然后在本机浏览器访问
# http://localhost:8800
# http://localhost:8501
```

---

##  更新部署

以后每次代码更新后：

```bash
# 1. 在本地重新打包
cd E:\SpliceGAIP
tar czf splicegaip-deploy.tar.gz --exclude='.git' --exclude='venv' ... .

# 2. 上传到服务器（使用 WinSCP 覆盖旧文件）

# 3. SSH 登录服务器
ssh -p 39145 wang_zi_wei@123.255.66.81

# 4. 解压并重启
cd ~/splicegaip
tar xzf ~/splicegaip-deploy.tar.gz -C ~/splicegaip/
docker compose up -d --build
docker compose logs -f
```

---

##  故障排查

### 问题 1：Docker Compose 命令不存在

```bash
# 检查版本
docker compose version

# 如果提示命令不存在，使用旧版语法
docker-compose up -d --build
```

### 问题 2：端口被占用

```bash
# 检查端口占用
netstat -tuln | grep -E ':(8800|8501)'

# 如果被占用，修改 docker-compose.coolify.yml
vim docker-compose.coolify.yml
# 改为其他端口，如 9800:8800
```

### 问题 3：容器启动后立即退出

```bash
# 查看详细日志
docker compose logs splicegaip-api

# 常见原因：
# - .env 文件缺失或 API Key 错误
# - 内存不足（free -h 检查）
# - 配置文件语法错误
```

### 问题 4：无法从外部访问

```bash
# 检查防火墙
sudo iptables -L -n | grep -E '(8800|8501)'

# 如果端口被阻止，请管理员开放
# 或使用 SSH 隧道（见上面第六步）
```

---

## 💡 提示

1. **保持 SSH 连接稳定**：使用 `screen` 或 `tmux`
   ```bash
   # 安装 screen
   sudo apt install screen  # 如果需要 root

   # 或使用 tmux
   tmux new -s deploy
   # 即使断开连接，会话也会保持
   ```

2. **监控部署进度**：
   ```bash
   # 实时查看日志
   docker compose logs -f --tail 100
   ```

3. **备份数据**：
   ```bash
   # 定期备份 SQLite 数据库
   cp ~/splicegaip-data/splicegaip.sqlite3 ~/backup-$(date +%Y%m%d).sqlite3
   ```

---

##  需要帮助？

如果在部署过程中遇到问题，请告诉我具体的错误信息，我会帮你解决！

常见错误示例：
- "Connection refused" → 端口问题
- "Permission denied" → 权限问题
- "Out of memory" → 资源不足
- "Invalid API key" → 配置问题
