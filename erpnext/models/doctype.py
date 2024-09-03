from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DocType(Base):
    __tablename__ = 'tabDocType'

    name = Column(String(140), primary_key=True)
    module = Column(String(140))
    is_submittable = Column(Boolean, default=False)
    is_tree = Column(Boolean, default=False)
    is_single = Column(Boolean, default=False)
    custom = Column(Boolean, default=False)
    modified = Column(DateTime)
    modified_by = Column(String(140))
    owner = Column(String(140))
    docstatus = Column(Integer, default=0)

    # Relationships
    fields = relationship("DocField", back_populates="doctype")

class DocField(Base):
    __tablename__ = 'tabDocField'

    name = Column(String(140), primary_key=True)
    fieldname = Column(String(140))
    label = Column(String(140))
    fieldtype = Column(String(140))
    options = Column(String(255))
    reqd = Column(Boolean, default=False)
    parent = Column(String(140), ForeignKey('tabDocType.name'))

    # Relationship
    doctype = relationship("DocType", back_populates="fields")

# Add more models for other core DocTypes...