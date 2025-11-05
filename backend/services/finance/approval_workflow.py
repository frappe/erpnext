"""
Finance - Approval Workflow Engine

Implements the document approval workflow per Finance PDF spec:
Draft → Pending Approval → Approved → Posted → Locked

Workflow States:
- draft: Document created, can be edited
- pending_approval: Submitted for approval, no edits allowed
- approved: Approved by authorized user, ready to post
- rejected: Rejected, back to draft
- posted: Posted to ledger, affects accounts
- locked: Period closed, immutable

Approval Levels:
- Basic: Any manager can approve (< 10,000 ZMW)
- Medium: Department manager approval (10,000 - 100,000 ZMW)
- High: Finance director approval (> 100,000 ZMW)
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, date
from decimal import Decimal
import models
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class ApprovalWorkflowEngine:
    """
    Manages document approval workflows for Finance module
    Applicable to: Journal Entries, Invoices, Bills, Payments
    """
    
    # Approval thresholds (in ZMW)
    BASIC_THRESHOLD = Decimal("10000.00")
    MEDIUM_THRESHOLD = Decimal("100000.00")
    
    # Valid state transitions
    STATE_TRANSITIONS = {
        "draft": ["pending_approval", "cancelled"],
        "pending_approval": ["approved", "rejected", "cancelled"],
        "approved": ["posted", "cancelled"],
        "rejected": ["draft", "cancelled"],
        "posted": ["locked", "reversed"],  # Posted can be locked or reversed
        "locked": [],  # Locked is final, cannot transition
        "reversed": ["locked"],  # Reversed entries can be locked
        "cancelled": []  # Cancelled is final
    }
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
        self.user = self._get_user()
    
    def _get_user(self) -> models.User:
        """Get current user"""
        user = self.db.query(models.User).filter(
            models.User.id == self.user_id
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    
    def _get_approval_level(self, amount: Decimal) -> str:
        """Determine approval level based on amount"""
        if amount < self.BASIC_THRESHOLD:
            return "basic"
        elif amount < self.MEDIUM_THRESHOLD:
            return "medium"
        else:
            return "high"
    
    def _can_approve(self, approval_level: str) -> bool:
        """Check if current user can approve based on their role"""
        user_role = self.user.role.lower()
        
        if user_role == "super_admin":
            return True
        
        if approval_level == "basic":
            # Any manager or above can approve basic
            return user_role in ["manager", "finance_manager", "admin"]
        
        elif approval_level == "medium":
            # Department manager or above
            return user_role in ["finance_manager", "admin"]
        
        elif approval_level == "high":
            # Finance director or admin only
            return user_role in ["admin"]
        
        return False
    
    def _validate_state_transition(self, current_state: str, new_state: str):
        """Validate if state transition is allowed"""
        if current_state not in self.STATE_TRANSITIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid current state: {current_state}"
            )
        
        allowed_transitions = self.STATE_TRANSITIONS[current_state]
        
        if new_state not in allowed_transitions:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from '{current_state}' to '{new_state}'. Allowed transitions: {allowed_transitions}"
            )
    
    def submit_for_approval(
        self,
        document_type: str,  # "journal_entry", "invoice", "bill", "payment"
        document_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit document for approval (draft → pending_approval)
        
        Args:
            document_type: Type of document (journal_entry, invoice, bill, payment)
            document_id: Document ID
            notes: Optional submission notes
        
        Returns:
            Updated document with approval request details
        """
        # Get document
        document = self._get_document(document_type, document_id)
        
        # Validate current state
        self._validate_state_transition(document.status, "pending_approval")
        
        # Determine approval level
        approval_level = self._get_approval_level(Decimal(str(document.total_amount)))
        
        # Create approval request
        approval_request = models.ApprovalRequest(
            company_id=self.company_id,
            document_type=document_type,
            document_id=document_id,
            requested_by=self.user_id,
            approval_level=approval_level,
            status="pending",
            notes=notes,
            requested_at=datetime.now()
        )
        
        self.db.add(approval_request)
        
        # Update document status
        document.status = "pending_approval"
        
        self.db.commit()
        self.db.refresh(approval_request)
        
        logger.info(
            f"Submitted {document_type} {document_id} for {approval_level} approval"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "document_type": document_type,
            "status": "pending_approval",
            "approval_level": approval_level,
            "approval_request_id": approval_request.id
        }
    
    def approve_document(
        self,
        document_type: str,
        document_id: str,
        approval_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a document (pending_approval → approved)
        
        Args:
            document_type: Type of document
            document_id: Document ID
            approval_notes: Optional approval notes
        
        Returns:
            Updated document with approval details
        """
        # Get document
        document = self._get_document(document_type, document_id)
        
        # Validate current state
        self._validate_state_transition(document.status, "approved")
        
        # Get approval request
        approval_request = self.db.query(models.ApprovalRequest).filter(
            models.ApprovalRequest.document_type == document_type,
            models.ApprovalRequest.document_id == document_id,
            models.ApprovalRequest.status == "pending"
        ).first()
        
        if not approval_request:
            raise HTTPException(
                status_code=404,
                detail="Approval request not found"
            )
        
        # Check if user can approve
        if not self._can_approve(approval_request.approval_level):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have permission to approve {approval_request.approval_level} level documents. User role: {self.user.role}"
            )
        
        # Prevent self-approval
        if approval_request.requested_by == self.user_id:
            raise HTTPException(
                status_code=403,
                detail="You cannot approve your own submission"
            )
        
        # Update approval request
        approval_request.status = "approved"
        approval_request.approved_by = self.user_id
        approval_request.approved_at = datetime.now()
        approval_request.approval_notes = approval_notes
        
        # Update document status
        document.status = "approved"
        
        self.db.commit()
        
        logger.info(
            f"Approved {document_type} {document_id} by user {self.user_id}"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "document_type": document_type,
            "status": "approved",
            "approved_by": self.user_id,
            "approved_at": approval_request.approved_at
        }
    
    def reject_document(
        self,
        document_type: str,
        document_id: str,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """
        Reject a document (pending_approval → rejected)
        
        Args:
            document_type: Type of document
            document_id: Document ID
            rejection_reason: Reason for rejection
        
        Returns:
            Updated document with rejection details
        """
        # Get document
        document = self._get_document(document_type, document_id)
        
        # Validate current state
        self._validate_state_transition(document.status, "rejected")
        
        # Get approval request
        approval_request = self.db.query(models.ApprovalRequest).filter(
            models.ApprovalRequest.document_type == document_type,
            models.ApprovalRequest.document_id == document_id,
            models.ApprovalRequest.status == "pending"
        ).first()
        
        if not approval_request:
            raise HTTPException(
                status_code=404,
                detail="Approval request not found"
            )
        
        # Check if user can approve (can also reject)
        if not self._can_approve(approval_request.approval_level):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have permission to reject {approval_request.approval_level} level documents"
            )
        
        # Update approval request
        approval_request.status = "rejected"
        approval_request.approved_by = self.user_id
        approval_request.approved_at = datetime.now()
        approval_request.approval_notes = rejection_reason
        
        # Update document status
        document.status = "rejected"
        
        self.db.commit()
        
        logger.info(
            f"Rejected {document_type} {document_id} by user {self.user_id}: {rejection_reason}"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "document_type": document_type,
            "status": "rejected",
            "rejected_by": self.user_id,
            "rejection_reason": rejection_reason
        }
    
    def post_document(
        self,
        document_type: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Post a document to the ledger (approved → posted)
        
        For journal entries, this means the entry affects account balances.
        Posted documents cannot be edited, only reversed.
        
        Args:
            document_type: Type of document
            document_id: Document ID
        
        Returns:
            Updated document with posted status
        """
        # Get document
        document = self._get_document(document_type, document_id)
        
        # Validate current state
        # Can post from 'draft' (direct posting) or 'approved' (after approval)
        if document.status not in ["draft", "approved"]:
            raise HTTPException(
                status_code=400,
                detail=f"Can only post documents in 'draft' or 'approved' status. Current status: {document.status}"
            )
        
        # If amount requires approval and not approved, reject
        approval_level = self._get_approval_level(Decimal(str(document.total_amount)))
        
        if approval_level != "basic" and document.status != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Document requires {approval_level} approval before posting. Please submit for approval first."
            )
        
        # Update document status
        document.status = "posted"
        
        # For journal entries, mark the date it was posted
        if document_type == "journal_entry" and hasattr(document, 'posted_at'):
            document.posted_at = datetime.now()
            document.posted_by = self.user_id
        
        self.db.commit()
        
        logger.info(
            f"Posted {document_type} {document_id} by user {self.user_id}"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "document_type": document_type,
            "status": "posted"
        }
    
    def lock_document(
        self,
        document_type: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Lock a document (posted → locked)
        
        Locked documents are in a closed accounting period and are immutable.
        This happens during period close.
        
        Args:
            document_type: Type of document
            document_id: Document ID
        
        Returns:
            Updated document with locked status
        """
        # Get document
        document = self._get_document(document_type, document_id)
        
        # Validate current state
        self._validate_state_transition(document.status, "locked")
        
        # Update document status
        document.status = "locked"
        
        self.db.commit()
        
        logger.info(
            f"Locked {document_type} {document_id}"
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "document_type": document_type,
            "status": "locked"
        }
    
    def get_pending_approvals(self, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests for current user
        
        Returns documents that current user has permission to approve.
        """
        # Build query for pending approvals
        query = self.db.query(models.ApprovalRequest).filter(
            models.ApprovalRequest.company_id == self.company_id,
            models.ApprovalRequest.status == "pending"
        )
        
        if document_type:
            query = query.filter(models.ApprovalRequest.document_type == document_type)
        
        approval_requests = query.all()
        
        # Filter by user permission level
        user_can_approve = []
        
        for req in approval_requests:
            # Skip self-submitted requests
            if req.requested_by == self.user_id:
                continue
            
            # Check if user can approve this level
            if self._can_approve(req.approval_level):
                user_can_approve.append({
                    "id": req.id,
                    "document_type": req.document_type,
                    "document_id": req.document_id,
                    "approval_level": req.approval_level,
                    "requested_by": req.requested_by,
                    "requested_at": req.requested_at,
                    "notes": req.notes
                })
        
        return user_can_approve
    
    def _get_document(self, document_type: str, document_id: str):
        """Get document by type and ID"""
        if document_type == "journal_entry":
            model = models.JournalEntry
        elif document_type == "invoice":
            model = models.Invoice
        elif document_type == "bill":
            model = models.Bill
        elif document_type == "payment":
            model = models.Payment
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid document type: {document_type}"
            )
        
        document = self.db.query(model).filter(
            model.id == document_id,
            model.company_id == self.company_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"{document_type} not found"
            )
        
        return document
