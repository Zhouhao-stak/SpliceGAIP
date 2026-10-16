# SpliceGAIP 图标设计说明

## 设计理念

SpliceGAIP 的图标融合了两个核心概念：

### 1. DNA双螺旋结构（青色 #00B4D8）
- 代表RNA剪接分析的核心功能
- 简化的现代风格，确保在小尺寸下依然清晰可辨
- 象征生物信息学和基因组学研究

### 2. AI神经网络网络（紫色 #7B2CBF）
- 代表多智能体AI系统
- 节点和连接线与DNA结构自然融合
- 体现人工智能驱动的自动化分析流程

### 3. 圆角方形背景
- 现代应用图标设计风格
- 从青色到紫色的渐变背景
- 白色前景元素提供高对比度

## 技术规格

### 源文件
- **格式**: PNG (1024x1024)
- **位置**: `packaging/icon_source.png`

### Windows ICO文件
- **格式**: ICO (包含多个尺寸)
- **位置**: `packaging/icon.ico`
- **包含尺寸**: 256x256, 128x128, 64x64, 48x48, 32x32, 16x16
- **用途**: EXE文件嵌入图标

### 应用场景
- Windows资源管理器中的EXE文件显示
- 桌面快捷方式图标
- 任务栏图标
- Alt+Tab切换窗口图标

## 颜色方案

| 元素 | 颜色代码 | 用途 |
|------|---------|------|
| DNA螺旋 | #00B4D8 (青蓝) | 生物科技、数据流 |
| 神经网络 | #7B2CBF (紫色) | AI智能、深度学习 |
| 背景渐变 | 青→紫 | 科技与智能融合 |
| 前景元素 | 白色 | 高对比度、清晰可见 |

## 打包配置

所有三个PyInstaller spec文件已更新为使用此图标：

1. **SpliceGAIP.spec** - CLI命令行版本
2. **SpliceGAIP-Web.spec** - Web版（onedir）
3. **SpliceGAIP-Web-OneFile.spec** - Web版（单文件）✅ 已构建

配置代码示例：
```python
exe = EXE(
    ...
    icon=os.path.join(HERE, "icon.ico"),
)
```

## 重新生成图标

如需修改图标设计：

1. 使用AI图像生成工具创建新设计（1024x1024 PNG）
2. 使用PowerShell转换为ICO格式：
   ```powershell
   Add-Type -AssemblyName System.Drawing
   $bitmap = [System.Drawing.Bitmap]::FromFile("new_icon.png")
   $icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
   $stream = New-Object System.IO.FileStream("icon.ico", 'Create')
   $icon.Save($stream)
   $stream.Close()
   ```
3. 重新运行PyInstaller打包命令

## 版权说明

图标由AI生成，专为SpliceGAIP项目设计。
项目遵循AGPL-3.0许可证。
