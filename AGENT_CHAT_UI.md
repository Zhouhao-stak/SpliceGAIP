# Agent对话面板功能说明 (v4)

## 新增功能概述

基于BioAgents的设计理念，SpliceGAIP v4新增了**Agent实时对话面板**和**日志查看器**，让用户能够：
1. 看到Agent的思考过程和决策逻辑
2. 与Agent进行自然语言交互
3. 实时监控分析进度和系统状态

---

## 界面布局

### 双栏设计（AI流水线页面）

```
┌─────────────────────┬──────────────────────┐
│                     │                      │
│   左侧：工作流进度    │   右侧：Agent对话     │
│   - 分析进度条       │   - 对话消息列表      │
│   - 6个Agent步骤     │   - 用户输入框        │
│                     │   - 清空按钮          │
│                     │                      │
└─────────────────────┴──────────────────────┘
┌────────────────────────────────────────────
│              底部：实时日志面板               │
│  - 自动滚动开关  - 清空按钮  - 日志内容       │
└────────────────────────────────────────────┘
```

---

## 核心功能

### 1. Agent对话面板

**位置**: AI流水线页面 → 右栏

**功能**:
- 📝 **显示Agent消息** - 每个Agent的操作都会以对话形式展示
- 💬 **用户提问** - 可在输入框中向Agent提问或下达指令
- ⏰ **时间戳** - 每条消息都有精确的时间记录
-  **角色区分** - 不同Agent有不同的图标和名称标识
- 🗑️ **清空对话** - 一键清除所有历史消息

**消息类型**:
- `system` - 系统通知（灰色边框）
- `agent` - Agent回复（黑色左边框）
- `user` - 用户消息（黑色右边框）

**示例对话**:
```
️ 系统 [14:30]
准备就绪。上传数据后，Agent将开始协作分析...

🤖 数据Agent [14:32]
正在验证BAM文件格式...
检测到3个样本，总计45M reads

🧠 推理Agent [14:33]
数据质量良好，开始质控流程...

 用户 [14:35]
为什么这个基因的FDR这么低？

🤖 注释Agent [14:35]
正在查询文献数据库...
```

---

### 2. 实时日志面板

**位置**: AI流水线页面 → 底部

**功能**:
- 📋 **实时日志流** - 显示所有系统事件和操作记录
- 🔄 **自动滚动** - 可开关，开启时自动显示最新日志
- 🎨 **颜色编码** - 不同级别的日志用不同颜色显示
  - 灰色: 普通信息 (info)
  - 黑色: 成功操作 (success)
  - 橙色: 警告 (warning)
  - 红色: 错误 (error)
- 🗑️ **清空日志** - 一键清除所有日志

**日志格式**:
```
[14:30:25] [系统] SpliceGAIP v4.0 已启动 - Agent对话增强版
[14:32:10] [数据Agent] 开始验证文件: sample1.bam
[14:32:15] [数据Agent] ✓ 文件格式正确
[14:33:00] [工作流] 质控Agent - 运行中
```

---

### 3. Agent工作流状态更新

**改进点**:
- ✅ 更紧凑的进度条（6px高度，纯黑填充）
- ✅ 简化的状态文字（16px标题，12px副标题）
- ✅ 实时状态同步到对话面板和日志

**状态流转**:
```
等待中 → 运行中 → 已完成/失败
  ↓         ↓         ↓
灰色      黑色      绿色/红色
```

---

## JavaScript API

### 对话相关函数

```javascript
// 添加对话消息
addChatMessage(agentName, message, type = 'agent', icon = '🤖')

// 示例
addChatMessage('数据Agent', '正在加载文件...', 'agent', '')
addChatMessage('用户', '帮我分析一下', 'user', '👤')

// 清空对话
clearChat()

// 发送用户消息
sendUserMessage()
```

### 日志相关函数

```javascript
// 添加日志条目
addLogEntry(source, message, level = 'info')

// 示例
addLogEntry('数据Agent', '文件验证通过', 'success')
addLogEntry('系统', '发生错误', 'error')

// 清空日志
clearLogs()

// 切换自动滚动
toggleAutoScroll()
```

### 工作流相关函数

```javascript
// 更新单个步骤状态
updatePipelineStep(stepIndex, status, progress = 0)

// 示例
updatePipelineStep(0, 'running')  // 数据Agent运行中
updatePipelineStep(0, 'completed') // 数据Agent完成

// 更新整体进度
updateProgress(percent, statusText)

// 示例
updateProgress(50, '正在进行剪接检测...')
```

---

## 使用场景

### 场景1: 监控分析进度
用户上传数据后，可以：
1. 在左侧看进度条和工作流步骤
2. 在右侧看Agent的实时对话
3. 在底部看详细的操作日志

### 场景2: 交互式分析
用户可以：
1. 在对话面板输入："为什么选择这个FDR阈值？"
2. Agent回复解释推理过程
3. 用户可以继续追问或调整参数

### 场景3: 问题诊断
当分析出现问题时：
1. 查看日志面板的错误信息
2. 在对话中询问Agent具体问题
3. Agent提供解决方案建议

---

## 技术实现

### 前端架构
- **HTML结构**: 双栏Grid布局 + 底部日志区
- **CSS样式**: 专业极简配色（黑白灰）
- **JavaScript**: 模块化设计 (`agent_chat_ui.js`)

### 数据流
```
用户操作 → JS函数 → DOM更新 → 界面刷新
   ↓
后端API (未来扩展) → WebSocket/轮询 → 实时更新
```

### 当前限制
- ️ 对话功能为前端模拟（演示版）
- ⚠️ 未连接真实LLM后端
- ️ Agent响应为预设模板

### 未来扩展
- ✅ 接入真实LLM API
- ✅ WebSocket实时通信
- ✅ 多轮对话上下文记忆
- ✅ Agent协作可视化

---

## 版本对比

| 特性 | v3 (专业UI) | v4 (Agent对话) |
|------|------------|---------------|
| 配色方案 | 黑白灰 | 黑白灰 (保持) |
| 布局 | 单栏工作流 | 双栏 (工作流+对话) |
| 进度显示 | 进度条 | 进度条 + 对话 + 日志 |
| 用户交互 | 被动观察 | 主动提问 |
| Agent透明度 | 低 | 高 (可见思考过程) |
| 文件大小 | 26MB | 26MB |

---

## 回滚指南

如需回退到v3（无对话面板版本）：

```bash
cd E:/SpliceGAIP
git checkout v3-professional-ui -- splicegaip/interface/
```

然后重新打包：
```bash
./venv/Scripts/python.exe -m PyInstaller packaging/SpliceGAIP-Web.spec \
  --distpath packaging/dist-rollback --workpath packaging/build-rollback
```

---

**创建日期**: 2026-10-16
**维护者**: SpliceGAIP Team
**参考设计**: BioAgents (Nature Scientific Reports, 2025)
