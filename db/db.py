from datetime import date
from sqlalchemy.orm import sessionmaker
from db.scheme import UserSchema, InvoiceSchema, engine


class Users:
    def __init__(self) -> None:
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def register(self, username: str, password: str):
        store_user = UserSchema(
            username=username,
            password=password,
        )

        self.session.add(store_user)
        self.session.commit()

    def user_info(self, username: str):
        """return id, username, password, register_date"""
        get_user = (
            self.session.query(UserSchema).filter(UserSchema.username == username).all()
        )
        get_password = [p.password for p in get_user]
        return get_password[0]


class Invoice:
    def __init__(self) -> None:
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def check_user_invoice(self, username: str):
        get_data = (
            self.session.query(UserSchema).filter(UserSchema.username == username).all()
        )
        return get_data[0]

    def create_db(
        self,
        id: int,
        date: date,
        company: str,
        amount: float,
        pdf: str,
        download: bool,
        user_id: int,
    ):
        data = InvoiceSchema(
            id=id,
            date=date,
            company=company,
            amount=amount,
            pdf=pdf,
            download=download,
            user_id=user_id,
        )
        self.session.add(data)
        self.session.commit()
