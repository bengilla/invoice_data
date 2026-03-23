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

from .utils import (
    normalize_unicode,
    get_file_md5,
    to_chinese_upper,
    generate_excel,
    get_ocr_engine,
    parse_invoice_image,
    parse_invoice_pdf,
)

local_invoice_routes = APIRouter()

TEMP_SESSIONS = {}


@local_invoice_routes.post("/api/parse-invoices")
async def parse_invoices(files: List[UploadFile] = File(...)):
    """解析上传的发票文件（PDF或图片）"""
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

    supported_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".gif"}

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
            file_hash = get_file_md5(content)

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

            if ext == ".pdf":
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
                        "total": 0.0,
                    }
                months_data[key]["invoices"].append(invoice)
                months_data[key]["total"] += invoice["amount"]

        return JSONResponse(
            {
                "success": True,
                "session_id": session_id,
                "invoices": all_invoices,
                "months": list(months_data.values()),
                "total_amount": sum(inv["amount"] for inv in all_invoices),
                "duplicates": duplicate_files,
            }
        )

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


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
        return JSONResponse(
            {"success": False, "error": "Session expired"}, status_code=400
        )

    temp_dir = TEMP_SESSIONS[session_id]

    buffer = BytesIO()

    try:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
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
                meta["chinese_price"] = f"金额大写：{to_chinese_upper(total)}"
                meta["total_invoice"] = len(invoices)
                meta["total_other_invoice"] = data.get("total_other_invoice", 0)
                excel_buf = generate_excel(
                    meta, invoices, total, len(invoices), meta["total_other_invoice"]
                )
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
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
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
        return JSONResponse(
            {"success": False, "error": "Session expired"}, status_code=400
        )

    temp_dir = TEMP_SESSIONS[session_id]
    first_year = months[0].get("year") if months else "2026"

    # 收集全部发票
    all_invoices = []
    for m in months:
        all_invoices.extend(m.get("invoices", []))

    buffer = BytesIO()

    try:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for month_data in months:
                year = month_data.get("year")
                month = month_data.get("month")
                month_total = month_data.get("total", 0)
                invoices = month_data.get("invoices", [])

                folder_name = (
                    f"{year}.{month:02d}（{len(invoices)}张发票）-¥{month_total:.2f}/"
                )

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
                meta["chinese_price"] = f"金额大写：{to_chinese_upper(total_amount)}"
                meta["total_invoice"] = len(all_invoices)
                meta["total_other_invoice"] = data.get("total_other_invoice", 0)
                excel_buf = generate_excel(
                    meta,
                    all_invoices,
                    total_amount,
                    len(all_invoices),
                    meta["total_other_invoice"],
                )
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
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
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
    c.drawString(20 * mm, height - 20 * mm, f"{year}年{month}月发票汇总")

    # 统计信息
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 35 * mm, f"发票数量: {len(invoices)}")
    c.drawString(20 * mm, height - 43 * mm, f"总金额: ¥{total:.2f}")
    c.drawString(
        20 * mm,
        height - 51 * mm,
        f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    # 表头
    y = height - 65 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(20 * mm, y, "日期")
    c.drawString(50 * mm, y, "公司")
    c.drawString(120 * mm, y, "金额")
    c.drawString(160 * mm, y, "发票号")

    # 分隔线
    y -= 3 * mm
    c.line(20 * mm, y, width - 20 * mm, y)

    # 数据行
    c.setFont("Helvetica", 8)
    y -= 5 * mm

    for i, inv in enumerate(invoices):
        if y < 30 * mm:
            c.showPage()
            y = height - 20 * mm
            c.setFont("Helvetica", 8)

        # 日期
        c.drawString(20 * mm, y, str(inv.get("date", "-")))
        # 公司（截断）
        company = inv.get("company", "-")
        if len(company) > 25:
            company = company[:25] + "..."
        c.drawString(50 * mm, y, company)
        # 金额
        c.drawString(120 * mm, y, f"¥{inv.get('amount', 0):.2f}")
        # 发票号
        invoice_no = str(inv.get("invoice_no", "-"))
        c.drawString(
            160 * mm, y, invoice_no[:15] if len(invoice_no) > 15 else invoice_no
        )

        y -= 6 * mm

    c.save()
    buffer.seek(0)

    filename = f"{year}-{month:02d}-发票汇总.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
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
    c.drawString(20 * mm, height - 20 * mm, "发票汇总报告")

    # 统计信息
    invoice_count = sum(len(m["invoices"]) for m in months)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 35 * mm, f"发票总数: {invoice_count}")
    c.drawString(20 * mm, height - 43 * mm, f"总金额: ¥{total_amount:.2f}")
    c.drawString(20 * mm, height - 51 * mm, f"月份数量: {len(months)}")
    c.drawString(
        20 * mm,
        height - 59 * mm,
        f"生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )

    y = height - 75 * mm

    for month_data in months:
        if y < 50 * mm:
            c.showPage()
            y = height - 20 * mm

        # 月份标题
        c.setFont("Helvetica-Bold", 11)
        c.drawString(
            20 * mm,
            y,
            f"{month_data['year']}年{month_data['month']}月 - 小计: ¥{month_data['total']:.2f} ({len(month_data['invoices'])}张)",
        )
        y -= 8 * mm

        # 月份内的发票
        c.setFont("Helvetica", 8)
        for inv in month_data["invoices"]:
            if y < 30 * mm:
                c.showPage()
                y = height - 20 * mm
                c.setFont("Helvetica", 8)

            company = inv.get("company", "-")
            if len(company) > 30:
                company = company[:30] + "..."

            c.drawString(
                25 * mm,
                y,
                f"{inv.get('date', '-')} | {company} | ¥{inv.get('amount', 0):.2f}",
            )
            y -= 5 * mm

        y -= 3 * mm

    c.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''发票汇总报告.pdf"
        },
    )
