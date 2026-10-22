# SpliceGAIP WinSCP 一键部署方案

> 像扣子一样简单：WinSCP 拖拽上传 + SSH 一条命令启动

---

##  准备工作（只需一次）

### 1. 下载部署包

文件已准备好：**`C:\tmp\splicegaip-deploy-package.tar.gz`** (2.5MB)

如果文件不存在，在 Git Bash 执行：
```bash
cd /e/SpliceGAIP
tar czf /tmp/splicegaip-deploy-package.tar.gz \
  --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.env' --exclude='node_modules' \
  --exclude='htmlcov' --exclude='dist' --exclude='build' \
  --exclude='.github' --exclude='*.tar.gz' .
```

### 2. 安装工具

- **WinSCP**: https://winscp.net （文件上传）
- **PuTTY**: https://www.putty.org （SSH终端）

或者使用 WinSCP 内置终端（菜单 → 命令 → 打开终端 PuTTY）

---

## 🚀 部署流程（3步搞定）

### 第 1 步：WinSCP 上传文件（1分钟）

1. 打开 WinSCP
2. 连接信息：
   - 主机: `123.255.66.81`
   - 端口: `39145`
   - 用户: `wang_zi_wei`
   - 密码: `qazedctgb`
3. 在右侧创建文件夹 `/home/wang_zi_wei/splicegaip`
4. 将 `C:\tmp\splicegaip-deploy-package.tar.gz` **拖拽**到该文件夹
5. 等待上传完成 ✅

### 第 2 步：SSH 一键启动（2分钟）

打开 PuTTY 或 Git Bash，执行以下**完整命令块**（一次性复制粘贴）：

```bash
# SSH 登录
ssh -p 39145 wang_zi_wei@123.255.66.81
# 密码: qazedctgb

# ===== 从这里开始复制 =====

# 解压文件
cd ~/splicegaip
tar xzf splicegaip-deploy-package.tar.gz && rm splicegaip-deploy-package.tar.gz

# 首次部署需要配置 API Key
if [ ! -f .env ]; then
    cp .env.production.example .env
    echo ""
    echo "⚠️  请编辑 .env 添加你的 DeepSeek API Key："
    echo "nano .env"
    echo ""
    echo "添加这一行：DEEPSEEK_API_KEY=sk-your-key-here"
    echo ""
    read -p "按回车继续..."
fi

# 启动服务（自动构建+后台运行）
echo "🚀 Starting SpliceGAIP..."
docker compose pull
docker compose up -d --build

# 等待并验证
echo "Waiting for service to start..."
sleep 15

echo ""
echo "Container status:"
docker compose ps

echo ""
echo "Health check:"
curl -s http://localhost:8800/api/health || echo "Service starting, check logs: docker compose logs -f"

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo "API: http://localhost:8800"
echo "UI:  http://localhost:8501"
echo ""
echo "Useful commands:"
echo "  Logs:     docker compose logs -f"
echo "  Restart:  docker compose restart"
echo "  Stop:     docker compose down"
echo ""

# ===== 到这里结束 =====
```

### 第 3 步：访问应用

**从服务器本地**：
```bash
curl http://localhost:8800/api/health
```

**从你的电脑**（如果端口未开放，使用 SSH 隧道）：
```bash
# 保持这个窗口打开
ssh -L 8800:localhost:8800 -L 8501:localhost:8501 -p 39145 wang_zi_wei@123.255.66.81

# 然后在本机浏览器访问
# http://localhost:8800
# http://localhost:8501
```

---

## 🔄 更新部署（超简单）

以后每次代码更新后：

### 1. 重新打包（本地）
```bash
cd /e/SpliceGAIP
tar czf /tmp/splicegaip-deploy-package.tar.gz \
  --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.env' --exclude='node_modules' \
  --exclude='htmlcov' --exclude='dist' --exclude='build' \
  --exclude='.github' --exclude='*.tar.gz' .
```

### 2. WinSCP 上传
- 拖拽新的 tar.gz 到服务器的 `~/splicegaip/`
- 覆盖旧文件

### 3. SSH 重启（一条命令）
```bash
ssh -p 39145 wang_zi_wei@123.255.66.81 "
cd ~/splicegaip && \
tar xzf splicegaip-deploy-package.tar.gz && \
rm splicegaip-deploy-package.tar.gz && \
docker compose up -d --build && \
docker compose ps
"
```

**就这么简单！** 整个过程不到 1 分钟。

---

##  像扣子一样的体验

| 扣子功能 | SpliceGAIP 实现 |
|---------|----------------|
| 拖拽上传 | ✅ WinSCP 图形界面 |
| 一键部署 | ✅ `docker compose up -d --build` |
| 自动构建 | ✅ Dockerfile 自动处理 |
| 健康检查 | ✅ 内置 healthcheck |
| 日志查看 | ✅ `docker compose logs -f` |
| 版本管理 | ✅ Git + tar 包版本控制 |
| Web 界面 | ✅ Streamlit UI (端口 8501) |

**虽然不是真正的 SaaS 平台，但操作流程已经非常接近了！**

---

## 🔧 常用维护命令

```bash
# 查看实时日志
docker compose logs -f

# 查看最近 100 行
docker compose logs --tail 100

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 查看资源使用
docker stats splicegaip-api

# 进入容器内部
docker compose exec splicegaip-api bash

# 备份数据库
docker compose exec splicegaip-api cp /data/splicegaip.sqlite3 /tmp/backup.sqlite3
docker cp splicegaip-splicegaip-api-1:/tmp/backup.sqlite3 ./backup.sqlite3
```

---

## ⚙️ 首次配置 API Key

首次部署后必须配置：

```bash
# SSH 登录
ssh -p 39145 wang_zi_wei@123.255.66.81

# 编辑配置
cd ~/splicegaip
nano .env

# 添加这一行（替换为你的真实密钥）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 保存退出 (Ctrl+O, Enter, Ctrl+X)

# 重启使配置生效
docker compose restart
```

---

## 🎯 对比传统方式

| 操作 | 传统手动部署 | WinSCP 方案 | 提升 |
|------|------------|------------|------|
| 文件上传 | scp 命令/命令行 | 拖拽 | ⭐⭐⭐⭐ |
| 配置环境 | 手动编辑多个文件 | 一条命令 | ⭐⭐⭐⭐ |
| 启动服务 | 多步命令 | 一键启动 | ⭐⭐⭐⭐⭐ |
| 更新部署 | 重复所有步骤 | 3步搞定 | ⭐⭐⭐⭐⭐ |
| 学习成本 | 高（Linux/Docker） | 低（图形界面） | ⭐⭐⭐⭐ |

---

## 📞 遇到问题？

常见错误及解决方案：

**Q: Connection timed out**
A: 检查网络，稍后再试。服务器可能暂时不可用。

**Q: Permission denied**
A: 确认密码正确，或联系管理员。

**Q: Docker command not found**
A: 服务器上 Docker 未安装，需要管理员协助。

**Q: Port already in use**
A: 修改 `docker-compose.coolify.yml` 中的端口映射。

**Q: Invalid API key**
A: 检查 `.env` 文件中的 DEEPSEEK_API_KEY 是否正确。

---

## 🎉 总结

这个方案的核心优势：

1. ✅ **WinSCP 图形界面** - 稳定可靠，适合不稳定网络
2. ✅ **一键启动命令** - 复制粘贴即可，无需记忆复杂命令
3. ✅ **像扣子一样简单** - 拖拽 + 一条命令 = 部署完成
4. ✅ **完全自主可控** - 数据在你的服务器上
5. ✅ **免费开源** - 无订阅费用

**总耗时**: 首次部署约 5 分钟，后续更新不到 1 分钟！

---

**开始部署吧！** 

有任何问题随时告诉我具体的错误信息。
