# 发票系统代码重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将 `invoice_system.html` 和 `routes/local_invoice.py` 拆分为职责清晰的模块

**架构：** 前端拆分为 HTML/CSS/JS 分离，后端拆分为 API 路由和服务层

**技术栈：** FastAPI, pdfplumber, rapidocr-onnxruntime

---

## 文件结构

```
fapiao/
├── main.py                        # FastAPI 入口 (修改)
├── routes/
│   ├── __init__.py                # 创建
│   ├── local_invoice.py          # 修改 - 精简 API
│   └── utils.py                   # 创建 - 工具函数
├── static/
│   ├── index.html                 # 创建 (从 invoice_system.html 提取)
│   ├── css/
│   │   └── style.css              # 创建 (从 invoice_system.html 提取)
│   └── js/
│       └── app.js                 # 创建 (从 invoice_system.html 提取)
├── services/
│   └── invoice_parser.py         # 创建 - 发票解析服务
├── images/
│   └── fapiao.png
├── docs/
│   └── refactoring-design.md
├── requirements.txt
└── README.md
```

---

## 实施任务

### Task 1: 创建目录结构和空文件

**Files:**
- Create: `routes/__init__.py`
- Create: `routes/utils.py`
- Create: `services/__init__.py`
- Create: `services/invoice_parser.py`
- Create: `static/css/style.css`
- Create: `static/js/app.js`

- [ ] **Step 1: 创建 routes/__init__.py**

```python
from .local_invoice import local_invoice_routes

__all__ = ["local_invoice_routes"]
```

- [ ] **Step 2: 创建 services/__init__.py**

```python
```

- [ ] **Step 3: 创建空文件**

```bash
touch routes/utils.py services/invoice_parser.py static/css/style.css static/js/app.js
```

- [ ] **Step 4: Commit**

```bash
git add routes/__init__.py routes/utils.py services/__init__.py static/css/style.css static/js/app.js
git commit -m "chore: create directory structure for refactoring"
```

---

### Task 2: 提取 CSS 到 style.css

**Files:**
- Modify: `invoice_system.html:10-820` (删除 `<style>` 块)
- Create: `static/css/style.css` (CSS 内容)

- [ ] **Step 1: 从 invoice_system.html 提取 `<style>` 块到 static/css/style.css**

提取 lines 10-820 的 CSS 内容到 `static/css/style.css`

- [ ] **Step 2: 在 invoice_system.html 中添加 CSS 引用**

在 `<head>` 中添加:
```html
<link rel="stylesheet" href="/static/css/style.css">
```

- [ ] **Step 3: 删除 invoice_system.html 中的 `<style>` 块**

- [ ] **Step 4: 测试 - 确保页面样式正常**

```bash
curl -s http://localhost:8000/static/css/style.css | head -20
```

- [ ] **Step 5: Commit**

```bash
git add static/css/style.css invoice_system.html
git commit -m "refactor: extract CSS to static/css/style.css"
```

---

### Task 3: 提取 JS 到 app.js

**Files:**
- Modify: `invoice_system.html` (删除 `<script>` 块)
- Create: `static/js/app.js` (JS 内容)

- [ ] **Step 1: 从 invoice_system.html 提取 `<script>` 块到 static/js/app.js**

提取 lines 915-1621 的 JS 内容到 `static/js/app.js`

- [ ] **Step 2: 在 invoice_system.html 中添加 JS 引用**

在 `</body>` 前添加:
```html
<script src="/static/js/app.js"></script>
```

- [ ] **Step 3: 删除 invoice_system.html 中的 `<script>` 块 (保留 pdf.js CDN 引用)**

- [ ] **Step 4: 测试 - 确保页面功能正常**

```bash
curl -s http://localhost:8000/static/js/app.js | head -20
```

- [ ] **Step 5: Commit**

```bash
git add static/js/app.js invoice_system.html
git commit -m "refactor: extract JavaScript to static/js/app.js"
```

---

### Task 4: 简化 index.html

**Files:**
- Create: `static/index.html` (精简的 HTML)
- Modify: `main.py` (更新静态文件路径)
- Delete: `invoice_system.html`

- [ ] **Step 1: 将 invoice_system.html 复制为 static/index.html**

```bash
cp invoice_system.html static/index.html
```

- [ ] **Step 2: 修改 main.py 静态文件挂载**

更新为:
```python
app.mount("/static", StaticFiles(directory="static"), name="static")
```

- [ ] **Step 3: 更新 index.html 中的路径引用**

- `/images/fapiao.png` → `/static/images/fapiao.png`
- 或者移动 images 到 static/images/

- [ ] **Step 4: 重命名 invoice_system.html 为 static/index.html**

```bash
git rm invoice_system.html
git add static/index.html
```

- [ ] **Step 5: 更新 main.py 的 FileResponse**

```python
@app.get("/local")
async def local_page():
    return FileResponse("static/index.html")
```

- [ ] **Step 6: 测试 - 访问 http://localhost:8000/local**

- [ ] **Step 7: Commit**

```bash
git add main.py
git mv invoice_system.html static/index.html
git commit -m "refactor: restructure static files to static/ directory"
```

---

### Task 5: 提取工具函数到 routes/utils.py

**Files:**
- Modify: `routes/local_invoice.py`
- Create: `routes/utils.py`

- [ ] **Step 1: 从 local_invoice.py 提取工具函数到 routes/utils.py**

提取:
- `normalize_unicode` 函数
- `get_file_md5` 函数
- `calculate_total` 函数
- 其他辅助函数

- [ ] **Step 2: 在 local_invoice.py 中导入工具函数**

```python
from .utils import normalize_unicode, get_file_md5, calculate_total
```

- [ ] **Step 3: 测试 - 确保功能正常**

- [ ] **Step 4: Commit**

```bash
git add routes/utils.py routes/local_invoice.py
git commit -m "refactor: extract utility functions to routes/utils.py"
```

---

### Task 6: 提取发票解析服务到 services/invoice_parser.py

**Files:**
- Modify: `routes/local_invoice.py`
- Create: `services/invoice_parser.py`

- [ ] **Step 1: 从 local_invoice.py 提取解析逻辑到 services/invoice_parser.py**

提取:
- InvoiceData 数据类
- `parse_pdf_invoice` 函数
- `parse_image_invoice` 函数
- `parse_invoice` 主函数
- 重复检测逻辑

- [ ] **Step 2: 在 local_invoice.py 中导入服务**

```python
from services.invoice_parser import InvoiceData, parse_invoice
```

- [ ] **Step 3: 测试 - 上传发票文件测试解析**

- [ ] **Step 4: Commit**

```bash
git add services/invoice_parser.py routes/local_invoice.py
git commit -m "refactor: extract invoice parsing to services/invoice_parser.py"
```

---

### Task 7: 最终测试和清理

**Files:**
- Modify: `main.py`
- Cleanup: 确保所有路径正确

- [ ] **Step 1: 重启服务测试**

```bash
pkill -f uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 测试所有功能**
- 上传 PDF/图片发票
- 查看发票列表
- 下载 ZIP
- 主题切换

- [ ] **Step 3: 检查 git status**

```bash
git status
```

- [ ] **Step 4: Push to GitHub**

```bash
git push
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: complete code restructuring - separate static files and services"
git push
```
