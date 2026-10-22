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

## 运行时安全与日志

API 默认保持本机开发的兼容行为；当服务需要被局域网或反向代理访问时，建议设置 API Key：

```dotenv
SPLICEGAIP_API_KEY=替换为随机长字符串
```

设置后，除 `/api/health` 外的 `/api/*` 请求必须携带下面任一种认证头：

```http
X-API-Key: <your-key>
```

或：

```http
Authorization: Bearer <your-key>
```

未配置 `SPLICEGAIP_API_KEY` 时不会强制认证，适合本机启动和桌面 EXE 场景。当前浏览器 UI 不会自动读取服务器密钥；若需要保护浏览器 UI，请在反向代理层做认证，或保持 API Key 未配置并限制服务只监听本机。不要把密钥提交到 Git；生产环境应通过环境变量或未纳入版本控制的 `.env` 文件注入。

每个请求都会返回 `X-Request-ID`，并写入结构化 JSON 日志。默认日志位置为运行时目录下的 `logs/splicegaip.log`，支持轮转；可通过以下变量覆盖：

```dotenv
SPLICEGAIP_LOG_LEVEL=INFO
SPLICEGAIP_LOG_FILE=/path/to/splicegaip.log
SPLICEGAIP_RATE_LIMIT=120
```

`SPLICEGAIP_RATE_LIMIT` 是每个客户端 IP 每 60 秒允许的 API 请求数，默认 `0`（关闭）。超过限制返回 `429` 和 `Retry-After`；健康探针不计入限流。日志不会记录 API Key、Authorization 头或完整请求体。
