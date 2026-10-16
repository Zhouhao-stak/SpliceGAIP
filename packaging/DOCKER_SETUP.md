# Docker 构建指南

## ❌ 当前问题

Docker Desktop未运行，无法构建镜像。

## ✅ 解决方案

### Windows用户

1. **启动Docker Desktop**
   ```
   - 在开始菜单搜索 "Docker Desktop"
   - 双击打开
   - 等待右下角鲸鱼图标变为绿色（Running状态）
   ```

2. **验证Docker运行**
   ```bash
   docker info
   # 应该显示服务器信息而不是错误
   ```

3. **重新构建**
   ```bash
   cd E:\SpliceGAIP
   docker build -t splicegaip:latest .
   ```

### Linux/Mac用户

```bash
# 启动Docker服务
sudo systemctl start docker    # Linux (systemd)
# 或
sudo service docker start      # Linux (init.d)

# Mac通常通过Docker Desktop应用启动

# 验证
docker info

# 构建
cd /path/to/splicegaip
docker build -t splicegaip:latest .
```

---

## 🔍 故障排查

### 问题1: "Cannot connect to the Docker daemon"

**原因**: Docker Desktop未启动

**解决**:
```bash
# Windows: 启动Docker Desktop应用
# Linux: sudo systemctl start docker
# Mac: 打开Docker Desktop应用
```

### 问题2: "permission denied while trying to connect to the Docker daemon socket"

**原因**: 用户不在docker组

**解决** (Linux):
```bash
sudo usermod -aG docker $USER
# 注销并重新登录
```

### 问题3: "no space left on device"

**原因**: Docker磁盘空间不足

**解决**:
```bash
# 清理未使用的镜像和容器
docker system prune -a

# 检查磁盘使用
docker system df
```

### 问题4: Build卡在下载依赖

**原因**: 网络慢或PyPI镜像问题

**解决**:
```bash
# 使用国内PyPI镜像（修改Dockerfile）
RUN pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --prefix=/install -r requirements.txt
```

---

## 📦 替代方案：如果Docker无法使用

### 方案A: 使用已有的EXE
```bash
cd packaging/dist-web/SpliceGAIP
双击 SpliceGAIP.exe
```

### 方案B: Python虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python serve_ui.py
```

### 方案C: Snakemake工作流
```bash
conda install -c bioconda snakemake
snakemake --cores all --use-conda
```

---

## 🎯 Docker构建成功后

### 查看镜像
```bash
docker images | grep splicegaip
# 输出示例:
# splicegaip   latest   abc123def456   2 minutes ago   500MB
```

### 运行容器
```bash
# 简单运行
docker run -p 8501:8501 splicegaip:latest

# 或使用docker-compose（推荐）
docker-compose up -d
```

### 访问应用
```
打开浏览器: http://localhost:8501
```

### 停止容器
```bash
docker-compose down
# 或
docker stop $(docker ps -q --filter ancestor=splicegaip:latest)
```

---

## 🚀 快速测试脚本

创建 `test-docker.sh` (Linux/Mac):
```bash
#!/bin/bash
echo "检查Docker状态..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker Desktop"
    exit 1
fi

echo "✅ Docker运行正常"
echo "开始构建镜像..."
docker build -t splicegaip:test .

if [ $? -eq 0 ]; then
    echo "✅ 构建成功！"
    echo "运行测试: docker run -p 8501:8501 splicegaip:test"
else
    echo "❌ 构建失败，请检查错误信息"
fi
```

Windows版本 `test-docker.bat`:
```batch
@echo off
echo 检查Docker状态...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker未运行，请先启动Docker Desktop
    exit /b 1
)

echo Docker运行正常
echo 开始构建镜像...
docker build -t splicegaip:test .

if %errorlevel% equ 0 (
    echo 构建成功！
    echo 运行测试: docker run -p 8501:8501 splicegaip:test
) else (
    echo 构建失败，请检查错误信息
    exit /b 1
)
```

---

## 📊 预期构建时间

| 阶段 | 时间 | 说明 |
|------|------|------|
| Stage 1: 基础镜像 | ~30s | 下载python:3.11-slim |
| Stage 1: 安装依赖 | ~2-5分钟 | pip install所有包 |
| Stage 2: 复制文件 | ~10s | 复制应用代码 |
| 总计 | **3-6分钟** | 首次构建较慢 |

后续构建会利用缓存，速度更快（~1分钟）。
