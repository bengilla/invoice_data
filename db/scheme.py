import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Uuid,
    Integer,
    Float,
    Boolean,
    BINARY,
)
from sqlalchemy.ext.declarative import declarative_base

from config.settings import Settings

_settings = Settings()

Base = declarative_base()
engine = create_engine(_settings.MySQL, echo=True)


class UserScheme(Base):
    __tablename__ = "users"
    id = Column("id", Uuid, primary_key=True, default=uuid.uuid1())
    username = Column("username", String(255), nullable=False, unique=True)
    password = Column("password", String(255), nullable=False)
    register_date = Column("register_date", DateTime, default=datetime.now())

    def __repr__(self):
        return f"{self.id}, {self.username}, {self.password}, {self.register_date}"


# def invoice_models(tablename):
#     class InvoiceScheme(Base):
#         __tablename__ = tablename
#         id = Column(Integer, primary_key=True, unique=True)
#         date = Column(DateTime())
#         company = Column(String())
#         amount = Column(Float())
#         pdf = Column(BINARY())
#         download = Column(Boolean, default=False)

#         def __repr__(self):
#             return f"{self.id}, {self.date}, {self.company}, {self.amount}, {self.pdf}, {self.download}"

#     return InvoiceScheme()


Base.metadata.create_all(bind=engine)
