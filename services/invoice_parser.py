"""发票解析服务"""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Set, Tuple

import numpy as np
import pdfplumber
from PIL import Image


@dataclass
class InvoiceData:
    """发票数据类"""
    file_name: str = ""
    date: Optional[str] = None
    year: int = field(default_factory=lambda: datetime.now().year)
    month: int = field(default_factory=lambda: datetime.now().month)
    company: str = ""
    buyer: str = "未知"
    amount: float = 0.0
    invoice_no: str = ""
    success: bool = False
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "file_name": self.file_name,
            "date": self.date,
            "year": self.year,
            "month": self.month,
            "company": self.company,
            "buyer": self.buyer,
            "amount": self.amount,
            "invoice_no": self.invoice_no,
            "success": self.success,
        }
        if self.error:
            result["error"] = self.error
        return result


class InvoiceParser:
    """发票解析器"""

    OCR_ENGINE = None

    def __init__(self):
        pass

    def _get_ocr_engine(self):
        """获取OCR引擎（单例模式）"""
        if InvoiceParser.OCR_ENGINE is None:
            from rapidocr_onnxruntime import RapidOCR
            InvoiceParser.OCR_ENGINE = RapidOCR()
        return InvoiceParser.OCR_ENGINE

    def _normalize_unicode(self, text: str) -> str:
        """规范化Unicode字符 - Kangxi radicals转正常中文"""
        kangxi_map = {"⽂": "文", "⽉": "月", "⽇": "日", "⽕": "火", "⽕": "水"}
        for old, new in kangxi_map.items():
            text = text.replace(old, new)
        return text

    def _extract_date(self, text: str) -> Tuple[Optional[str], int, int]:
        """从文本中提取日期"""
        year = datetime.now().year
        month = datetime.now().month
        date_str = None
        
        date_match = re.search(r"(\d{4})年(\d{1,2})[⽉月](\d{1,2})[⽇日]", text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            date_str = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
        
        return date_str, year, month

    def _extract_company(self, text: str) -> str:
        """从文本中提取公司名称"""
        company = "未知"
        
        double_match = re.findall(r"名\s*称[：:]\s*([^\s\n]{2,50})", text)
        if len(double_match) >= 1:
            company = double_match[0].strip()
        else:
            lines = text.split("\n")
            for line in lines:
                parts = line.split()
                company_candidates = [p for p in parts if len(p) >= 4 and "公司" in p]
                if len(company_candidates) >= 1:
                    company = company_candidates[0]
                    break

        if company.startswith("名称：") or company.startswith("名称:"):
            company = company[3:]

        return self._normalize_unicode(company)

    def _extract_amount(self, text: str) -> float:
        """从文本中提取金额"""
        amount_match = re.search(r"[¥￥]([0-9,]+\.?\d*)", text)
        if amount_match:
            amount_str = amount_match.group(1).replace(",", "")
            return float(amount_str)
        return 0.0

    def _extract_invoice_no(self, text: str) -> str:
        """从文本中提取发票号码"""
        no_match = re.search(r"发票号码[：:]*\s*(\d+)", text)
        if no_match:
            return no_match.group(1)
        
        no20_match = re.search(r"\b(\d{20})\b", text)
        if no20_match:
            return no20_match.group(1)
        
        return ""

    def parse_image(self, file_path: str) -> InvoiceData:
        """使用OCR解析图片发票"""
        result = InvoiceData(file_name=os.path.basename(file_path))

        try:
            ocr = self._get_ocr_engine()
            img = Image.open(file_path)
            img_array = np.array(img)

            ocr_result, elapse = ocr(img_array)

            if not ocr_result:
                result.error = "未识别到文字"
                return result

            text_lines = [line[1] for line in ocr_result]
            text = "\n".join(text_lines)

            result.date, result.year, result.month = self._extract_date(text)
            result.buyer = self._extract_company(text)
            result.amount = self._extract_amount(text)
            result.invoice_no = self._extract_invoice_no(text)
            result.success = True

        except Exception as e:
            result.error = str(e)

        return result

    def parse_pdf(self, file_path: str) -> InvoiceData:
        """解析单个发票PDF"""
        result = InvoiceData(file_name=os.path.basename(file_path))

        try:
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            result.date, result.year, result.month = self._extract_date(text)
            result.buyer = self._extract_company(text)
            result.amount = self._extract_amount(text)
            result.invoice_no = self._extract_invoice_no(text)
            result.success = True

        except Exception as e:
            result.error = str(e)

        return result


class DuplicateDetector:
    """重复发票检测"""

    def __init__(self):
        self.processed_filenames: Set[str] = set()
        self.processed_hashes: Set[str] = set()
        self.duplicate_files: list = []

    def check_and_register(self, filename: str, file_hash: str) -> bool:
        """
        检查是否重复
        返回True表示重复（应该跳过），False表示正常
        """
        if filename in self.processed_filenames:
            self.duplicate_files.append(filename)
            return True

        if file_hash in self.processed_hashes:
            self.duplicate_files.append(filename)
            return True

        self.processed_filenames.add(filename)
        self.processed_hashes.add(file_hash)
        return False

    def reset(self):
        """重置检测器"""
        self.processed_filenames.clear()
        self.processed_hashes.clear()
        self.duplicate_files.clear()


def parse_invoice(file_path: str) -> InvoiceData:
    """解析发票文件（根据扩展名自动选择解析器）"""
    parser = InvoiceParser()
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return parser.parse_pdf(file_path)
    else:
        return parser.parse_image(file_path)
