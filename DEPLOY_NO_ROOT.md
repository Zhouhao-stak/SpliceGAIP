# 无 Root 权限部署指南

> 没有服务器 root 权限？没问题！这里有多种解决方案。

---

##  首先确认你的情况

### 检查清单

```bash
# SSH 登录到你的服务器
ssh user@your-server.com

# 1. 检查 Docker 是否已安装
docker --version
# 如果输出类似 "Docker version 24.x.x"，说明已安装 ✅

# 2. 检查你是否有 Docker 权限
docker ps
# 如果能列出容器（即使为空），说明有权限 ✅
# 如果提示 "permission denied"，说明需要加入 docker 组 ❌

# 3. 检查你是否能创建目录
mkdir -p ~/test && rmdir ~/test
# 如果成功，说明可以部署到用户目录 ✅
```

---

## ✅ 场景 1：Docker 已安装 + 你有权限

**最简单！** 直接使用自动化脚本：

```bash
# 在本地执行
./deploy-to-server.sh user@your-server.com /home/user/splicegaip

# 首次部署后，更新只需重新运行脚本
./deploy-to-server.sh user@your-server.com /home/user/splicegaip
```

**优点**：
- ✅ 无需 root 权限
- ✅ 一键部署/更新
- ✅ 完全自动化

**缺点**：
- ️ 需要管理员预先安装 Docker
- ⚠️ 没有 Web 管理界面

---

## ⚠️ 场景 2：Docker 已安装 + 你没有权限

**症状**：`docker ps` 提示 "permission denied"

**解决**：请管理员执行一条命令

```bash
# 让管理员执行（只需一次）
sudo usermod -aG docker $USER

# 然后你重新登录 SSH
exit
ssh user@your-server.com

# 现在应该可以了
docker ps
```

之后就可以使用场景 1 的脚本了。

---

## ❌ 场景 3：Docker 未安装

你有两个选择：

### 选项 A：请管理员安装 Docker（推荐）

给管理员发送邮件/消息：

```
主题：请求在服务器上安装 Docker

您好，

我需要在服务器上部署 SpliceGAIP 应用，需要安装 Docker。

安装命令（Ubuntu/Debian）：
sudo apt update
sudo apt install docker.io docker-compose-plugin

安装后请将我的用户加入 docker 组：
sudo usermod -aG docker $USER

谢谢！
```

### 选项 B：使用 Python 虚拟环境部署（无需 Docker）

如果管理员无法安装 Docker，可以用传统方式：

```bash
# SSH 登录服务器
ssh user@your-server.com

# 1. 创建项目目录
mkdir -p ~/splicegaip
cd ~/splicegaip

# 2. 上传代码（从本地）
# 在本地执行：
scp -r * user@your-server.com:~/splicegaip/

# 3. 在服务器上设置
ssh user@your-server.com
cd ~/splicegaip

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.production.example .env
vim .env  # 编辑添加 API Keys

# 启动服务
nohup python run.py serve --api --ui --port 8800 > splicegaip.log 2>&1 &

# 查看日志
tail -f splicegaip.log
```

**缺点**：
-  手动操作较多
- ❌ 没有自动重启
- ❌ 更新需要手动操作

---

## 🌟 方案 C：使用云平台 PaaS（完全不需要服务器）

如果你不想管理服务器，可以使用免费的云平台：

### Railway.app（最简单）

1. 访问 https://railway.app
2. 用 GitHub 登录
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择你的 SpliceGAIP 仓库
5. 添加环境变量（API Keys 等）
6. 自动部署完成！

**免费额度**：$5/月（足够个人使用）

### Render.com

1. 访问 https://render.com
2. 连接 GitHub 仓库
3. 选择 "Web Service"
4. 配置 Dockerfile
5. 添加环境变量
6. 部署！

**免费额度**：750 小时/月

### Fly.io

```bash
# 安装 flyctl
curl -L https://fly.io/install.sh | sh

# 登录
fly auth signup

# 部署
fly launch
fly deploy
```

**免费额度**：3 个共享 CPU VM

---

##  方案对比

| 特性 | Docker+SSH | Python Venv | Railway | Render |
|------|-----------|-------------|---------|--------|
| **需要 Root** | ❌ | ❌ | ❌ | ❌ |
| **部署难度** | ⭐ 简单 | ⭐⭐⭐ 复杂 | ⭐ 超简单 | ⭐ 简单 |
| **自动重启** | ✅ | ❌ | ✅ | ✅ |
| **自动更新** | ✅ (脚本) | ❌ | ✅ (Git push) | ✅ (Git push) |
| **Web 管理** | ❌ |  | ✅ | ✅ |
| **成本** | 服务器费用 | 服务器费用 | $5/月起 | 免费 tier |
| **数据控制** | ✅ 完全控制 | ✅ 完全控制 | ⚠️ 第三方 | ⚠️ 第三方 |
| **适合场景** | 有自己的服务器 | 无法装 Docker | 快速上线 | 免费试用 |

---

## 🎯 我的建议

### 如果你有固定服务器

**优先尝试**：
1. 检查 Docker 是否已安装
2. 如果有，用 `deploy-to-server.sh` 脚本
3. 如果没有，请管理员安装（只需 5 分钟）

**备选方案**：
- 如果管理员不配合，用 Python 虚拟环境方式

### 如果你想快速体验

**推荐云平台**：
1. Railway.app（最简单，$5/月）
2. Render.com（有免费额度）

### 如果是生产环境

**必须用自己的服务器**：
- 数据安全可控
- 性能有保障
- 长期成本更低

---

## 🔧 故障排查

### 问题 1：SSH 连接失败

```bash
# 检查网络
ping your-server.com

# 检查 SSH 端口
ssh -v user@your-server.com

# 常见原因：
# - IP 地址错误
# - 防火墙阻止
# - SSH 服务未运行
```

### 问题 2：rsync 不可用

```bash
# 在服务器上安装
sudo apt install rsync

# 或者改用 scp（较慢）
scp -r ./ user@server:~/splicegaip/
```

### 问题 3：端口被占用

```bash
# 检查端口占用
ssh user@server "netstat -tuln | grep 8800"

# 修改端口
# 在 docker-compose.yml 中改为其他端口，如 9900:8800
```

### 问题 4：内存不足

```bash
# 检查内存
ssh user@server "free -h"

# 减少 Docker 资源限制
# 在 docker-compose.yml 中调整：
deploy:
  resources:
    limits:
      memory: 4G  # 从 8G 降到 4G
```

---

## 💡 提示

1. **首次部署后**：立即测试 API 是否正常
   ```bash
   curl http://your-server:8800/api/health
   ```

2. **定期备份**：
   ```bash
   # 备份数据库
   ssh user@server "cp ~/splicegaip/data/*.sqlite3 ~/backup/"
   ```

3. **监控日志**：
   ```bash
   # 实时查看日志
   ssh user@server "tail -f ~/splicegaip/splicegaip.log"
   ```

4. **设置别名**（方便以后使用）：
   ```bash
   # 添加到 ~/.bashrc
   alias deploy-splicegaip='./deploy-to-server.sh user@server /home/user/splicegaip'
   
   # 以后只需输入
   deploy-splicegaip
   ```

---

##  相关文档

- [自动化部署脚本](deploy-to-server.sh)
- [Coolify 部署指南](DEPLOY_COOLIFY.md)（需要 root）
- [Docker 使用指南](DOCKER_USAGE.md)
- [快速开始](COOLIFY_QUICKSTART.md)

---

**没有 root 权限不是障碍，选择合适的方案即可！** 

有疑问？查看上面的故障排查或联系你的服务器管理员。
