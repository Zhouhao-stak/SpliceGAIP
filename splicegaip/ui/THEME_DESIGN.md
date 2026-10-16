# SpliceGAIP UI Design System

## 专业极简主义主题 (Professional Minimalist)

基于SpaceX设计理念的克制、专业UI风格。

---

## 🎨 设计原则

### 1. **克制用色**
- ✅ 纯黑白灰单色系
- ❌ 无彩色点缀
- 专注内容本身

### 2. **系统字体**
- 使用操作系统原生字体
- macOS: -apple-system, SF Pro
- Windows: Segoe UI
- Linux: Roboto / Sans-serif
- 代码: SF Mono / Monaco / Consolas

### 3. **极简Chrome**
- 最少的边框和装饰
- 细线分隔（hairline）
- 充足的留白

### 4. **清晰层次**
- 标题：600字重，紧凑字距
- 正文：15px，1.6行高
- 辅助文字：13px，灰色

---

## 📐 设计规范

### 色彩系统

```css
--black:     #000000  /* 主要文字 */
--gray-900:  #1a1a1a  /* 深色文字 */
--gray-700:  #4a4a4a  /* 正文 */
--gray-500:  #8a8a8a  /* 次要文字 */
--gray-300:  #d0d0d0  /* 边框 */
--gray-100:  #f5f5f5  /* 背景 */
--white:     #ffffff  /* 主背景 */
```

### 间距系统

```
--space-1:  4px   (超小)
--space-2:  8px   (小)
--space-3:  12px  (中小)
--space-4:  16px  (中)
--space-5:  24px  (大)
--space-6:  32px  (超大)
--space-7:  48px  (巨大)
--space-8:  64px  (超巨大)
```

### 圆角

```
默认按钮:    4px
卡片:        6px
输入框:      4px
```

---

## 🧩 组件样式

### 按钮

**主要按钮**
```css
background: #000000;
color: #ffffff;
border: 1px solid #000000;
padding: 10px 20px;
font-size: 14px;
font-weight: 500;
```

**次要按钮**
```css
background: transparent;
color: #1a1a1a;
border: 1px solid #d0d0d0;
```

### 卡片

```css
background: #ffffff;
border: 1px solid #f5f5f5;
border-radius: 6px;
padding: 16px;
```

### 表格

```css
/* 表头 */
th {
    background: #f5f5f5;
    font-weight: 600;
    border-bottom: 2px solid #d0d0d0;
}

/* 数据行 */
td {
    border-bottom: 1px solid #f5f5f5;
}

/* 悬停效果 */
tr:hover {
    background: #f5f5f5;
}
```

### 指标显示

```css
/* 数值 */
metric-value {
    font-size: 28px;
    font-weight: 600;
    color: #000000;
}

/* 标签 */
metric-label {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8a8a8a;
}
```

---

## 🚀 应用方法

### Streamlit应用

```python
from splicegaip.ui.theme_professional import apply_professional_theme

apply_professional_theme()
```

### 辅助函数

```python
# 章节标题
section_header("分析结果", "候选基因列表")

# 辅助文字
muted("最后更新: 2026-10-15")

# 等宽字体（ID、代码）
mono("GENE001")
```

---

## 📊 与SpaceX原版对比

| 特性 | SpaceX原版 | SpliceGAIP专业版 |
|------|-----------|-----------------|
| 背景色 | 纯黑 #000 | 纯白 #fff |
| 文字色 | 白色 | 深灰 #1a1a1a |
| 适用场景 | 营销网站 | 数据分析工具 |
| 字体 | D-DIN | 系统字体 |
| 按钮 | 幽灵轮廓 | 实心黑色 |
| 共同点 | 极简、克制 | 极简、克制 |

---

## 💡 为什么选择白色而非黑色？

虽然SpaceX使用纯黑背景，但对于**数据分析工具**：

1. **可读性**: 长时间阅读深色背景上的浅色文字会疲劳
2. **专业性**: 学术论文、报告都是白底黑字
3. **打印友好**: 用户可能需要打印结果
4. **习惯**: 科研人员熟悉PubMed、NCBI等白底界面

我们保留了SpaceX的**极简精神**，但调整为更适合科研工作的配色。

---

## 🔧 自定义

如需调整颜色或间距，编辑 `theme_professional.py` 中的CSS变量：

```python
:root {
    --gray-700: #4a4a4a;  /* 改为更浅/深的灰色 */
    --space-4: 16px;      /* 调整基础间距 */
}
```

---

## 📝 示例页面

查看实际效果：
```bash
cd E:\SpliceGAIP
streamlit run splicegaip/interface/streamlit_app.py
```

所有组件会自动应用专业主题，无需额外配置。
