"""
Finance - Payment Matching Engine

Implements payment matching per Finance PDF spec:
- Match payments to invoices (AR)
- Match payments to bills (AP)
- Automatic matching by amount/reference
- Manual matching with partial payments
- Payment allocation across multiple invoices
- Unmatched payment handling
- Overpayment/underpayment detection

Payment Matching Process:
1. Receive payment transaction
2. Try automatic matching (by reference, amount, customer)
3. Allow manual matching if automatic fails
4. Support partial payments
5. Support payment allocation to multiple invoices
6. Track unmatched/unapplied payments
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


class PaymentMatchingEngine:
    """
    Payment Matching Engine
    Handles automatic and manual matching of payments to invoices/bills
    """
    
    # Match confidence levels
    MATCH_EXACT = "exact"       # 100% confidence (reference + amount match)
    MATCH_HIGH = "high"         # 90%+ confidence (reference OR amount + customer)
    MATCH_MEDIUM = "medium"     # 60%+ confidence (amount + date proximity)
    MATCH_LOW = "low"           # <60% confidence (customer only)
    
    # Payment statuses
    STATUS_UNMATCHED = "unmatched"
    STATUS_PARTIALLY_MATCHED = "partially_matched"
    STATUS_FULLY_MATCHED = "fully_matched"
    STATUS_OVERPAID = "overpaid"
    
    def __init__(self, db: Session, company_id: str, user_id: str):
        self.db = db
        self.company_id = company_id
        self.user_id = user_id
    
    def match_payment_auto(
        self,
        payment_id: str,
        payment_type: str = "customer"  # "customer" or "supplier"
    ) -> Dict[str, Any]:
        """
        Automatically match a payment to invoices/bills
        
        Matching logic:
        1. Exact match by reference number
        2. Match by amount + customer/supplier
        3. Match by amount + date proximity
        4. Return suggestions if no exact match
        
        Args:
            payment_id: ID of payment to match
            payment_type: "customer" (AR) or "supplier" (AP)
        
        Returns:
            Match results with confidence levels
        """
        # Get payment record
        # For now, we'll use journal entries with source_type = "payment"
        payment = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.id == payment_id,
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.source_type == "payment"
        ).first()
        
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")
        
        # Extract payment details from journal entry
        payment_amount = abs(Decimal(str(payment.total_amount)))
        payment_date = payment.date
        payment_reference = payment.reference
        
        # Get customer/supplier from journal lines (if available)
        party_id = None
        for line in payment.lines:
            if hasattr(line, "customer_id") and line.customer_id:
                party_id = line.customer_id
                break
            elif hasattr(line, "supplier_id") and line.supplier_id:
                party_id = line.supplier_id
                break
        
        # Find potential matches
        if payment_type == "customer":
            matches = self._find_invoice_matches(
                payment_amount, payment_date, payment_reference, party_id
            )
        else:
            matches = self._find_bill_matches(
                payment_amount, payment_date, payment_reference, party_id
            )
        
        if not matches:
            logger.info(f"No automatic matches found for payment {payment.journal_number}")
            return {
                "success": False,
                "matched": False,
                "payment_id": payment_id,
                "payment_amount": float(payment_amount),
                "suggestions": [],
                "message": "No matches found - requires manual matching"
            }
        
        # Apply best match automatically if exact/high confidence
        best_match = matches[0]
        
        if best_match["confidence"] in [self.MATCH_EXACT, self.MATCH_HIGH]:
            # Apply payment automatically
            result = self.apply_payment_to_invoice(
                payment_id=payment_id,
                invoice_id=best_match["invoice_id"],
                amount=min(payment_amount, Decimal(str(best_match["amount_due"])))
            )
            
            logger.info(
                f"Auto-matched payment {payment.journal_number} to invoice "
                f"{best_match['invoice_number']} (confidence: {best_match['confidence']})"
            )
            
            return {
                "success": True,
                "matched": True,
                "payment_id": payment_id,
                "match_type": "automatic",
                "confidence": best_match["confidence"],
                "applied_to": [result],
                "suggestions": matches[1:] if len(matches) > 1 else []
            }
        else:
            # Return suggestions for manual matching
            logger.info(
                f"Found {len(matches)} potential matches for payment {payment.journal_number} "
                f"- requires manual confirmation"
            )
            
            return {
                "success": True,
                "matched": False,
                "payment_id": payment_id,
                "payment_amount": float(payment_amount),
                "suggestions": matches,
                "message": "Found potential matches - manual confirmation required"
            }
    
    def _find_invoice_matches(
        self,
        amount: Decimal,
        payment_date: date,
        reference: Optional[str],
        customer_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find matching invoices for a customer payment"""
        matches = []
        
        # Query unpaid/partially paid invoices
        query = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.company_id == self.company_id,
            models.SalesOrder.payment_status.in_(["unpaid", "partially_paid"])
        )
        
        if customer_id:
            query = query.filter(models.SalesOrder.customer_id == customer_id)
        
        invoices = query.all()
        
        for invoice in invoices:
            confidence = None
            score = 0
            
            # Calculate amount due (total - paid)
            total = Decimal(str(invoice.total_amount or 0))
            paid = Decimal(str(invoice.amount_paid or 0))
            amount_due = total - paid
            
            if amount_due <= 0:
                continue  # Skip fully paid invoices
            
            # Exact match: reference + amount
            if reference and reference == invoice.order_number:
                if abs(amount - amount_due) < Decimal("0.01"):
                    confidence = self.MATCH_EXACT
                    score = 100
                else:
                    confidence = self.MATCH_HIGH
                    score = 90
            
            # High match: reference OR (amount + customer)
            elif reference and reference == invoice.order_number:
                confidence = self.MATCH_HIGH
                score = 85
            elif customer_id and abs(amount - amount_due) < Decimal("0.01"):
                confidence = self.MATCH_HIGH
                score = 80
            
            # Medium match: amount + date proximity
            elif abs(amount - amount_due) < Decimal("0.01"):
                days_diff = abs((payment_date - invoice.order_date).days)
                if days_diff <= 30:
                    confidence = self.MATCH_MEDIUM
                    score = 70 - (days_diff * 0.3)
            
            # Low match: customer only
            elif customer_id:
                confidence = self.MATCH_LOW
                score = 50
            
            if confidence:
                matches.append({
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.order_number,
                    "invoice_date": invoice.order_date,
                    "customer_id": invoice.customer_id,
                    "total_amount": float(total),
                    "amount_due": float(amount_due),
                    "confidence": confidence,
                    "score": score
                })
        
        # Sort by score (descending)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return matches
    
    def _find_bill_matches(
        self,
        amount: Decimal,
        payment_date: date,
        reference: Optional[str],
        supplier_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Find matching bills for a supplier payment"""
        matches = []
        
        # Query unpaid/partially paid bills
        query = self.db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.company_id == self.company_id,
            models.PurchaseOrder.payment_status.in_(["unpaid", "partially_paid"])
        )
        
        if supplier_id:
            query = query.filter(models.PurchaseOrder.supplier_id == supplier_id)
        
        bills = query.all()
        
        for bill in bills:
            confidence = None
            score = 0
            
            # Calculate amount due
            total = Decimal(str(bill.total_amount or 0))
            paid = Decimal(str(bill.amount_paid or 0))
            amount_due = total - paid
            
            if amount_due <= 0:
                continue
            
            # Similar matching logic as invoices
            if reference and reference == bill.order_number:
                if abs(amount - amount_due) < Decimal("0.01"):
                    confidence = self.MATCH_EXACT
                    score = 100
                else:
                    confidence = self.MATCH_HIGH
                    score = 90
            elif reference and reference == bill.order_number:
                confidence = self.MATCH_HIGH
                score = 85
            elif supplier_id and abs(amount - amount_due) < Decimal("0.01"):
                confidence = self.MATCH_HIGH
                score = 80
            elif abs(amount - amount_due) < Decimal("0.01"):
                days_diff = abs((payment_date - bill.order_date).days)
                if days_diff <= 30:
                    confidence = self.MATCH_MEDIUM
                    score = 70 - (days_diff * 0.3)
            elif supplier_id:
                confidence = self.MATCH_LOW
                score = 50
            
            if confidence:
                matches.append({
                    "bill_id": bill.id,
                    "bill_number": bill.order_number,
                    "bill_date": bill.order_date,
                    "supplier_id": bill.supplier_id,
                    "total_amount": float(total),
                    "amount_due": float(amount_due),
                    "confidence": confidence,
                    "score": score
                })
        
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        return matches
    
    def apply_payment_to_invoice(
        self,
        payment_id: str,
        invoice_id: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Apply payment to a specific invoice
        
        Args:
            payment_id: ID of payment
            invoice_id: ID of invoice
            amount: Amount to apply
        
        Returns:
            Application result
        """
        # Get invoice
        invoice = self.db.query(models.SalesOrder).filter(
            models.SalesOrder.id == invoice_id,
            models.SalesOrder.company_id == self.company_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        # Calculate amount due
        total = Decimal(str(invoice.total_amount or 0))
        paid = Decimal(str(invoice.amount_paid or 0))
        amount_due = total - paid
        
        if amount > amount_due:
            logger.warning(
                f"Payment amount {amount} exceeds amount due {amount_due} "
                f"for invoice {invoice.order_number}"
            )
        
        # Apply payment amount
        applied_amount = min(amount, amount_due)
        invoice.amount_paid = (paid + applied_amount)
        
        # Update payment status
        if invoice.amount_paid >= total:
            invoice.payment_status = "paid"
        elif invoice.amount_paid > 0:
            invoice.payment_status = "partially_paid"
        
        invoice.payment_date = datetime.now()
        
        self.db.commit()
        self.db.refresh(invoice)
        
        logger.info(
            f"Applied payment {payment_id} to invoice {invoice.order_number}: "
            f"{applied_amount} applied, {total - invoice.amount_paid} remaining"
        )
        
        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice.order_number,
            "amount_applied": float(applied_amount),
            "amount_remaining": float(total - invoice.amount_paid),
            "payment_status": invoice.payment_status
        }
    
    def apply_payment_to_bill(
        self,
        payment_id: str,
        bill_id: str,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Apply payment to a specific bill"""
        bill = self.db.query(models.PurchaseOrder).filter(
            models.PurchaseOrder.id == bill_id,
            models.PurchaseOrder.company_id == self.company_id
        ).first()
        
        if not bill:
            raise ValueError(f"Bill {bill_id} not found")
        
        total = Decimal(str(bill.total_amount or 0))
        paid = Decimal(str(bill.amount_paid or 0))
        amount_due = total - paid
        
        applied_amount = min(amount, amount_due)
        bill.amount_paid = (paid + applied_amount)
        
        if bill.amount_paid >= total:
            bill.payment_status = "paid"
        elif bill.amount_paid > 0:
            bill.payment_status = "partially_paid"
        
        bill.payment_date = datetime.now()
        
        self.db.commit()
        self.db.refresh(bill)
        
        logger.info(
            f"Applied payment {payment_id} to bill {bill.order_number}: "
            f"{applied_amount} applied, {total - bill.amount_paid} remaining"
        )
        
        return {
            "bill_id": bill_id,
            "bill_number": bill.order_number,
            "amount_applied": float(applied_amount),
            "amount_remaining": float(total - bill.amount_paid),
            "payment_status": bill.payment_status
        }
    
    def apply_payment_split(
        self,
        payment_id: str,
        allocations: List[Dict[str, Any]],
        payment_type: str = "customer"
    ) -> Dict[str, Any]:
        """
        Apply a single payment to multiple invoices/bills
        
        Args:
            payment_id: ID of payment
            allocations: List of {invoice_id/bill_id, amount}
            payment_type: "customer" or "supplier"
        
        Returns:
            Split application results
        """
        results = []
        total_applied = Decimal("0.00")
        
        for allocation in allocations:
            amount = Decimal(str(allocation["amount"]))
            
            if payment_type == "customer":
                result = self.apply_payment_to_invoice(
                    payment_id=payment_id,
                    invoice_id=allocation["invoice_id"],
                    amount=amount
                )
            else:
                result = self.apply_payment_to_bill(
                    payment_id=payment_id,
                    bill_id=allocation["bill_id"],
                    amount=amount
                )
            
            results.append(result)
            total_applied += Decimal(str(result["amount_applied"]))
        
        logger.info(
            f"Split payment {payment_id} across {len(allocations)} "
            f"{payment_type} documents: total {total_applied} applied"
        )
        
        return {
            "success": True,
            "payment_id": payment_id,
            "total_applied": float(total_applied),
            "allocations": results
        }
    
    def get_unmatched_payments(
        self,
        payment_type: str = "customer"
    ) -> List[Dict[str, Any]]:
        """
        Get list of unmatched payments requiring manual attention
        
        Args:
            payment_type: "customer" or "supplier"
        
        Returns:
            List of unmatched payment records
        """
        # Query journal entries with source_type = "payment"
        # that haven't been matched yet
        # For this implementation, we'll return payments without allocations
        
        payments = self.db.query(models.JournalEntry).filter(
            models.JournalEntry.company_id == self.company_id,
            models.JournalEntry.source_type == "payment"
        ).all()
        
        unmatched = []
        
        for payment in payments:
            # Check if payment has been applied
            # (This would require a payment_allocations table in production)
            # For now, we'll return all payments as potential unmatched
            
            unmatched.append({
                "payment_id": payment.id,
                "payment_number": payment.journal_number,
                "payment_date": payment.date,
                "amount": float(payment.total_amount),
                "reference": payment.reference,
                "status": self.STATUS_UNMATCHED
            })
        
        return unmatched
