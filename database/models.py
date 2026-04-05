from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from database.engine import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    CLIENT = "client"
    STAFF = "staff"
    ADMIN = "admin"


class OrderStatus(str, enum.Enum):
    AWAITING = "awaiting_assignment"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String(255))
    phone = Column(String(20))
    role = Column(Enum(UserRole, native_enum=False), default=UserRole.CLIENT)
    is_blocked = Column(Boolean, default=False)
    has_returned_equipment = Column(Boolean, default=True)
    last_equipment_return = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    orders = relationship("Order", foreign_keys="Order.client_id", back_populates="client")
    assigned_orders = relationship("Order", foreign_keys="Order.employee_id", back_populates="employee")
    work_slots = relationship("WorkSlot", back_populates="employee")


class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    base_price = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    category = Column(String(100))
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("users.id"))
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id"),
                        nullable=True)  # Может быть Null, если заказ сложный из калькулятора

    custom_details = Column(Text, nullable=True)  # Текст из калькулятора
    address = Column(String(500), nullable=False)
    order_date = Column(DateTime, nullable=False)
    payment_method = Column(String(100), default="Наличными")  # ТЗ 7.2: Оплата

    total_price = Column(Float, nullable=False)
    cost_price = Column(Float, default=0.0)
    status = Column(Enum(OrderStatus, native_enum=False), default=OrderStatus.AWAITING)
    cancel_reason = Column(String(255), nullable=True)
    review_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    complaint = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_utc_now)

    client = relationship("User", foreign_keys=[client_id], back_populates="orders")
    employee = relationship("User", foreign_keys=[employee_id], back_populates="assigned_orders")
    service = relationship("Service")
    work_slots = relationship("WorkSlot", back_populates="order")


class WorkSlot(Base):
    __tablename__ = "work_slots"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    order_id = Column(Integer, ForeignKey("orders.id"))
    slot_type = Column(String(50))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    employee = relationship("User", back_populates="work_slots")
    order = relationship("Order", back_populates="work_slots")


class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    item_type = Column(String(50))
    quantity = Column(Float, default=0)
    unit = Column(String(20))
    min_quantity = Column(Float, default=0)


class EquipmentIssue(Base):
    __tablename__ = "equipment_issues"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("users.id"))
    item_id = Column(Integer, ForeignKey("inventory.id"))
    issue_type = Column(String(50))
    description = Column(Text)
    date = Column(DateTime, default=get_utc_now)
    employee = relationship("User")
    item = relationship("InventoryItem")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)
    text = Column(Text)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)
    order = relationship("Order")
    user = relationship("User")