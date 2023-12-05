from datetime import date
from sqlalchemy.orm import sessionmaker
from db.scheme import UserSchema, InvoiceSchema, engine


class Users:
    def __init__(self) -> None:
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def register(self, username: str, password: str):
        """用户注册"""
        user = UserSchema(
            username=username,
            password=password,
        )

        self.session.add(user)
        self.session.commit()
        self.session.close_all()

    def user_info(self, username: str):
        """return 用户数据与用户关联发票数据"""
        user = (
            self.session.query(UserSchema)
            .filter(UserSchema.username == username)
            .first()
        )
        return user


class Invoices:
    """MySQL数据库"""

    def __init__(self) -> None:
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def store_invoice(
        self,
        id: int,
        date: date,
        company: str,
        amount: float,
        pdf: str,
        user_id: str,
    ):
        invoice_data = InvoiceSchema(
            id=id, date=date, company=company, amount=amount, pdf=pdf, user_id=user_id
        )
        self.session.add(invoice_data)
        self.session.commit()
        self.session.close_all()

    def each_invoice(self, invoice_id: int):
        invoice = (
            self.session.query(InvoiceSchema)
            .filter(InvoiceSchema.id == invoice_id)
            .first()
        )
        return invoice

    def year_invoice(self, username: str):
        year_list = []
        user = (
            self.session.query(UserSchema)
            .filter(UserSchema.username == username)
            .first()
        )
        user_invoice = user.invoice
        for i in user_invoice:
            year_list.append(i.date.year)
        return list(set(year_list))

    def modify(self, invoice_id: int, reason: str, note: str):
        data = (
            self.session.query(InvoiceSchema)
            .filter(InvoiceSchema.id == invoice_id)
            .first()
        )
        data.reason = reason
        data.note = note
        self.session.commit()
        # self.session.close_all()
        self.session.refresh(data)

    def download(self, invoice_id: int):
        downloaded = (
            self.session.query(InvoiceSchema)
            .filter(InvoiceSchema.id == invoice_id)
            .first()
        )
        if downloaded.download == False:
            downloaded.download = True
            self.session.commit()
            # self.session.close_all()
            self.session.refresh(downloaded)
