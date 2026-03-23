"""本地发票处理（无需数据库）"""
import os
import re
import base64
import json
import zipfile
import io
import uuid
import numpy as np
from datetime import datetime
from typing import List

import pdfplumber
from PIL import Image
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse

local_invoice_routes = APIRouter()

TEMP_SESSIONS = {}

OCR_ENGINE = None

def get_ocr_engine():
    global OCR_ENGINE
    if OCR_ENGINE is None:
        from rapidocr_onnxruntime import RapidOCR
        OCR_ENGINE = RapidOCR()
    return OCR_ENGINE


def parse_invoice_image(file_path: str) -> dict:
    """使用OCR解析图片发票"""
    result = {
        "file_name": os.path.basename(file_path),
        "date": None,
        "year": datetime.now().year,
        "month": datetime.now().month,
        "company": "未知",
        "buyer": "未知",
        "amount": 0.0,
        "invoice_no": "",
        "success": False
    }
    
    try:
        ocr = get_ocr_engine()
        img = Image.open(file_path)
        img_array = np.array(img)
        
        ocr_result, elapse = ocr(img_array)
        
        if not ocr_result:
            result["error"] = "未识别到文字"
            return result
        
        text_lines = [line[1] for line in ocr_result]
        text = "\n".join(text_lines)
        
        date_match = re.search(r"(\d{4})年(\d{1,2})[⽉月](\d{1,2})[⽇日]", text)
        if date_match:
            result["year"] = int(date_match.group(1))
            result["month"] = int(date_match.group(2))
            result["date"] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
        
        double_match = re.findall(r'名\s*称[：:]\s*([^\s\n]{2,50})', text)
        if len(double_match) >= 2:
            result["buyer"] = double_match[0].strip()
            result["company"] = double_match[1].strip()
        else:
            lines = text.split('\n')
            for line in lines:
                parts = line.split()
                company_candidates = [p for p in parts if len(p) >= 4 and '公司' in p]
                if len(company_candidates) >= 2:
                    result["buyer"] = company_candidates[0]
                    result["company"] = company_candidates[1]
                    break
        
        # 移除"名称："前缀
        if result["buyer"].startswith('名称：') or result["buyer"].startswith('名称:'):
            result["buyer"] = result["buyer"][3:]
        if result["company"].startswith('名称：') or result["company"].startswith('名称:'):
            result["company"] = result["company"][3:]
        
        # 规范化Unicode字符 - Kangxi radicals转正常中文
        kangxi_map = {'⽂': '文', '⽉': '月', '⽇': '日', '⽕': '火', '⽔': '水'}
        for old, new in kangxi_map.items():
            result["buyer"] = result["buyer"].replace(old, new)
            result["company"] = result["company"].replace(old, new)
        
        amount_match = re.search(r"[小写（(][）)]?\s*[¥￥]?\s*([\d,]+\.?\d*)", text)
        if amount_match:
            amount_str = amount_match.group(1).replace(",", "")
            result["amount"] = float(amount_str)
        
        no_match = re.search(r"发票号码[：:]*\s*(\d+)", text)
        if no_match:
            result["invoice_no"] = no_match.group(1)
        else:
            no20_match = re.search(r"\b(\d{20})\b", text)
            if no20_match:
                result["invoice_no"] = no20_match.group(1)
        
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def parse_invoice_pdf(file_path: str) -> dict:
    """解析单个发票PDF"""
    result = {
        "file_name": os.path.basename(file_path),
        "date": None,
        "year": datetime.now().year,
        "month": datetime.now().month,
        "company": "未知",
        "buyer": "未知",
        "amount": 0.0,
        "invoice_no": "",
        "success": False
    }
    
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        # 提取日期 (2026年03月10日) - 支持月(月/⽉)和日(日/⽇)的多种Unicode字符
        date_match = re.search(r"(\d{4})年(\d{1,2})[⽉月](\d{1,2})[⽇日]", text)
        if date_match:
            result["year"] = int(date_match.group(1))
            result["month"] = int(date_match.group(2))
            result["date"] = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
        
        # 提取公司名称 - 名称：xxx 名称：xxx 格式，取第一个为购方，第二个为销方
        double_match = re.findall(r'名\s*称[：:]\s*([^\s\n]{2,50})', text)
        if len(double_match) >= 2:
            result["buyer"] = double_match[0].strip()
            result["company"] = double_match[1].strip()
        else:
            lines = text.split('\n')
            for line in lines:
                parts = line.split()
                company_candidates = [p for p in parts if len(p) >= 4 and '公司' in p]
                if len(company_candidates) >= 2:
                    result["buyer"] = company_candidates[0]
                    result["company"] = company_candidates[1]
                    break
        
        # 移除"名称："前缀
        if result["buyer"].startswith('名称：') or result["buyer"].startswith('名称:'):
            result["buyer"] = result["buyer"][3:]
        if result["company"].startswith('名称：') or result["company"].startswith('名称:'):
            result["company"] = result["company"][3:]
        
        # 规范化Unicode字符 - Kangxi radicals转正常中文
        kangxi_map = {'⽂': '文', '⽉': '月', '⽇': '日', '⽕': '火', '⽔': '水'}
        for old, new in kangxi_map.items():
            result["buyer"] = result["buyer"].replace(old, new)
            result["company"] = result["company"].replace(old, new)
        
        # 提取金额 - 小写后面的金额
        amount_match = re.search(r"小写[）):]*\s*[¥￥]?\s*([\d]+\.?\d*)", text)
        if amount_match:
            result["amount"] = float(amount_match.group(1))
        
        # 提取发票号码
        no_match = re.search(r"发票号码[：:]*\s*(\d+)", text)
        if no_match:
            result["invoice_no"] = no_match.group(1)
        else:
            no20_match = re.search(r"\b(\d{20})\b", text)
            if no20_match:
                result["invoice_no"] = no20_match.group(1)
        
        result["success"] = True
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


@local_invoice_routes.post("/api/parse-invoices")
async def parse_invoices(files: List[UploadFile] = File(...)):
    """解析上传的发票文件（PDF或图片）"""
    import hashlib
    
    all_invoices = []
    months_data = {}
    duplicate_files = []
    processed_filenames = set()
    processed_hashes = set()
    
    session_id = str(uuid.uuid4())[:8]
    temp_dir = f"/tmp/invoice_{session_id}"
    os.makedirs(temp_dir, exist_ok=True)
    TEMP_SESSIONS[session_id] = temp_dir
    
    print(f"Received {len(files)} files, session: {session_id}")
    
    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.gif'}
    
    try:
        for file in files:
            print(f"Processing file: {file.filename}")
            
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in supported_extensions:
                print(f"Skipping unsupported: {file.filename}")
                continue
            
            # 读取文件内容
            content = await file.read()
            
            # 计算文件哈希
            file_hash = hashlib.md5(content).hexdigest()
            
            # 检查重复 - 文件名重复或内容重复
            if file.filename in processed_filenames:
                duplicate_files.append(file.filename)
                print(f"Duplicate filename skipped: {file.filename}")
                continue
            
            if file_hash in processed_hashes:
                duplicate_files.append(file.filename)
                print(f"Duplicate content skipped: {file.filename}")
                continue
            
            processed_filenames.add(file.filename)
            processed_hashes.add(file_hash)
            
            file_path = os.path.join(temp_dir, file.filename)
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            print(f"Saved: {file_path}")
            
            if ext == '.pdf':
                invoice = parse_invoice_pdf(file_path)
            else:
                invoice = parse_invoice_image(file_path)
            
            if invoice["success"]:
                all_invoices.append(invoice)
                
                key = f"{invoice['year']}-{invoice['month']:02d}"
                if key not in months_data:
                    months_data[key] = {
                        "year": invoice["year"],
                        "month": invoice["month"],
                        "invoices": [],
                        "total": 0.0
                    }
                months_data[key]["invoices"].append(invoice)
                months_data[key]["total"] += invoice["amount"]
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "invoices": all_invoices,
            "months": list(months_data.values()),
            "total_amount": sum(inv["amount"] for inv in all_invoices),
            "duplicates": duplicate_files
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@local_invoice_routes.post("/api/download-month-zip")
async def download_month_zip(data: dict):
    """打包月度发票原件ZIP"""
    from fastapi.responses import StreamingResponse
    import zipfile
    from io import BytesIO
    
    session_id = data.get("session_id")
    year = data.get("year")
    month = data.get("month")
    invoices = data.get("invoices", [])
    total = data.get("total", 0)
    
    if not session_id or session_id not in TEMP_SESSIONS:
        return JSONResponse({"success": False, "error": "Session expired"}, status_code=400)
    
    temp_dir = TEMP_SESSIONS[session_id]
    
    buffer = BytesIO()
    
    try:
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for inv in invoices:
                file_name = inv.get("file_name")
                if not file_name:
                    continue
                
                file_path = os.path.join(temp_dir, file_name)
                
                if os.path.exists(file_path):
                    zip_file.write(file_path, file_name)
        
        buffer.seek(0)
        
        filename = f"{year}-{total:.2f}.zip"
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
        )
    finally:
        pass


@local_invoice_routes.post("/api/download-all-zip")
async def download_all_zip(data: dict):
    """打包全部发票ZIP，按月份分文件夹"""
    from fastapi.responses import StreamingResponse
    import zipfile
    from io import BytesIO
    
    session_id = data.get("session_id")
    months = data.get("months", [])
    total_amount = data.get("total_amount", 0)
    
    if not session_id or session_id not in TEMP_SESSIONS:
        return JSONResponse({"success": False, "error": "Session expired"}, status_code=400)
    
    temp_dir = TEMP_SESSIONS[session_id]
    first_year = months[0].get("year") if months else "2026"
    
    buffer = BytesIO()
    
    try:
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for month_data in months:
                year = month_data.get("year")
                month = month_data.get("month")
                month_total = month_data.get("total", 0)
                invoices = month_data.get("invoices", [])
                
                folder_name = f"{year}.{month:02d}-¥{month_total:.2f}/"
                
                for inv in invoices:
                    file_name = inv.get("file_name")
                    if not file_name:
                        continue
                    
                    file_path = os.path.join(temp_dir, file_name)
                    
                    if os.path.exists(file_path):
                        zip_file.write(file_path, folder_name + file_name)
        
        buffer.seek(0)
        
        filename = f"{first_year}-¥{total_amount:.2f}.zip"
        return StreamingResponse(
            buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
        )
    finally:
        pass


@local_invoice_routes.post("/api/download-month-pdf")
async def download_month_pdf(data: dict):
    """生成月份汇总PDF"""
    from fastapi.responses import StreamingResponse
    
    year = data.get("year")
    month = data.get("month")
    invoices = data.get("invoices", [])
    total = data.get("total", 0)
    
    # 使用reportlab生成PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from io import BytesIO
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 标题
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, height - 20*mm, f"{year}年{month}月发票汇总")
    
    # 统计信息
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, height - 35*mm, f"发票数量: {len(invoices)}")
    c.drawString(20*mm, height - 43*mm, f"总金额: ¥{total:.2f}")
    c.drawString(20*mm, height - 51*mm, f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 表头
    y = height - 65*mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20*mm, y, "日期")
    c.drawString(50*mm, y, "公司")
    c.drawString(120*mm, y, "金额")
    c.drawString(160*mm, y, "发票号")
    
    # 分隔线
    y -= 3*mm
    c.line(20*mm, y, width - 20*mm, y)
    
    # 数据行
    c.setFont("Helvetica", 8)
    y -= 5*mm
    
    for i, inv in enumerate(invoices):
        if y < 30*mm:
            c.showPage()
            y = height - 20*mm
            c.setFont("Helvetica", 8)
        
        # 日期
        c.drawString(20*mm, y, str(inv.get("date", "-")))
        # 公司（截断）
        company = inv.get("company", "-")
        if len(company) > 25:
            company = company[:25] + "..."
        c.drawString(50*mm, y, company)
        # 金额
        c.drawString(120*mm, y, f"¥{inv.get('amount', 0):.2f}")
        # 发票号
        invoice_no = str(inv.get("invoice_no", "-"))
        c.drawString(160*mm, y, invoice_no[:15] if len(invoice_no) > 15 else invoice_no)
        
        y -= 6*mm
    
    c.save()
    buffer.seek(0)
    
    filename = f"{year}-{month:02d}-发票汇总.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )


@local_invoice_routes.post("/api/download-all-pdf")
async def download_all_pdf(data: dict):
    """生成全部发票汇总PDF"""
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from io import BytesIO
    
    months = data.get("months", [])
    total_amount = data.get("total_amount", 0)
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # 标题
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20*mm, height - 20*mm, "发票汇总报告")
    
    # 统计信息
    invoice_count = sum(len(m["invoices"]) for m in months)
    c.setFont("Helvetica", 10)
    c.drawString(20*mm, height - 35*mm, f"发票总数: {invoice_count}")
    c.drawString(20*mm, height - 43*mm, f"总金额: ¥{total_amount:.2f}")
    c.drawString(20*mm, height - 51*mm, f"月份数量: {len(months)}")
    c.drawString(20*mm, height - 59*mm, f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    y = height - 75*mm
    
    for month_data in months:
        if y < 50*mm:
            c.showPage()
            y = height - 20*mm
        
        # 月份标题
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20*mm, y, f"{month_data['year']}年{month_data['month']}月 - 小计: ¥{month_data['total']:.2f} ({len(month_data['invoices'])}张)")
        y -= 8*mm
        
        # 月份内的发票
        c.setFont("Helvetica", 8)
        for inv in month_data["invoices"]:
            if y < 30*mm:
                c.showPage()
                y = height - 20*mm
                c.setFont("Helvetica", 8)
            
            company = inv.get("company", "-")
            if len(company) > 30:
                company = company[:30] + "..."
            
            c.drawString(25*mm, y, f"{inv.get('date', '-')} | {company} | ¥{inv.get('amount', 0):.2f}")
            y -= 5*mm
        
        y -= 3*mm
    
    c.save()
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''发票汇总报告.pdf"}
    )
