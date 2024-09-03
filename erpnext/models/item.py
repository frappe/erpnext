from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .doctype import Base

class Item(Base):
    __tablename__ = 'tabItem'

    name = Column(String(140), primary_key=True)
    item_code = Column(String(140), unique=True, index=True)
    item_name = Column(String(140))
    item_group = Column(String(140))
    stock_uom = Column(String(140))
    disabled = Column(Boolean, default=False)
    is_stock_item = Column(Boolean, default=True)
    has_variants = Column(Boolean, default=False)
    variant_of = Column(String(140), ForeignKey('tabItem.name'))
    valuation_rate = Column(Float(precision=2), default=0)
    description = Column(String(1000))
    
    # Relationships
    variants = relationship("Item", back_populates="parent_item")
    parent_item = relationship("Item", back_populates="variants", remote_side=[name])

# Add more Item-related models as needed