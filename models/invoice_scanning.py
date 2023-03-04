import base64
import pendulum
import pdfplumber
from pymongo.errors import DuplicateKeyError

from models.mongodb import MongoDB

_db = MongoDB()


class Invoice:
    """All function about invoice calculate"""

    def pdf_file(self, file) -> dict:
        """Calculate invoice data"""
        try:
            with pdfplumber.open(file) as pdf:
                content = []
                for i in range(len(pdf.pages)):
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
                code_output = int("".join(code))
                num_output = int("".join(number))
                amount_output = float(amount[1][num + 1 :])

                # date section, year and month are from invoice data
                dt = pendulum.from_format(date_output, "YYYYMMDD")
                self.year = dt.year
                self.month = dt.month

                # encode pdf file and store to db
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

                # store to db
                _db.send_data(str(dt.month)).insert_one(data)
        except DuplicateKeyError:
            # when duplicate file
            return f"File duplicate, '_id' {num_output}".upper()
        except Exception as error:
            # other error
            return f"Error: {error}"
