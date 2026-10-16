# SpliceGAIP 打包方式对比

本项目支持两种打包部署方式，可根据使用场景选择：

## 🖥️ 方式一：PyInstaller EXE（Windows推荐）

**适用场景：**
- Windows 用户
- 无需安装额外软件
- 双击即可运行
- 完全本地化运行

**构建命令：**
```bash
build.bat
```

**输出位置：**
```
dist/SpliceGAIP/
├── SpliceGAIP.exe      # 主程序 (26MB)
├── _internal/          # 依赖库
├── .env                # API配置
└── API_CONFIG.md       # 配置指南
```

**分发方式：**
直接复制整个 `dist/SpliceGAIP/` 文件夹

---

## 🐳 方式二：Docker（跨平台推荐）

**适用场景：**
- Linux/Mac 用户
- 服务器部署
- 需要隔离环境
- 团队协作开发

**启动命令：**
```bash
# Windows（一键启动）
docker-start.bat

# Linux/Mac
docker-compose up -d
```

**管理命令：**
```bash
docker-run.bat start      # 启动
docker-run.bat stop       # 停止
docker-run.bat logs       # 查看日志
docker-run.bat status     # 查看状态
```

**访问地址：**
- Web UI: http://localhost:8800/
- API: http://localhost:8800/api/health

---

## 📊 对比表

| 特性 | PyInstaller EXE | Docker |
|------|----------------|--------|
| **平台支持** | Windows only | Windows/Linux/Mac |
| **安装要求** | 无 | 需安装 Docker |
| **启动速度** | ⚡ 快 | 🐢 较慢（首次需拉取镜像） |
| **资源占用** | 较低 | 较高（容器开销） |
| **隔离性** | 低 | 高（容器隔离） |
| **更新方式** | 重新构建EXE | docker pull / rebuild |
| **数据持久化** | 本地文件 | Docker Volume |
| **多实例** | 困难 | 简单（docker-compose） |
| **生产部署** | ❌ 不推荐 | ✅ 推荐 |
| **开发调试** | 一般 | ✅ 方便 |

---

## 🎯 选择建议

**个人用户（Windows）：**
→ 使用 PyInstaller EXE，最简单方便

**团队/服务器部署：**
→ 使用 Docker，易于管理和维护

**开发测试：**
→ 使用 Docker，环境一致性好

**离线环境：**
→ 使用 PyInstaller EXE，无需网络

---

## 📝 配置文件说明

两种方式共用同一个 `.env` 配置文件：

```env
MODEL_API_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
MODEL_API_KEY=sk-your-api-key-here
MODEL_THINKING=auto
MODEL_REASONING_EFFORT=low
```

- **PyInstaller**: `.env` 放在 EXE 同目录
- **Docker**: `.env` 通过环境变量或挂载传入

详细配置说明见：`API_CONFIG.md`、`DOCKER_USAGE.md`
