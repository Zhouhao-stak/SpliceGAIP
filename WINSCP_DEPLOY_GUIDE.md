# WinSCP 部署 SpliceGAIP 完整指南

> 最简单可靠的部署方式 - 图形界面操作，无需命令行

---

## 📦 第一步：准备部署包

部署包已为你准备好：

**文件位置**: `C:\tmp\splicegaip-deploy-package.tar.gz` (2.5MB)

如果文件不存在，在 Git Bash 中执行：
```bash
cd /e/SpliceGAIP
tar czf /tmp/splicegaip-deploy-package.tar.gz \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='node_modules' \
  --exclude='htmlcov' \
  --exclude='dist' \
  --exclude='build' \
  --exclude='.github' \
  --exclude='*.tar.gz' \
  .
```

---

##  第二步：下载安装 WinSCP

1. **下载地址**: https://winscp.net/eng/download.php
2. **安装**: 双击安装包，使用默认设置即可
3. **启动**: 打开 WinSCP

---

##  第三步：连接服务器

### WinSCP 登录设置

打开 WinSCP 后，点击 "新建会话"，填写：

| 字段 | 值 |
|------|-----|
| **文件协议** | SFTP |
| **主机名** | `123.255.66.81` |
| **端口号** | `39145` |
| **用户名** | `wang_zi_wei` |
| **密码** | `qazedctgb` |

然后点击 **"登录"**

首次连接会提示保存主机密钥，点击 **"是"**。

---

## 📤 第四步：上传文件

### 4.1 创建远程目录

登录后，你会看到左右两个面板：
- **左边**: 你的本地电脑（Windows）
- **右边**: 远程服务器（Linux）

**在右侧面板（服务器）操作**：
1. 导航到 `/home/wang_zi_wei/`
2. 右键 → 新建 → 目录
3. 输入目录名: `splicegaip`
4. 回车确认

### 4.2 上传部署包

**在左侧面板（本地）操作**：
1. 导航到 `C:\tmp\`
2. 找到 `splicegaip-deploy-package.tar.gz` 文件
3. **拖拽**这个文件到右侧的 `splicegaip` 文件夹中

或者：
1. 右键点击文件
2. 选择 "上传"
3. 确认传输

**等待上传完成**（2.5MB 大约需要 10-30 秒，取决于网速）

---

## 🔧 第五步：SSH 解压和配置

上传完成后，需要 SSH 登录服务器解压文件。

### 方法 A：使用 PuTTY（推荐）

1. **下载 PuTTY**: https://www.putty.org/
2. **连接设置**:
   - Host Name: `123.255.66.81`
   - Port: `39145`
   - Connection type: SSH
3. 点击 **"Open"**
4. 登录信息:
   - login as: `wang_zi_wei`
   - password: `qazedctgb`

### 方法 B：使用 Git Bash

打开 Git Bash，执行：
```bash
ssh -p 39145 wang_zi_wei@123.255.66.81
# 输入密码: qazedctgb
```

### 在服务器上执行以下命令

```bash
# 1. 进入部署目录
cd ~/splicegaip

# 2. 解压文件
tar xzf splicegaip-deploy-package.tar.gz

# 3. 验证文件
ls -la
# 应该看到 Dockerfile, docker-compose.yml, requirements.txt, splicegaip/ 等

# 4. 删除压缩包（节省空间）
rm splicegaip-deploy-package.tar.gz

# 5. 创建环境变量文件
cp .env.production.example .env

# 6. 编辑配置文件添加 API Key
nano .env
# 或
vim .env
```

### 编辑 .env 文件

在文件中添加这一行（替换为你的真实密钥）：

```bash
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
```

**如果使用 nano**：
- 按 `Ctrl+O` 保存
- 按 `Enter` 确认
- 按 `Ctrl+X` 退出

**如果使用 vim**：
- 按 `i` 进入编辑模式
- 添加 API Key
- 按 `Esc` 退出编辑模式
- 输入 `:wq` 保存并退出

---

## 🚀 第六步：启动服务

继续在 SSH 终端中执行：

```bash
# 确保在 splicegaip 目录
cd ~/splicegaip

# 1. 拉取最新 Docker 镜像
docker compose pull

# 2. 构建并启动容器
docker compose up -d --build

# 3. 查看容器状态
docker compose ps
```

**期望输出**：
```
NAME                IMAGE          STATUS
splicegaip-api-1    ...            Up (healthy)
```

```bash
# 4. 等待服务启动
sleep 15

# 5. 测试健康检查
curl http://localhost:8800/api/health
```

**期望输出**：
```json
{"status":"ok","version":"0.1.0"}
```

```bash
# 6. 查看实时日志（可选）
docker compose logs -f

# 按 Ctrl+C 退出日志查看
```

---

## 🌐 第七步：访问应用

### 从服务器本地访问

```bash
# API
curl http://localhost:8800/api/health

# Web UI（如果服务器有浏览器）
firefox http://localhost:8501 &
```

### 从你的电脑访问

**如果服务器端口已开放**：

在浏览器中打开：
- API: `http://123.255.66.81:8800`
- UI: `http://123.255.66.81:8501`

**如果端口未开放（更常见）**，使用 SSH 隧道：

```bash
# 在本地电脑执行（保持这个窗口打开）
ssh -L 8800:localhost:8800 -L 8501:localhost:8501 -p 39145 wang_zi_wei@123.255.66.81

# 然后在本机浏览器访问
# http://localhost:8800
# http://localhost:8501
```

---

## 🔄 更新部署

以后每次代码更新后：

### 步骤 1：重新打包

在本地 Git Bash 执行：
```bash
cd /e/SpliceGAIP
tar czf /tmp/splicegaip-deploy-package.tar.gz \
  --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  --exclude='*.pyc' --exclude='.env' --exclude='node_modules' \
  --exclude='htmlcov' --exclude='dist' --exclude='build' \
  --exclude='.github' --exclude='*.tar.gz' .
```

### 步骤 2：上传新包

在 WinSCP 中：
1. 将新的 `splicegaip-deploy-package.tar.gz` 拖到服务器的 `~/splicegaip/`
2. 覆盖旧文件

### 步骤 3：SSH 解压重启

```bash
ssh -p 39145 wang_zi_wei@123.255.66.81

cd ~/splicegaip
tar xzf splicegaip-deploy-package.tar.gz
rm splicegaip-deploy-package.tar.gz
docker compose up -d --build
docker compose logs -f
```

---

##  实用技巧

### 1. 保存 WinSCP 会话

避免每次都输入信息：
1. 在 WinSCP 登录界面填写好信息
2. 点击 "保存"
3. 输入会话名称（如 "SpliceGAIP Server"）
4. 下次直接双击会话名即可连接

### 2. 使用 WinSCP 内置终端

WinSCP 菜单栏 → 命令 → 打开终端 PuTTY

这样可以在 WinSCP 中直接打开 SSH 终端，无需额外软件。

### 3. 同步文件夹（高级）

WinSCP 支持文件夹同步：
1. 菜单 → 命令 → 同步文件夹
2. 选择 "本地到远程"
3. 可以自动同步更改的文件

但首次部署建议使用 tar 包方式，更可靠。

---

## 🔍 故障排查

### 问题 1：WinSCP 连接失败

**检查**：
- 主机名、端口是否正确
- 网络是否通畅（ping 123.255.66.81）
- 防火墙是否阻止

**解决**：
```bash
# 测试连接
ping 123.255.66.81

# 测试 SSH
ssh -p 39145 wang_zi_wei@123.255.66.81
```

### 问题 2：上传速度慢

**原因**：网络带宽限制

**解决**：
- 耐心等待（2.5MB 通常很快）
- 或使用压缩率更高的选项

### 问题 3：解压后文件不全

**检查**：
```bash
cd ~/splicegaip
ls -la
# 应该看到完整的文件结构
```

**解决**：
- 重新上传 tar 包
- 确认 tar 命令没有报错

### 问题 4：Docker 启动失败

**查看详细日志**：
```bash
docker compose logs splicegaip-api
```

**常见原因**：
- `.env` 文件缺失 → `cp .env.production.example .env`
- API Key 未配置 → 编辑 `.env` 添加
- 端口被占用 → 修改 `docker-compose.coolify.yml`

---

## 📞 需要帮助？

如果在任何步骤遇到问题，告诉我具体的错误信息或截图，我会帮你解决！

常见问题关键词：
- "Connection refused" → 网络/端口问题
- "Permission denied" → 权限问题
- "No such file" → 路径错误
- "Out of memory" → 资源不足

---

**祝你部署顺利！** 
