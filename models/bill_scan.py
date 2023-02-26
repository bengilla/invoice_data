import cv2
import pendulum
from models.mongodb import MongoDB

_db = MongoDB()


class Invoice:
    def qrcode(self, image, pdf):
        qrcode = cv2.imread(image)
        detector = cv2.QRCodeDetector()
        data = detector.detectAndDecode(qrcode)

        list_data = data[0].split(",")

        code = list_data[2]
        date = list_data[5]
        amount = list_data[4]

        dt = pendulum.from_format(date, "YYYYMMDD")
        self.month = dt.month

        data = {
            "_id": code,
            "date": dt.to_date_string(),
            "amount": float(amount),
            "pdf": pdf,
        }

        _db.send_data(dt.month).insert_one(data)
