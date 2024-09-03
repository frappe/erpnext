from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .doctype import Base

class StockEntry(Base):
    __tablename__ = 'tabStock Entry'

    name = Column(String(140), primary_key=True)
    posting_date = Column(DateTime)
    company = Column(String(140), ForeignKey('tabCompany.name'))
    purpose = Column(String(140))
    
    # Relationships
    items = relationship("StockEntryDetail", back_populates="stock_entry")

class StockEntryDetail(Base):
    __tablename__ = 'tabStock Entry Detail'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabStock Entry.name'))
    item_code = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    basic_rate = Column(Float(precision=2))
    
    # Relationships
    stock_entry = relationship("StockEntry", back_populates="items")
    item = relationship("Item")

class PurchaseReceipt(Base):
    __tablename__ = 'tabPurchase Receipt'

    name = Column(String(140), primary_key=True)
    supplier = Column(String(140), ForeignKey('tabSupplier.name'))
    posting_date = Column(DateTime)
    company = Column(String(140), ForeignKey('tabCompany.name'))
    
    # Relationships
    items = relationship("PurchaseReceiptItem", back_populates="purchase_receipt")

class PurchaseReceiptItem(Base):
    __tablename__ = 'tabPurchase Receipt Item'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabPurchase Receipt.name'))
    item_code = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    rate = Column(Float(precision=2))
    
    # Relationships
    purchase_receipt = relationship("PurchaseReceipt", back_populates="items")
    item = relationship("Item")