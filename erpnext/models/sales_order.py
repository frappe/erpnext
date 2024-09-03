from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .doctype import Base

class SalesOrder(Base):
    __tablename__ = 'tabSales Order'

    name = Column(String(140), primary_key=True)
    customer = Column(String(140), ForeignKey('tabCustomer.name'))
    transaction_date = Column(DateTime)
    delivery_date = Column(DateTime)
    total = Column(Float(precision=2), default=0)
    status = Column(String(140), default="Draft")

    # Relationships
    items = relationship("SalesOrderItem", back_populates="sales_order")

class SalesOrderItem(Base):
    __tablename__ = 'tabSales Order Item'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabSales Order.name'))
    item_code = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    rate = Column(Float(precision=2))
    amount = Column(Float(precision=2))

    # Relationships
    sales_order = relationship("SalesOrder", back_populates="items")
    item = relationship("Item")