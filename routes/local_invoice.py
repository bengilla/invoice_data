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
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Side, Font
    from io import BytesIO

    wb = Workbook()
    ws = wb.active
    ws.title = 'invoice'

    # 样式
    title_font = Font(name='微软雅黑', size=16, bold=True)
    label_font = Font(name='微软雅黑', size=10)
    header_font = Font(name='微软雅黑', size=10, bold=True)
    data_font = Font(name='微软雅黑', size=10)
    center = Alignment(horizontal='center', vertical='center')
    left = Alignment(horizontal='left', vertical='center')
    right = Alignment(horizontal='right', vertical='center')
    thin = Side(style='thin')
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)

    # 列宽 (匹配模板)
    ws.column_dimensions['A'].width = 7.3
    ws.column_dimensions['B'].width = 15.6
    ws.column_dimensions['C'].width = 12.3
    ws.column_dimensions['D'].width = 14.1
    ws.column_dimensions['E'].width = 12.3
    ws.column_dimensions['F'].width = 26.0

    # Row 1: 标题 (A1:F1 合并)
    ws.merge_cells('A1:F1')
    ws['A1'].value = '费用报销单（正规通用版）'
    ws['A1'].font = title_font
    ws['A1'].alignment = center
    ws.row_dimensions[1].height = 40

    # Row 2: 报销部门(A2:B2) / 部门值(C2:D2) / 报销日期(E2) / 日期值(F2)
    ws.merge_cells('A2:B2')
    ws['A2'].value = '报销部门：'
    ws['A2'].font = label_font
    ws['A2'].alignment = left
    ws.merge_cells('C2:D2')
    ws['C2'].value = meta.get('department', '')
    ws['C2'].font = data_font
    ws['E2'].value = '报销日期：'
    ws['E2'].font = label_font
    ws['E2'].alignment = right
    ws['F2'].value = meta.get('date', '')
    ws['F2'].font = data_font
    ws.row_dimensions[2].height = 20

    # Row 3: 报销人(A3:B3) / 值(C3:D3) / 所属岗位(E3) / 值(F3)
    ws.merge_cells('A3:B3')
    ws['A3'].value = '报销人：'
    ws['A3'].font = label_font
    ws['A3'].alignment = left
    ws.merge_cells('C3:D3')
    ws['C3'].value = meta.get('name', '')
    ws['C3'].font = data_font
    ws['E3'].value = '所属岗位：'
    ws['E3'].font = label_font
    ws['E3'].alignment = right
    ws['F3'].value = meta.get('position', '')
    ws['F3'].font = data_font
    ws.row_dimensions[3].height = 20

    # Row 4: 事由(A4:B4) / 值(C4:F4)
    ws.merge_cells('A4:B4')
    ws['A4'].value = '事由（用途说明）：'
    ws['A4'].font = label_font
    ws['A4'].alignment = left
    ws.merge_cells('C4:F4')
    ws['C4'].value = meta.get('use', '')
    ws['C4'].font = data_font
    ws.row_dimensions[4].height = 20

    # Row 5: 分隔行 (A5:F5)
    ws.merge_cells('A5:F5')
    ws.row_dimensions[5].height = 25

    # Row 6: 表头
    ws['A6'].value = '序号'
    ws['A6'].font = header_font
    ws['A6'].alignment = center
    ws['A6'].border = border_all
    ws.merge_cells('B6:C6')
    ws['B6'].value = '费用项目'
    ws['B6'].font = header_font
    ws['B6'].alignment = center
    ws['B6'].border = border_all
    ws['C6'].border = border_all
    ws['D6'].value = '金额（元）'
    ws['D6'].font = header_font
    ws['D6'].alignment = center
    ws['D6'].border = border_all
    ws['E6'].value = '票据张数'
    ws['E6'].font = header_font
    ws['E6'].alignment = center
    ws['E6'].border = border_all
    ws['F6'].value = '备注'
    ws['F6'].font = header_font
    ws['F6'].alignment = center
    ws['F6'].border = border_all
    ws.row_dimensions[6].height = 22

    # Row 7-11: 数据行 (最多5条)
    for idx in range(5):
        row = 7 + idx
        inv = invoices[idx] if idx < len(invoices) else None
        ws.row_dimensions[row].height = 22

        ws[f'A{row}'].value = f'{idx+1}.'
        ws[f'A{row}'].font = data_font
        ws[f'A{row}'].alignment = center
        ws[f'A{row}'].border = border_all

        ws.merge_cells(f'B{row}:C{row}')
        ws[f'B{row}'].value = inv.get('company', '') if inv else ''
        ws[f'B{row}'].font = data_font
        ws[f'B{row}'].border = border_all
        ws[f'C{row}'].border = border_all

        amount = inv.get('amount', 0) if inv else ''
        ws[f'D{row}'].value = f'¥{amount:.2f}' if inv else ''
        ws[f'D{row}'].font = data_font
        ws[f'D{row}'].alignment = right
        ws[f'D{row}'].border = border_all

        ws[f'E{row}'].value = inv.get('invoice_no', '') if inv else ''
        ws[f'E{row}'].font = data_font
        ws[f'E{row}'].alignment = center
        ws[f'E{row}'].border = border_all

        ws[f'F{row}'].value = ''
        ws[f'F{row}'].font = data_font
        ws[f'F{row}'].border = border_all

    # Row 12: 合计 (A12:B12 合并=合计: / C12:D12:F12 合并=total)
    ws.merge_cells('A12:B12')
    ws['A12'].value = ''
    ws['A12'].border = border_all
    ws['B12'].border = border_all
    ws['C12'].value = '合计：'
    ws['C12'].font = header_font
    ws['C12'].alignment = right
    ws['C12'].border = border_all
    ws.merge_cells('D12:F12')
    ws['D12'].value = f'¥{total_amount:.2f}'
    ws['D12'].font = header_font
    ws['D12'].alignment = right
    ws['D12'].border = border_all
    ws['E12'].border = border_all
    ws['F12'].border = border_all
    ws.row_dimensions[12].height = 22

    # Row 13: 金额大写 (A13:F13)
    ws.merge_cells('A13:F13')
    ws['A13'].value = f'金额大写：{to_chinese_upper(total_amount)}'
    ws['A13'].font = label_font
    ws['A13'].alignment = left
    ws.row_dimensions[13].height = 25

    # Row 14: 空行
    ws.row_dimensions[14].height = 25

    # Row 15: 附件说明 (A15:F15)
    ws.merge_cells('A15:F15')
    ws['A15'].value = '附件说明：'
    ws['A15'].font = label_font
    ws['A15'].alignment = left
    ws.row_dimensions[15].height = 25

    # Row 16: 发票共 (A16:B16) / total_invoice(C16) / 张(D16:F16)
    ws.merge_cells('A16:B16')
    ws['A16'].value = '发票共'
    ws['A16'].font = label_font
    ws['A16'].alignment = left
    ws['C16'].value = total_invoice
    ws['C16'].font = data_font
    ws['C16'].alignment = center
    ws.merge_cells('D16:F16')
    ws['D16'].value = '张'
    ws['D16'].font = label_font
    ws['D16'].alignment = left
    ws.row_dimensions[16].height = 25

    # Row 17: 其他单据共 (A17:B17) / total_other_invoice(C17) / 张(D17:F17)
    ws.merge_cells('A17:B17')
    ws['A17'].value = '其他单据共'
    ws['A17'].font = label_font
    ws['A17'].alignment = left
    ws['C17'].value = total_other_invoice
    ws['C17'].font = data_font
    ws['C17'].alignment = center
    ws.merge_cells('D17:F17')
    ws['D17'].value = '张'
    ws['D17'].font = label_font
    ws['D17'].alignment = left
    ws.row_dimensions[17].height = 25

    # Row 18: 空行
    ws.row_dimensions[18].height = 25

    # Row 19: 审批签字 (A19:F19)
    ws.merge_cells('A19:F19')
    ws['A19'].value = '审批签字：'
    ws['A19'].font = label_font
    ws['A19'].alignment = left
    ws.row_dimensions[19].height = 25

    # Row 20-23: 签字栏
    sign_items = [
        ('报销人签字：', '部门负责人：'),
        ('财务审核：', '公司负责人：'),
    ]
    for i, (left_text, right_text) in enumerate(sign_items):
        row = 20 + i * 2
        ws.merge_cells(f'A{row}:B{row}')
        ws[f'A{row}'].value = left_text
        ws[f'A{row}'].font = label_font
        ws[f'A{row}'].alignment = left
        ws.merge_cells(f'C{row}:F{row}')
        ws[f'C{row}'].value = right_text
        ws[f'C{row}'].font = label_font
        ws[f'C{row}'].alignment = left
        ws.row_dimensions[row].height = 25
        ws.row_dimensions[row + 1].height = 25

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
