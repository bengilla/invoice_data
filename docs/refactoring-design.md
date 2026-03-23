# 发票系统代码重构设计

## 目标

重构发票系统代码结构，将大型文件拆分为职责清晰的模块。

## 当前状态

| 文件 | 行数 | 问题 |
|------|------|------|
| `invoice_system.html` | 1623 | HTML/CSS/JS 全部混在一起 |
| `routes/local_invoice.py` | 932 | API 逻辑过于集中 |
| `main.py` | 31 | 结构良好 |

## 目标结构

```
fapiao/
├── main.py                        # FastAPI 入口，路由挂载
├── routes/
│   ├── __init__.py
│   ├── local_invoice.py          # 发票相关 API (保留核心接口)
│   └── utils.py                   # PDF/OCR 处理工具函数
├── static/
│   ├── index.html                 # 精简的 HTML 结构
│   ├── css/
│   │   └── style.css              # 样式
│   └── js/
│       └── app.js                 # JavaScript
├── services/
│   └── invoice_parser.py         # 发票解析服务
├── images/
│   └── fapiao.png
├── requirements.txt
└── README.md
```

## 拆分方案

### 1. 前端拆分 (`invoice_system.html` → `static/`)

**`static/index.html`** - 仅包含：
- HTML 骨架
- `<link>` 引用 CSS
- `<script>` 引用 JS

**`static/css/style.css`**：
- 所有 CSS 样式（从当前 `<style>` 块提取）

**`static/js/app.js`**：
- 所有 JavaScript（从当前 `<script>` 块提取）
- 保留全局变量和函数

### 2. 后端拆分 (`routes/local_invoice.py`)

**`routes/local_invoice.py`** - 保留：
- FastAPI 路由定义
- 请求/响应处理
- Session 管理

**`services/invoice_parser.py`** - 移入：
- PDF 解析逻辑
- OCR 图片识别
- 发票数据结构定义
- 重复检测逻辑

**`routes/utils.py`** - 移入：
- 文件处理工具函数
- 金额转换函数
- Unicode 规范化

## 实施步骤

1. 创建目录结构
2. 提取 CSS 到 `static/css/style.css`
3. 提取 JS 到 `static/js/app.js`
4. 简化 `static/index.html`
5. 提取解析服务到 `services/invoice_parser.py`
6. 提取工具函数到 `routes/utils.py`
7. 更新 `main.py` 的静态文件挂载路径
8. 测试确保功能正常

## 注意事项

- 保持所有现有功能不变
- 保持 API 接口兼容
- 相对路径引用资源
