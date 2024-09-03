from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .doctype import Base

class WorkOrder(Base):
    __tablename__ = 'tabWork Order'

    name = Column(String(140), primary_key=True)
    production_item = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    planned_start_date = Column(DateTime)
    planned_end_date = Column(DateTime)
    status = Column(String(140))
    
    # Relationships
    operations = relationship("WorkOrderOperation", back_populates="work_order")

class WorkOrderOperation(Base):
    __tablename__ = 'tabWork Order Operation'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabWork Order.name'))
    operation = Column(String(140))
    workstation = Column(String(140), ForeignKey('tabWorkstation.name'))
    time_in_mins = Column(Float(precision=2))
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="operations")

class BOM(Base):
    __tablename__ = 'tabBOM'

    name = Column(String(140), primary_key=True)
    item = Column(String(140), ForeignKey('tabItem.name'))
    quantity = Column(Float(precision=2))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    items = relationship("BOMItem", back_populates="bom")

class BOMItem(Base):
    __tablename__ = 'tabBOM Item'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabBOM.name'))
    item_code = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    rate = Column(Float(precision=2))
    
    # Relationships
    bom = relationship("BOM", back_populates="items")
    item = relationship("Item")