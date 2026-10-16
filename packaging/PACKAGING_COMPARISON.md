# SpliceGAIP 打包方案完整对比

基于BioGAIP的容器化经验，SpliceGAIP提供多种部署方式。

---

## 📊 方案对比表

| 特性 | Windows EXE | Docker容器 | Snakemake工作流 | Python包 |
|------|-------------|-----------|----------------|---------|
| **适用平台** | Windows only | Linux/Mac/Windows | Linux/Mac/Windows | All |
| **安装难度** | ⭐ 最简单 | ⭐⭐ 简单 | ⭐⭐⭐ 中等 | ⭐⭐⭐⭐ 复杂 |
| **启动速度** | 快 (~5秒) | 中 (~15秒) | 慢 (首次环境搭建) | 快 |
| **文件大小** | 23MB | ~500MB (镜像) | ~100MB (env.zip) | 按需 |
| **离线运行** | ✅ 完全离线 | ✅ 完全离线 | ✅ 完全离线 | ✅ |
| **可复现性** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **学术发表** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **服务器部署** | ❌ | ✅ 优秀 | ✅ 良好 | ✅ |
| **bioservices支持** | ✅ | ✅ | ✅ | ✅ |
| **知识持久化** | ✅ | ✅ (volume) | ✅ | ✅ |
| **老虎机学习** | ✅ | ✅ | ✅ | ✅ |

---

## 🎯 推荐使用场景

### 1️⃣ **Windows EXE** - 最适合：
- ✅ 临床医生快速使用
- ✅ 无需编程背景的用户
- ✅ 单机本地分析
- ✅ 演示和培训

**使用方法：**
```bash
cd packaging/dist-web/SpliceGAIP
双击 SpliceGAIP.exe
```

---

### 2️⃣ **Docker容器** - 最适合：
- ✅ 实验室服务器部署
- ✅ 多用户共享环境
- ✅ 云平台部署（AWS/Azure/GCP）
- ✅ 生产环境稳定性

**使用方法：**
```bash
# 构建
docker build -t splicegaip:latest .

# 运行
docker-compose up -d

# 访问 http://localhost:8501
```

**优势：**
- 环境隔离，不影响宿主机
- 资源限制（CPU/内存）
- 健康检查和自动重启
- 易于版本管理和回滚

---

### 3️⃣ **Snakemake工作流** - 最适合：
- ✅ 学术论文方法复现
- ✅ 大规模批量分析
- ✅ 流程审计和追溯
- ✅ 与其他bioinformatics工具集成

**使用方法：**
```bash
snakemake --cores all --use-conda
```

**输出示例：**
```
results/
└── my-project/
    ├── profile.json              # 数据集概况
    ├── significant_events.tsv    # 显著事件
    ├── ranked_candidates.tsv     # 排序候选
    ├── enrichment.tsv            # 功能富集
    ├── figures/                  # 出版级图表
    │   ├── volcano.png
    │   ├── heatmap.png
    │   └── pathways.png
    ├── evidence.json             # 文献证据
    ├── interpretation.txt        # 生物学解释
    ├── report.html               # HTML报告
    ├── report.pdf                # PDF报告
    └── lab_knowledge.sqlite3     # 知识库
```

**环境导出（论文补充材料）：**
```bash
conda env export > environment.yml
# 或
conda pack -n splicegaip-workflow -o env.zip
```

---

### 4️⃣ **Python包** - 最适合：
- ✅ 开发者定制扩展
- ✅ 集成到其他项目
- ✅ 最新功能测试
- ✅ 贡献代码

**使用方法：**
```bash
git clone https://github.com/your-org/splicegaip.git
cd splicegaip
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python serve_ui.py
```

---

## 🔬 功能完整性对比

| 功能模块 | EXE | Docker | Snakemake | Python |
|---------|-----|--------|-----------|--------|
| **核心分析** | ✅ | ✅ | ✅ | ✅ |
| **自适应阈值(老虎机)** | ✅ | ✅ | ✅ | ✅ |
| **知识持久化** | ✅ | ✅ | ✅ | ✅ |
| **bioservices集成** | ✅ | ✅ | ✅ | ✅ |
| **Ensembl注释** | ✅ | ✅ | ✅ | ✅ |
| **KEGG/Reactome** | ✅ | ✅ | ✅ | ✅ |
| **MCP技能系统** | ✅ | ✅ | ⚠️ 部分 | ✅ |
| **Streamlit UI** | ✅ | ✅ | ❌ CLI only | ✅ |
| **FastAPI后端** | ✅ | ✅ | ❌ | ✅ |
| **回归基准测试** | ✅ | ✅ | ✅ | ✅ |
| **PDF报告生成** | ✅ | ✅ | ✅ | ✅ |
| **HTML交互报告** | ✅ | ✅ | ✅ | ✅ |

---

## 📦 打包技术细节

### Windows EXE (PyInstaller)
```python
# 配置文件: packaging/SpliceGAIP-Web.spec
- 模式: onedir (便于调试)
- 大小: 23MB
- 包含: Python 3.11 + 所有依赖
- 图标: icon.ico
- 启动: serve_ui.py → FastAPI + 自动打开浏览器
```

### Docker镜像
```dockerfile
# 多阶段构建优化大小
Stage 1 (builder): python:3.11-slim + gcc/g++
Stage 2 (runtime): python:3.11-slim + 编译后的包

最终镜像: ~500MB
- 基础系统: ~150MB
- Python依赖: ~300MB
- 应用代码: ~50MB
```

### Snakemake + Conda
```yaml
# workflow/env.yaml
channels:
  - conda-forge
  - bioconda
dependencies:
  - python=3.11
  - pandas, numpy, scipy
  - matplotlib, seaborn, plotly
  - mygene, bioservices
  - autogen-agentchat
  - gseapy
```

---

## 🚀 性能对比

| 指标 | EXE | Docker | Snakemake |
|------|-----|--------|-----------|
| **冷启动时间** | ~5s | ~15s | ~30s (环境激活) |
| **内存占用** | ~500MB | ~600MB | ~450MB |
| **CPU利用率** | 100% | 受限(可配置) | 100% (--cores all) |
| **磁盘I/O** | 直接访问 | volume挂载 | 直接访问 |

---

## 🔄 版本更新策略

### EXE
```bash
# 下载新版本EXE覆盖即可
# 或保留多个版本
SpliceGAIP-v1.0.exe
SpliceGAIP-v1.1.exe
```

### Docker
```bash
# 语义化版本标签
docker pull splicegaip:v1.0.0
docker pull splicegaip:v1.1.0
docker pull splicegaip:latest

# 回滚
docker-compose down
docker-compose up -d splicegaip:v1.0.0
```

### Snakemake
```bash
# Git tag管理
git checkout v1.0.0
snakemake --cores all --use-conda
```

---

## 💡 最佳实践建议

### 临床应用场景
```
推荐: Windows EXE
原因: 零配置、双击即用、适合非技术用户
```

### 实验室研究场景
```
推荐: Docker + Snakemake组合
- Docker用于日常交互式分析
- Snakemake用于论文数据复现
```

### 大规模筛选场景
```
推荐: Snakemake on HPC cluster
原因: 并行处理、资源调度、断点续跑
```

### 云服务部署场景
```
推荐: Docker on Kubernetes/ECS
原因: 自动扩缩容、负载均衡、高可用
```

---

## 📝 快速选择指南

**问：我是临床医生，想快速分析样本**
→ 选 **Windows EXE**

**问：我是研究生，要在实验室服务器跑大量数据**
→ 选 **Docker容器**

**问：我要发论文，需要方法可复现**
→ 选 **Snakemake工作流**

**问：我是开发者，想定制新功能**
→ 选 **Python包开发模式**

---

## 🎓 与BioGAIP的对比

| 特性 | BioGAIP | SpliceGAIP |
|------|---------|------------|
| **容器化** | Docker + Singularity | Docker |
| **沙箱** | Bubblewrap | PyInstaller隔离 |
| **工作流** | Snakemake + Conda | Snakemake + Conda |
| **Windows支持** | .exe | .exe (更轻量) |
| **AI代理** | 基础AutoGen | 增强版+老虎机学习 |
| **知识管理** | ❌ | ✅ SQLite持久化 |
| **外部数据库** | 手动API调用 | bioservices统一接口 |
| **回归测试** | 基础 | 150+自动化测试 |

---

**总结：** SpliceGAIP继承了BioGAIP的容器化理念，但在Windows用户体验、AI智能化和知识管理方面做了显著增强。
