# SpliceGAIP 构建指南

## 📁 目录结构（已简化）

```
SpliceGAIP/
├── dist/                    ← 唯一的EXE输出目录
│   └── SpliceGAIP.exe      ← 你的可执行文件在这里
├── packaging/               ← 只保留配置文件
│   ├── SpliceGAIP-Web.spec ← PyInstaller配置
│   ├── icon.ico            ← 应用图标
│   └── rthook_runtime.py   ← 运行时钩子
├── build.bat                ← 一键构建脚本
└── clean_builds.bat         ← 清理构建产物脚本
```

**不再有**：
- ❌ `packaging/dist-*` (多个版本目录)
- ❌ `packaging/build-*` (多个构建缓存)
-  `packaging/dist/` (嵌套的dist)

---

## 🚀 快速开始

### 构建EXE

双击运行：
```
build.bat
```

或手动执行：
```bash
cd E:/SpliceGAIP
./venv/Scripts/python.exe -m PyInstaller packaging/SpliceGAIP-Web.spec \
    --distpath dist \
    --workpath packaging/build-temp
```

**输出位置**：`dist/SpliceGAIP.exe` (~26MB)

---

### 清理构建产物

双击运行：
```
clean_builds.bat
```

这会删除：
- ✅ `packaging/build-*` 所有构建缓存
- ✅ `packaging/dist-*` 所有旧版本
- ✅ `packaging/build-temp` 临时目录

**保留**：
- ✅ `dist/SpliceGAIP.exe` 你的EXE
- ✅ `packaging/*.spec` 配置文件
- ✅ `packaging/*.md` 文档

---

##  版本管理

### Git标签

| 标签 | 日期 | 说明 |
|------|------|------|
| `v2026-10-13-stable` | 2026-10-13 | 稳定版（报告修复） |
| `v3-professional-ui` | 2026-10-15 | 专业极简UI（黑白配色） |
| `v4-agent-chat-ui` | 2026-10-16 | Agent对话面板增强 |

### 回滚到指定版本

```bash
# 查看历史版本
git tag -l

# 恢复UI文件到v3
git checkout v3-professional-ui -- splicegaip/interface/

# 重新构建
build.bat
```

---

##  构建检查清单

构建前确认：
- [ ] 代码已提交到Git
- [ ] 运行过测试（`pytest tests/`）
- [ ] UI显示正常（无透明遮罩、无渐变色）
- [ ] `.env.example` 文件存在

构建后验证：
- [ ] `dist/SpliceGAIP.exe` 存在
- [ ] 文件大小 ~26MB
- [ ] 能正常启动（`dist/SpliceGAIP.exe --help`）
- [ ] Web UI可访问（默认端口8800+）

---

## 🎯 常见问题

### Q: 为什么packaging里还有旧目录？

A: 如果某些目录删不掉（"Device or resource busy"），说明有进程在占用。运行 `clean_builds.bat` 会自动杀掉进程再清理。

### Q: 能不能自定义输出目录？

A: 可以，修改 `build.bat` 中的 `--distpath` 参数：
```bash
python -m PyInstaller ... --distpath my-custom-dir
```

### Q: 如何创建新版本标签？

A: 
```bash
git add .
git commit -m "描述本次修改"
git tag -a v5-xxx -m "版本说明"
```

---

**最后更新**: 2026-10-16  
**维护者**: SpliceGAIP Team
