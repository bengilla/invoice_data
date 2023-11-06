import uuid
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from db.scheme import User, engine


class Users:
    def __init__(self) -> None:
        Session = sessionmaker(bind=engine)
        self.session = Session()

    def register(self, username: str, password: str):
        store_user = User(
            username=username,
            password=password,
            # register_date=datetime.now(),
        )

        self.session.add(store_user)
        self.session.commit()

    def user_info(self, username: str):
        """return id, username, password, register_date"""
        get_user = self.session.query(User).filter(User.username == username).all()
        get_password = [p.password for p in get_user]
        return get_password[0]


# class Invoice:
#     def __init__(self) -> None:
#         Session = sessionmaker(bind=engine)
#         self.session = Session()

#     def invoice(
#         self,
#         id: int,
#         date: datetime,
#         company: str,
#         amount: float,
#         pdf: bytes,
#         download: bool,
#     ):
#         pass
