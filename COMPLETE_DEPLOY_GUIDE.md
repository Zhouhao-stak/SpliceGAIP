# SpliceGAIP 完整部署指南

## 当前状态

✅ Docker 镜像已成功构建（包含 Rust 编译器支持）
✅ 容器已启动但缺少应用代码文件
⚠️ 需要完整上传项目文件到服务器

## 问题原因

之前通过 SCP 上传的文件不完整，服务器上缺少：
- `splicegaip/` Python 包目录（所有核心代码）
- `tests/` 测试目录
- 其他关键 Python 文件

## 解决方案（三选一）

### 方案 A：使用 WinSCP 上传完整项目（推荐）

1. **下载 WinSCP**（如果还没有）：https://winscp.net/eng/download.php

2. **连接到服务器**：
   - 主机名：`123.255.66.81`
   - 端口：`39145`
   - 用户名：`wang_zi_wei`
   - 密码：`qazedctgb`
   - 协议：SFTP

3. **上传整个项目**：
   - 本地路径：`E:\SpliceGAIP\`
   - 远程路径：`/home/wang_zi_wei/splicegaip/`
   - 确保勾选"递归复制子目录"
   - 等待上传完成（可能需要几分钟）

4. **重新构建和启动**：
   ```bash
   sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p 39145 wang_zi_wei@123.255.66.81 << 'EOF'
   cd /home/wang_zi_wei/splicegaip
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   EOF
   ```

### 方案 B：创建压缩包上传（更快）

1. **在本地创建压缩包**：
   ```powershell
   cd E:\SpliceGAIP
   tar czf splicegaip-full.tar.gz ^
     --exclude="venv" ^
     --exclude=".pytest_cache" ^
     --exclude="__pycache__" ^
     --exclude="*.pyc" ^
     --exclude=".coverage" ^
     --exclude="SpliceGAIP项目汇报" ^
     --exclude="*.pptx" ^
     .
   ```

2. **使用 WinSCP 上传压缩包**：
   - 上传 `splicegaip-full.tar.gz` 到服务器的 `/home/wang_zi_wei/`

3. **在服务器上解压并重新部署**：
   ```bash
   sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p 39145 wang_zi_wei@123.255.66.81 << 'EOF'
   cd /home/wang_zi_wei
   rm -rf splicegaip
   mkdir splicegaip
   tar xzf splicegaip-full.tar.gz -C splicegaip
   cd splicegaip
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   EOF
   ```

### 方案 C：使用 rsync（如果可用）

```bash
rsync -avz --exclude='venv' --exclude='.pytest_cache' --exclude='__pycache__' --exclude='*.pyc' --exclude='.coverage' --exclude='SpliceGAIP项目汇报' --exclude='*.pptx' -e "ssh -p 39145" E:\SpliceGAIP\ wang_zi_wei@123.255.66.81:/home/wang_zi_wei/splicegaip/
```

## 验证部署

部署完成后，检查服务是否正常运行：

```bash
sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p 39145 wang_zi_wei@123.255.66.81 << 'EOF'
cd /home/wang_zi_wei/splicegaip

# 检查容器状态
docker compose ps

# 查看日志
docker compose logs --tail=50

# 测试 API 健康端点
curl -s http://localhost:8800/api/health | python3 -m json.tool

# 检查端口监听
netstat -tuln | grep -E '(8800|8501)'
EOF
```

## 访问服务

部署成功后，可以通过以下方式访问：

1. **API 服务**：`http://123.255.66.81:8800`
2. **Streamlit UI**：`http://123.255.66.81:8501`

如果端口未开放，可以使用 SSH 隧道：
```bash
ssh -L 8800:localhost:8800 -L 8501:localhost:8501 -p 39145 wang_zi_wei@123.255.66.81
```

然后在本地浏览器访问：
- API: `http://localhost:8800`
- UI: `http://localhost:8501`

## 配置 API Key

编辑服务器上的 `.env` 文件，添加你的 DeepSeek API Key：

```bash
sshpass -p 'qazedctgb' ssh -o StrictHostKeyChecking=no -p 39145 wang_zi_wei@123.255.66.81 << 'EOF'
cd /home/wang_zi_wei/splicegaip
nano .env
EOF
```

修改以下行：
```
MODEL_API_KEY=sk-your-deepseek-api-key-here
```

然后重启容器：
```bash
docker compose restart
```

## 故障排查

如果遇到问题，检查：

1. **容器日志**：
   ```bash
   docker compose logs
   ```

2. **Docker 镜像**：
   ```bash
   docker images | grep splicegaip
   ```

3. **文件完整性**：
   ```bash
   ls -la /home/wang_zi_wei/splicegaip/splicegaip/
   ls -la /home/wang_zi_wei/splicegaip/run.py
   ```

4. **网络连接**：
   ```bash
   ping 123.255.66.81
   ```

## 下一步

部署成功后，你可以：
1. 访问 Web UI 进行剪接分析
2. 通过 API 提交分析任务
3. 查看生成的报告
4. 配置 PubMed 文献检索（如果需要）
