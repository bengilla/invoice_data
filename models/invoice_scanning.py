"""invoice work section"""
import base64
import pendulum
import pdfplumber
from pymongo.errors import DuplicateKeyError

from models.mongodb import MongoDB

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def __init__(self) -> None:
        self.year = None
        self.month = None

    def pdf_file(self, file):
        """Calculate invoice data"""
        try:
            with pdfplumber.open(file) as pdf:
                content = []
                for i, _ in enumerate(pdf.pages):
                    page = pdf.pages[i]
                    page_content = page.extract_text().split("\n")[:-1]
                    content.append(page_content)
                # print(content)

                date = []
                code = []
                number = []
                amount = []

                for i in content[0]:
                    if "发票代码" in i:
                        for codes in i:
                            if codes.isdigit():
                                code.append(codes)
                    if "发票号码" in i:
                        for numbers in i:
                            if numbers.isdigit():
                                number.append(numbers)
                    if "开票日期" in i:
                        for dates in i:
                            if dates.isdigit():
                                date.append(dates)
                    if "¥" in i or "￥" in i:
                        amount.append(i)

                # get currency symbol index position
                currency_symbol = ("¥", "￥")
                for i in amount[1]:
                    if i in currency_symbol:
                        num = amount[1].index(i)

                date_output = "".join(date)
                code_output = int("".join(code))
                num_output = int("".join(number))
                amount_output = float(amount[1][num + 1 :])

                # date section, year and month are from invoice data
                get_date = pendulum.from_format(date_output, "YYYYMMDD")
                self.year = get_date.year
                self.month = get_date.month

                # encode pdf file and store to db
                with open(file, "rb") as pdf:
                    encoded = base64.b64encode(pdf.read())

                data = {
                    "_id": num_output,
                    "date": get_date.to_date_string(),
                    "code": code_output,
                    "amount": f"{amount_output:0.2f}",
                    "pdf": encoded,
                }
                # print(data)

                # store to db
                _db.send_data(str(get_date.month)).insert_one(data)
        except DuplicateKeyError:
            # when duplicate file
            return f"重复文件, 发票代码: {num_output}"
        except Exception:  # pylint: disable=W0718
            # other error
            return "文件异常, 请重新上传发票(PDF)"
