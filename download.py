import codecs
from models.mongodb import MongoDB


_db = MongoDB()
file = _db.send_data("2").find({})
for i in file:
    date = i["date"]
    amount = i["amount"]
    code = i["pdf"]

    name = f"{date}[¥{amount}].pdf"

    with open(name, "wb") as f:
        f.write(codecs.decode(code, "base64"))
