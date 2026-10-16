# SpliceGAIP Docker 打包说明

## 为什么选择Docker？

✅ **环境隔离**: 不污染宿主系统，所有依赖在容器内
✅ **可复现**: 一次构建，到处运行
✅ **易部署**: 一条命令即可启动
✅ **干净**: 不需要时直接删除容器，不留垃圾
✅ **专业**: 适合科研和生产环境

## 快速开始（3步）

### 1️⃣ 安装Docker Desktop
下载地址: https://www.docker.com/products/docker-desktop

### 2️⃣ 双击运行启动脚本
```
docker-start.bat
```
选择选项 `1` (构建并启动)

### 3️⃣ 打开浏览器访问
- Web界面: http://localhost:8501
- API: http://localhost:8800

就这么简单！🎉

## 文件结构

```
SpliceGAIP/
├── Dockerfile              # Docker镜像定义
├── docker-compose.yml      # 容器编排配置
├── .dockerignore          # Docker忽略文件
├── DOCKER_USAGE.md        # 详细使用指南
├── docker-start.bat       # Windows快速启动脚本
└── packaging/
    └── DOCKER_READIME.md  # 本文件
```

## 常用场景

### 场景1: 首次使用
```bash
# 双击运行
docker-start.bat
# 选择 1

# 或手动执行
docker-compose build
docker-compose up -d
```

### 场景2: 日常启动
```bash
# 双击运行
docker-start.bat
# 选择 2

# 或手动执行
docker-compose start
```

### 场景3: 停止服务
```bash
# 双击运行
docker-start.bat
# 选择 3

# 或手动执行
docker-compose down
```

### 场景4: 查看日志
```bash
# 双击运行
docker-start.bat
# 选择 4

# 或手动执行
docker-compose logs -f
```

## 配置LLM（可选）

在项目根目录创建 `.env` 文件：

```env
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=sk-your-api-key-here
MODEL_NAME=deepseek-flash
MODEL_THINKING=auto
```

然后重新启动容器。

## 数据持久化

所有分析结果保存在 `runtime/` 目录：

```
runtime/
└── projects/
    ├── SPN-20261013-xxx/
    │   ├── figures/
    │   ├── report.html
    │   └── report.pdf
    └── ...
```

即使删除容器，数据也不会丢失（因为挂载了卷）。

## 优势对比

| 特性 | Docker | PyInstaller EXE |
|------|--------|----------------|
| 文件大小 | ~800MB镜像 | ~43MB单文件 |
| 启动速度 | 快（秒级） | 慢（需解压） |
| 依赖管理 | 完美隔离 | 可能缺失模块 |
| 跨平台 | ✅ Linux/Mac/Windows | ❌ 仅Windows |
| 更新维护 | 简单（重建镜像） | 复杂（重新打包） |
| 生产部署 | ✅ 推荐 | ❌ 不推荐 |
| 开发调试 | 方便 | 困难 |

## 故障排查

### Q: Docker未安装？
A: 下载安装 Docker Desktop for Windows

### Q: 端口被占用？
A: 修改 `docker-compose.yml` 中的端口映射

### Q: 容器启动失败？
A: 运行 `docker-compose logs` 查看详细错误

### Q: 如何完全清理？
A: 运行 `docker-start.bat` 选择选项 6

## 更多信息

详细使用文档: [DOCKER_USAGE.md](../DOCKER_USAGE.md)

---

**推荐使用Docker进行开发和部署！** 🐳
