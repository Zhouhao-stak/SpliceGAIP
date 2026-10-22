#  Coolify 5 分钟快速部署

> 在你的服务器上实现类似扣子（Coze）的一键部署体验

---

##  前置条件

- ✅ 一台 Linux 服务器（Ubuntu/Debian，2核4G+）
- ✅ 一个域名（可选，但推荐）
- ✅ SSH 访问权限

---

##  部署步骤

### 第 1 步：安装 Coolify（2 分钟）

```bash
# SSH 登录到你的服务器
ssh root@your-server-ip

# 一键安装 Coolify
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
```

等待 3-5 分钟，安装完成后访问：
```
https://your-server-ip:8000
```

---

### 第 2 步：配置 SpliceGAIP 项目（2 分钟）

**在 Coolify Web UI 中操作**：

1. **连接 GitHub**
   - Sources → Add Source → GitHub
   - 授权访问你的 SpliceGAIP 仓库

2. **创建项目**
   - Projects → Add Project
   - Name: `SpliceGAIP`
   - Source: 选择你的仓库
   - Branch: `main`

3. **配置环境变量**
   ```bash
   # 必填
   DEEPSEEK_API_KEY=sk-your-key-here

   # 推荐
   SPLICEGAIP_ENABLE_PUBMED=true
   SPLICEGAIP_LOG_LEVEL=INFO
   SPLICEGAIP_API_KEY=<生成随机密钥>
   ```

---

### 第 3 步：首次部署（1 分钟）

**方式 A：手动部署**
- 点击 "Deploy" 按钮

**方式 B：自动部署（推荐）**
```bash
# 本地推送代码，Coolify 自动部署！
git push origin main
```

---

## ✨ 部署完成！

访问你的应用：
```
https://splicegaip.your-domain.com
```

**享受的功能**：
- 🎯 Web 管理界面
- 📊 实时日志和监控
- 🔒 自动 HTTPS
- 🔄 Git push 自动部署
- 💾 自动备份

---

## 📚 详细文档

- [完整部署指南](DEPLOY_COOLIFY.md)
- [架构对比](DEPLOYMENT_WORKFLOW.md)
- [故障排查](DEPLOY_COOLIFY.md#故障排查)

---

## 💡 提示

**首次部署后**：
1. 立即测试 API：`curl https://your-domain.com/api/health`
2. 备份 `.env.production` 文件
3. 配置自动备份（Coolify → Backups）

**日常使用**：
- 修改代码 → `git push` → 自动部署
- 查看日志 → Coolify Web UI → Logs
- 重启服务 → Coolify Web UI → Restart

---

**就这么简单！** 🎉

有问题？查看 [DEPLOY_COOLIFY.md](DEPLOY_COOLIFY.md) 获取详细说明。
