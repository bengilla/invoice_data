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

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "_sample", "invoice_sample.xls")

CN_NUMS = ['零','壹','贰','叁','肆','伍','陆','柒','捌','玖']
CN_INT_RADICE = ['','拾','佰','仟']
CN_INT_UNITS = ['','万','亿','兆']
CN_DEC_UNITS = ['角','分']


def to_chinese_upper(amount):
    integer_num = int(amount)
    decimal_num = round((amount - integer_num) * 100)
    s = ''
    if integer_num == 0:
        s = CN_NUMS[0]
    else:
        zero_count = 0
        int_str = str(integer_num)
        int_len = len(int_str)
        for i in range(int_len):
            n = int(int_str[i])
            p = int_len - i - 1
            quotient = p // 4
            modulus = p % 4
            if n == 0:
                zero_count += 1
            else:
                if zero_count > 0:
                    s += CN_NUMS[0]
                zero_count = 0
                s += CN_NUMS[n] + CN_INT_RADICE[modulus]
            if modulus == 0 and zero_count < 4:
                s += CN_INT_UNITS[quotient]
    s += '元'
    if decimal_num == 0:
        s += '整'
    else:
        jiao = decimal_num // 10
        fen = decimal_num % 10
        if jiao > 0:
            s += CN_NUMS[jiao] + CN_DEC_UNITS[0]
        if fen > 0:
            s += CN_NUMS[fen] + CN_DEC_UNITS[1]
    return '人民币 ' + s


def generate_excel(meta, invoices, total_amount, total_invoice, total_other_invoice):
    import xlrd
    from openpyxl import load_workbook
    from io import BytesIO

    # 先用xlrd读取.xls模板，转存为.xlsx供openpyxl使用
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Side, Font

    rb = xlrd.open_workbook(TEMPLATE_PATH, formatting_info=True)
    rs = rb.sheet_by_index(0)

    wb = Workbook()
    ws = wb.active
    ws.title = 'invoice'

    # 复制数据和基本格式
    for r in range(rs.nrows):
        for c in range(rs.ncols):
            cell = rs.cell(r, c)
            new_cell = ws.cell(row=r+1, column=c+1, value=cell.value)
            new_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # 数据映射: (row, col) - 0-indexed转1-indexed
    data_map = {
        'department': (2, 3),
        'date': (2, 6),
        'name': (3, 3),
        'position': (3, 6),
        'chinese_price': (13, 1),
        'total_invoice': (16, 3),
        'total_other_invoice': (17, 3),
        'total': (12, 4),
    }

    for key, (r, c) in data_map.items():
        val = meta.get(key)
        if val is not None:
            ws.cell(row=r, column=c, value=val)

    # 填充发票数据到item行 (row 7-11, 1-indexed对应6-10的0-indexed数据行)
    for i, inv in enumerate(invoices[:5]):
        row = 7 + i  # 1-indexed: row 7 = item1
        company = inv.get('company', '')
        amount = inv.get('amount', 0)
        inv_no = inv.get('invoice_no', '')
        ws.cell(row=row, column=2, value=company)
        ws.cell(row=row, column=4, value=amount)
        ws.cell(row=row, column=5, value=inv_no)

    # 合计
    ws.cell(row=12, column=4, value=total_amount)

    # 大写金额
    ws.cell(row=13, column=1, value=f'金额大写：{to_chinese_upper(total_amount)}')

    # 发票数
    ws.cell(row=16, column=3, value=total_invoice)
    ws.cell(row=17, column=3, value=total_other_invoice)

    # 调整列宽
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max(max_len + 2, 10)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf

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
    meta = data.get("meta", {})

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

            # 生成Excel报销单
            try:
                meta["total"] = total
                meta["chinese_price"] = f'金额大写：{to_chinese_upper(total)}'
                meta["total_invoice"] = len(invoices)
                meta["total_other_invoice"] = data.get("total_other_invoice", 0)
                excel_buf = generate_excel(meta, invoices, total, len(invoices), meta["total_other_invoice"])
                zip_file.writestr("费用报销单.xlsx", excel_buf.read())
                print("Excel added to ZIP successfully")
            except Exception as e:
                print(f"Excel generation failed: {e}")
                import traceback
                traceback.print_exc()

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
    meta = data.get("meta", {})

    if not session_id or session_id not in TEMP_SESSIONS:
        return JSONResponse({"success": False, "error": "Session expired"}, status_code=400)

    temp_dir = TEMP_SESSIONS[session_id]
    first_year = months[0].get("year") if months else "2026"

    # 收集全部发票
    all_invoices = []
    for m in months:
        all_invoices.extend(m.get("invoices", []))

    buffer = BytesIO()

    try:
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for month_data in months:
                year = month_data.get("year")
                month = month_data.get("month")
                month_total = month_data.get("total", 0)
                invoices = month_data.get("invoices", [])

                folder_name = f"{year}.{month:02d}（{len(invoices)}张发票）-¥{month_total:.2f}/"

                for inv in invoices:
                    file_name = inv.get("file_name")
                    if not file_name:
                        continue

                    file_path = os.path.join(temp_dir, file_name)

                    if os.path.exists(file_path):
                        zip_file.write(file_path, folder_name + file_name)

            # 生成Excel报销单
            try:
                meta["total"] = total_amount
                meta["chinese_price"] = f'金额大写：{to_chinese_upper(total_amount)}'
                meta["total_invoice"] = len(all_invoices)
                meta["total_other_invoice"] = data.get("total_other_invoice", 0)
                excel_buf = generate_excel(meta, all_invoices, total_amount, len(all_invoices), meta["total_other_invoice"])
                zip_file.writestr("费用报销单.xlsx", excel_buf.read())
                print("Excel added to ZIP successfully")
            except Exception as e:
                print(f"Excel generation failed: {e}")
                import traceback
                traceback.print_exc()

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
