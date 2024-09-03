from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from Goldfish.models.doctype import Base

class Workflow(Base):
    __tablename__ = 'tabWorkflow'

    name = Column(String(140), primary_key=True)
    document_type = Column(String(140))
    is_active = Column(Boolean, default=True)

    states = relationship("WorkflowState", back_populates="workflow")
    transitions = relationship("WorkflowTransition", back_populates="workflow")

class WorkflowState(Base):
    __tablename__ = 'tabWorkflow State'

    name = Column(String(140), primary_key=True)
    workflow = Column(String(140), ForeignKey('tabWorkflow.name'))
    state = Column(String(140))
    allow_edit = Column(String(140))

    workflow_rel = relationship("Workflow", back_populates="states")

class WorkflowTransition(Base):
    __tablename__ = 'tabWorkflow Transition'

    name = Column(String(140), primary_key=True)
    workflow = Column(String(140), ForeignKey('tabWorkflow.name'))
    state = Column(String(140))
    action = Column(String(140))
    next_state = Column(String(140))
    allowed = Column(String(140))

    workflow_rel = relationship("Workflow", back_populates="transitions")

def apply_workflow(document, action):
    # Implement workflow logic here
    pass