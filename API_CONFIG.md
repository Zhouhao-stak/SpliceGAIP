# DeepSeek API 配置指南

## 快速开始

### 方式一：编辑 `.env` 文件（推荐）

1. 打开项目根目录的 `.env` 文件
2. 将 `MODEL_API_KEY=sk-YOUR_API_KEY_HERE` 替换为你的真实密钥
3. 保存后重启程序

**获取 API 密钥：** https://platform.deepseek.com

### 方式二：通过 Web 界面配置

1. 启动 SpliceGAIP
2. 点击左侧菜单 "AI 解读" → "模型配置"
3. 选择预设 "DeepSeek V4.1-Flash"
4. 填入你的 API Key
5. 点击保存

## 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `MODEL_API_BASE_URL` | API 端点地址 | `https://api.deepseek.com` |
| `MODEL_NAME` | 模型名称 | `deepseek-flash` |
| `MODEL_API_KEY` | **你的 API 密钥（必填）** | - |
| `MODEL_THINKING` | 推理模式 | `auto`（智能切换） |
| `MODEL_REASONING_EFFORT` | 推理强度 | `low` |

## Thinking 模式说明

- **auto**（推荐）：工具调用时自动关闭，报告解读时开启
- **disabled**：全部关闭，速度最快，temperature 生效
- **enabled**：全部开启，最慢但叙述更严谨

## 支持的其他模型

可在 `.env` 中修改 `MODEL_API_BASE_URL` 和 `MODEL_NAME`：

- **OpenAI**: `https://api.openai.com/v1` + `gpt-4o-mini`
- **月之暗面**: `https://api.moonshot.cn/v1` + `moonshot-v1-32k`
- **阿里云百炼**: `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen-plus`

## 离线模式

如果不配置 API 密钥，程序会自动降级到**离线确定性模式**：
- ✅ 分析结果完全一致
- ❌ 没有 AI 解读、基因注释、假设生成等增强功能

## 安全提示

- `.env` 文件包含敏感信息，**不要**提交到 Git
- 已添加到 `.gitignore`，不会被版本控制追踪
- 建议定期轮换 API 密钥
