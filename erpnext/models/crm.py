from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .doctype import Base
import enum

class LeadStatus(enum.Enum):
    OPEN = "Open"
    REPLIED = "Replied"
    OPPORTUNITY = "Opportunity"
    QUOTATION = "Quotation"
    LOST = "Lost"

class Lead(Base):
    __tablename__ = 'tabLead'

    name = Column(String(140), primary_key=True)
    lead_name = Column(String(140))
    company_name = Column(String(140))
    status = Column(Enum(LeadStatus), default=LeadStatus.OPEN)
    email = Column(String(140))
    phone = Column(String(140))

class Opportunity(Base):
    __tablename__ = 'tabOpportunity'

    name = Column(String(140), primary_key=True)
    opportunity_from = Column(String(140))
    party_name = Column(String(140))
    status = Column(String(140))
    expected_closing = Column(DateTime)
    
    # Relationships
    items = relationship("OpportunityItem", back_populates="opportunity")

class OpportunityItem(Base):
    __tablename__ = 'tabOpportunity Item'

    name = Column(String(140), primary_key=True)
    parent = Column(String(140), ForeignKey('tabOpportunity.name'))
    item_code = Column(String(140), ForeignKey('tabItem.name'))
    qty = Column(Float(precision=2))
    
    # Relationships
    opportunity = relationship("Opportunity", back_populates="items")
    item = relationship("Item")