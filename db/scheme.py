from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Integer,
    Float,
    Boolean,
    ForeignKey,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from config.settings import Settings

_settings = Settings()

Base = declarative_base()
engine = create_engine(_settings.MySQL, echo=True)


class UserScheme(Base):
    __tablename__ = "users"
    id = Column("id", Integer, primary_key=True)
    username = Column("username", String(255), nullable=False, unique=True)
    password = Column("password", String(255), nullable=False)
    register_date = Column("register_date", DateTime, default=datetime.now())
    invoice = relationship("InvoiceSchema", backref="user")


class InvoiceScheme(Base):
    __tablename__ = "invoices"
    id = Column("id", Integer(), primary_key=True, unique=True)
    date = Column("date", DateTime())
    company = Column("company", String(255))
    amount = Column("amount", Float())
    pdf = Column("pdf", LONGTEXT)
    download = Column("download", Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"))


Base.metadata.create_all(bind=engine)
