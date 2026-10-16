# SpliceGAIP 快速启动指南

## 🚀 选择你的启动方式

### Windows 用户（最简单）

**方式1：PyInstaller EXE（推荐新手）**
```bash
# 直接运行已构建好的EXE
cd dist/SpliceGAIP
SpliceGAIP.exe
```

**方式2：Docker（推荐团队使用）**
```bash
# 一键启动，带配置向导
docker-start.bat
```

### Linux/Mac 用户

**Docker部署**
```bash
# 设置API密钥
export MODEL_API_KEY=sk-your-key-here

# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 📋 前置要求

### PyInstaller EXE
- ✅ Windows 10/11
- ✅ 无需安装任何软件

### Docker
- ✅ 安装 Docker Desktop
  - Windows: https://desktop.docker.com/win/main/Docker%20Desktop%20Installer.exe
  - Mac: https://desktop.docker.com/mac/main/Docker.dmg
  - Linux: `sudo apt install docker.io docker-compose`

---

## 🔧 配置 API 密钥（必需）

无论使用哪种方式，都需要配置 DeepSeek API 密钥：

1. **编辑 `.env` 文件**
   ```env
   MODEL_API_BASE_URL=https://api.deepseek.com
   MODEL_NAME=deepseek-flash
   MODEL_API_KEY=sk-your-actual-api-key-here
   MODEL_THINKING=auto
   MODEL_REASONING_EFFORT=low
   ```

2. **获取 API 密钥**
   - 访问：https://platform.deepseek.com
   - 注册账号
   - 创建 API Key

3. **不配置会怎样？**
   - 程序仍可正常运行
   - 但没有 AI 解读、基因注释等增强功能
   - 分析结果完全一致（离线模式）

---

## 🎯 首次使用

### 步骤1：启动程序

**Windows EXE:**
```bash
cd E:\SpliceGAIP\dist\SpliceGAIP
.\SpliceGAIP.exe
```

**Docker:**
```bash
docker-start.bat
```

### 步骤2：访问界面

浏览器自动打开：http://localhost:8800/

或手动访问：
- Web UI: http://localhost:8800/
- API Health: http://localhost:8800/api/health

### 步骤3：上传数据

1. 点击 "Upload Data" 按钮
2. 选择 rMATS 输出文件（.MATS.JC.txt）
3. 填写样本元数据
4. 点击 "Start Analysis"

### 步骤4：查看结果

- **Dashboard**: 概览统计
- **AI Pipeline**: Agent 工作流程
- **Explorer**: 交互式结果浏览
- **Report**: 生成 PDF/HTML 报告

---

## 🛠️ 常用命令

### Docker 管理

```bash
# 启动
docker-run.bat start

# 停止
docker-run.bat stop

# 查看日志
docker-run.bat logs

# 查看状态
docker-run.bat status

# 重启
docker-run.bat restart

# 重新构建（代码更新后）
docker-run.bat rebuild

# 清理所有数据（谨慎使用）
docker-run.bat clean
```

### 检查健康状态

```bash
# 浏览器访问
http://localhost:8800/api/health

# 或使用 curl
curl http://localhost:8800/api/health
```

---

## ❓ 常见问题

### Q1: 程序启动失败？

**PyInstaller:**
```bash
# 检查是否有 .env 文件
ls dist/SpliceGAIP/.env

# 检查端口是否被占用
netstat -ano | findstr :8800
```

**Docker:**
```bash
# 检查 Docker 是否运行
docker info

# 查看详细日志
docker-compose logs splicegaip
```

### Q2: AI 功能未启用？

检查 `.env` 文件中的 `MODEL_API_KEY` 是否正确：

```bash
# 测试 API 密钥
curl -H "Authorization: Bearer sk-your-key" https://api.deepseek.com/v1/models
```

### Q3: 如何更新到最新版本？

**PyInstaller:**
```bash
git pull
build.bat
```

**Docker:**
```bash
git pull
docker-run.bat rebuild
```

### Q4: 数据保存在哪里？

**PyInstaller:**
- 本地目录：`runtime/`
- SQLite 数据库：`runtime/splicegaip.sqlite3`

**Docker:**
- Docker Volume: `splicegaip-data`
- 备份：`docker volume inspect splicegaip-data`

---

## 📚 更多文档

- **API 配置**: `API_CONFIG.md`
- **Docker 详细用法**: `DOCKER_USAGE.md`
- **打包方式对比**: `README_DOCKER.md`
- **完整文档**: `README.md`

---

## 🆘 需要帮助？

1. 查看日志：
   ```bash
   # Docker
   docker-run.bat logs
   
   # EXE (控制台输出)
   SpliceGAIP.exe --no-browser
   ```

2. 检查配置文件：
   ```bash
   # 验证 .env 格式
   cat .env
   ```

3. 查看 GitHub Issues 或联系技术支持

---

**祝你使用愉快！** 🎉
