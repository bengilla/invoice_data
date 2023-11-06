import uuid
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Uuid,
    Float,
    Boolean,
    BINARY,
)
from sqlalchemy.ext.declarative import declarative_base

from config.settings import Settings

_settings = Settings()

Base = declarative_base()
engine = create_engine(_settings.DB_URL)


class User(Base):
    __tablename__ = "users"
    id = Column(Uuid, primary_key=True, default=uuid.uuid1())
    username = Column(String(25), nullable=False, unique=True)
    password = Column(String(25), nullable=False)
    register_date = Column(DateTime, default=datetime.now())

    def __repr__(self):
        return f"{self.id}, {self.username}, {self.password}, {self.register_date}"


# class Invoice(Base):
#     __tablename__ = "invoice"
#     id = Column("id", primary_key=True)
#     date = Column("date", DateTime)
#     company = Column("company", String)
#     amount = Column("amount", Float)
#     pdf = Column("pdf", BINARY)
#     download = Column("download", Boolean)

#     def __repr__(self):
#         return f"{self.id}, {self.date}, {self.company}, {self.amount}, {self.pdf}, {self.download}"


# Base.metadata.create_all(bind=engine)
