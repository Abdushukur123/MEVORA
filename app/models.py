from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .database import Base

class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), default="Quritilgan mevalar")
    description: Mapped[str] = mapped_column(Text, default="")
    unit: Mapped[str] = mapped_column(String(20), default="kg") # kg yoki dona
    retail_price: Mapped[float] = mapped_column(Float, default=0)
    wholesale_price: Mapped[float] = mapped_column(Float, default=0)
    image: Mapped[str] = mapped_column(String(300), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    stock: Mapped[float] = mapped_column(Float, default=100)

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40))
    address: Mapped[str] = mapped_column(String(300), default="")
    items_json: Mapped[str] = mapped_column(Text)
    total: Mapped[float] = mapped_column(Float)
    price_type: Mapped[str] = mapped_column(String(20), default="retail")
    status: Mapped[str] = mapped_column(String(30), default="Yangi")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
