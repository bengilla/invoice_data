import base64
import pendulum
import pdfplumber
from fastapi import UploadFile
from models.mongodb import MongoDB
from pymongo.errors import DuplicateKeyError

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def pdf_file(self, file: UploadFile | None) -> dict:
        # calculate
        try:
            with pdfplumber.open(file) as pdf:
                content = []
                for i in range(len(pdf.pages)):
                    page = pdf.pages[i]
                    page_content = page.extract_text().split("\n")[:-1]
                    content.append(page_content)
                # print(content)

                code = []
                number = []
                date = []
                amount = []
                for i in content[0]:
                    if "发票代码" in i:
                        for x in i:
                            if x.isnumeric():
                                code.append(x)
                    if "发票号码" in i:
                        for x in i:
                            if x.isnumeric():
                                number.append(x)
                    if "开票日期" in i:
                        for x in i:
                            if x.isnumeric():
                                date.append(x)
                    if "¥" in i or "￥" in i:
                        amount.append(i)

                for x in amount[1]:
                    if x == "¥" or x == "￥":
                        num = amount[1].index(x)

                date_output = "".join(date)
                num_output = int("".join(number))
                code_output = int("".join(code))
                amount_output = float(amount[1][num + 1 :])

                dt = pendulum.from_format(date_output, "YYYYMMDD")
                self.year = dt.year
                self.month = dt.month

                with open(file, "rb") as f:
                    encoded = base64.b64encode(f.read())

                data = {
                    "_id": num_output,
                    "date": dt.to_date_string(),
                    "code": code_output,
                    "amount": "{:0.2f}".format(amount_output),
                    "pdf": encoded,
                }
                # print(data)

                _db.send_data(dt.month).insert_one(data)
        except DuplicateKeyError:
            return f"File duplicate, '_id' {num_output}".upper()
        except Exception as error:
            return f"Error: {error}"
