"""
Statutory Compliance Tracking Service

Features:
- Automatic generation of statutory obligations (PAYE, NAPSA, NHIMA, VAT, etc.)
- Due date management and confirmation
- Compliance percentage tracking
- Time-based alerts and notifications
- Checklist management for each obligation
"""

import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import models

logger = logging.getLogger(__name__)

# Zambian Statutory Obligations Configuration
STATUTORY_OBLIGATIONS_CONFIG = {
    "PAYE": {
        "name": "PAYE (Pay As You Earn Tax)",
        "frequency": "monthly",
        "due_day": 10,  # 10th of following month
        "authority": "ZRA (Zambia Revenue Authority)",
        "penalty_rate": 0.05,  # 5% per month late
        "checklist": [
            {"name": "Calculate monthly PAYE from payroll", "category": "calculation"},
            {"name": "Complete PAYE return form (P11)", "category": "preparation"},
            {"name": "Submit PAYE return to ZRA portal", "category": "filing"},
            {"name": "Make PAYE payment to ZRA", "category": "payment"},
            {"name": "Save payment confirmation", "category": "documentation"}
        ]
    },
    "NAPSA": {
        "name": "NAPSA Contributions",
        "frequency": "monthly",
        "due_day": 10,  # 10th of following month
        "authority": "NAPSA (National Pension Scheme Authority)",
        "penalty_rate": 0.10,  # 10% cumulative penalty
        "checklist": [
            {"name": "Calculate NAPSA contributions (employee + employer)", "category": "calculation"},
            {"name": "Complete NAPSA Schedule 1 return", "category": "preparation"},
            {"name": "Upload return to NAPSA iCARE portal", "category": "filing"},
            {"name": "Make NAPSA payment", "category": "payment"},
            {"name": "Save payment receipt", "category": "documentation"}
        ]
    },
    "NHIMA": {
        "name": "NHIMA Contributions",
        "frequency": "monthly",
        "due_day": 10,  # 10th of following month
        "authority": "NHIMA (National Health Insurance Management Authority)",
        "penalty_rate": 0.05,
        "checklist": [
            {"name": "Calculate NHIMA contributions", "category": "calculation"},
            {"name": "Upload employee data to NHIMA portal", "category": "filing"},
            {"name": "Make NHIMA payment", "category": "payment"},
            {"name": "Save payment confirmation", "category": "documentation"}
        ]
    },
    "VAT": {
        "name": "VAT (Value Added Tax)",
        "frequency": "monthly",
        "due_day": 18,  # 18th of following month
        "authority": "ZRA",
        "penalty_rate": 0.05,
        "checklist": [
            {"name": "Reconcile output VAT (sales)", "category": "calculation"},
            {"name": "Reconcile input VAT (purchases)", "category": "calculation"},
            {"name": "Calculate net VAT payable/refundable", "category": "calculation"},
            {"name": "Complete VAT return form", "category": "preparation"},
            {"name": "Submit VAT return to ZRA", "category": "filing"},
            {"name": "Make VAT payment", "category": "payment"},
            {"name": "Save submission confirmation", "category": "documentation"}
        ]
    },
    "WHT": {
        "name": "Withholding Tax",
        "frequency": "monthly",
        "due_day": 14,  # 14th of following month
        "authority": "ZRA",
        "penalty_rate": 0.05,
        "checklist": [
            {"name": "Identify all WHT transactions", "category": "calculation"},
            {"name": "Calculate WHT by category", "category": "calculation"},
            {"name": "Complete WHT return", "category": "preparation"},
            {"name": "Submit WHT return to ZRA", "category": "filing"},
            {"name": "Make WHT payment", "category": "payment"}
        ]
    },
    "TURNOVER_TAX": {
        "name": "Turnover Tax",
        "frequency": "monthly",
        "due_day": 14,  # 14th of following month
        "authority": "ZRA",
        "rate": 0.05,  # 5% on gross sales
        "applicable_if": "turnover_between_800k_and_5m",
        "checklist": [
            {"name": "Calculate gross monthly turnover", "category": "calculation"},
            {"name": "Calculate 5% turnover tax", "category": "calculation"},
            {"name": "Submit turnover tax return", "category": "filing"},
            {"name": "Make payment to ZRA", "category": "payment"}
        ]
    },
    "PROVISIONAL_TAX_Q1": {
        "name": "Provisional Income Tax Q1",
        "frequency": "quarterly",
        "due_day": 10,  # 10 April
        "due_month": 4,
        "authority": "ZRA",
        "checklist": [
            {"name": "Estimate Q1 taxable income", "category": "calculation"},
            {"name": "Calculate provisional tax", "category": "calculation"},
            {"name": "Submit provisional tax return", "category": "filing"},
            {"name": "Make payment", "category": "payment"}
        ]
    },
    "PROVISIONAL_TAX_Q2": {
        "name": "Provisional Income Tax Q2",
        "frequency": "quarterly",
        "due_day": 10,  # 10 July
        "due_month": 7,
        "authority": "ZRA"
    },
    "PROVISIONAL_TAX_Q3": {
        "name": "Provisional Income Tax Q3",
        "frequency": "quarterly",
        "due_day": 10,  # 10 October
        "due_month": 10,
        "authority": "ZRA"
    },
    "PROVISIONAL_TAX_Q4": {
        "name": "Provisional Income Tax Q4",
        "frequency": "quarterly",
        "due_day": 10,  # 10 January (following year)
        "due_month": 1,
        "authority": "ZRA"
    },
    "CORPORATE_TAX_RETURN": {
        "name": "Corporate Income Tax Return",
        "frequency": "annual",
        "due_day": 21,  # 21 June (electronic), 5 June (manual)
        "due_month": 6,
        "authority": "ZRA",
        "checklist": [
            {"name": "Finalize annual financial statements", "category": "preparation"},
            {"name": "Calculate taxable income", "category": "calculation"},
            {"name": "Complete tax computation", "category": "calculation"},
            {"name": "Prepare income tax return", "category": "preparation"},
            {"name": "Submit return electronically", "category": "filing"},
            {"name": "Pay balance due", "category": "payment"},
            {"name": "Obtain tax clearance certificate", "category": "documentation"}
        ]
    }
}


class StatutoryComplianceService:
    """Service for managing statutory compliance tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_monthly_obligations(
        self,
        company_id: str,
        year: int,
        month: int,
        enabled_obligations: List[str] = None
    ) -> List[models.StatutoryObligation]:
        """
        Generate all monthly statutory obligations for a given month
        
        enabled_obligations: List of obligation types to generate (e.g., ["PAYE", "NAPSA", "NHIMA", "VAT"])
        If None, generates all monthly obligations
        """
        if enabled_obligations is None:
            enabled_obligations = ["PAYE", "NAPSA", "NHIMA", "VAT", "WHT"]
        
        period_start = date(year, month, 1)
        period_end = (period_start + relativedelta(months=1)) - timedelta(days=1)
        
        # Due date is in the following month
        due_date_month = month + 1 if month < 12 else 1
        due_date_year = year if month < 12 else year + 1
        
        obligations = []
        
        for obligation_type in enabled_obligations:
            config = STATUTORY_OBLIGATIONS_CONFIG.get(obligation_type)
            if not config or config.get("frequency") != "monthly":
                continue
            
            # Calculate due date
            due_day = config["due_day"]
            due_date = date(due_date_year, due_date_month, due_day)
            
            # Check if obligation already exists
            existing = self.db.query(models.StatutoryObligation).filter(
                and_(
                    models.StatutoryObligation.company_id == company_id,
                    models.StatutoryObligation.obligation_type == obligation_type,
                    models.StatutoryObligation.period_start == period_start,
                    models.StatutoryObligation.period_end == period_end
                )
            ).first()
            
            if existing:
                logger.info(f"Obligation {obligation_type} for {year}-{month:02d} already exists")
                continue
            
            # Create obligation
            obligation = models.StatutoryObligation(
                company_id=company_id,
                obligation_type=obligation_type,
                obligation_name=config["name"],
                description=f"{config['name']} for {period_start.strftime('%B %Y')}",
                frequency="monthly",
                due_day_of_month=due_day,
                period_start=period_start,
                period_end=period_end,
                due_date=due_date,
                status="pending",
                compliance_status="not_started",
                alert_days_before=5,
                metadata={
                    "authority": config["authority"],
                    "penalty_rate": config.get("penalty_rate")
                }
            )
            
            self.db.add(obligation)
            self.db.flush()  # Get the ID
            
            # Create checklist items
            if "checklist" in config:
                for idx, item in enumerate(config["checklist"]):
                    checklist_item = models.ComplianceChecklist(
                        company_id=company_id,
                        obligation_id=obligation.id,
                        item_name=item["name"],
                        item_category=item["category"],
                        sequence_order=idx + 1,
                        is_required=True
                    )
                    self.db.add(checklist_item)
            
            obligations.append(obligation)
        
        self.db.commit()
        
        logger.info(f"Generated {len(obligations)} statutory obligations for {year}-{month:02d}")
        
        return obligations
    
    def generate_quarterly_obligations(
        self,
        company_id: str,
        year: int,
        quarter: int
    ) -> List[models.StatutoryObligation]:
        """Generate quarterly obligations (Provisional Tax)"""
        quarter_config = {
            1: {"month": 3, "due_month": 4, "type": "PROVISIONAL_TAX_Q1"},
            2: {"month": 6, "due_month": 7, "type": "PROVISIONAL_TAX_Q2"},
            3: {"month": 9, "due_month": 10, "type": "PROVISIONAL_TAX_Q3"},
            4: {"month": 12, "due_month": 1, "type": "PROVISIONAL_TAX_Q4"}
        }
        
        q_config = quarter_config[quarter]
        period_end = date(year, q_config["month"], self._get_last_day_of_month(year, q_config["month"]))
        period_start = date(year, ((quarter - 1) * 3) + 1, 1)
        
        due_year = year if q_config["due_month"] > q_config["month"] else year + 1
        due_date = date(due_year, q_config["due_month"], 10)
        
        obligation_type = q_config["type"]
        config = STATUTORY_OBLIGATIONS_CONFIG[obligation_type]
        
        obligation = models.StatutoryObligation(
            company_id=company_id,
            obligation_type=obligation_type,
            obligation_name=config["name"],
            description=f"Provisional Tax Q{quarter} {year}",
            frequency="quarterly",
            due_day_of_month=10,
            due_month=q_config["due_month"],
            period_start=period_start,
            period_end=period_end,
            due_date=due_date,
            status="pending",
            compliance_status="not_started",
            alert_days_before=10
        )
        
        self.db.add(obligation)
        self.db.commit()
        
        return [obligation]
    
    def calculate_compliance_percentage(self, obligation_id: str) -> Dict:
        """Calculate compliance percentage based on checklist completion"""
        checklist_items = self.db.query(models.ComplianceChecklist).filter(
            models.ComplianceChecklist.obligation_id == obligation_id
        ).all()
        
        if not checklist_items:
            return {
                "total_items": 0,
                "completed_items": 0,
                "completion_percentage": 0.0,
                "status": "no_checklist"
            }
        
        total_items = len(checklist_items)
        completed_items = sum(1 for item in checklist_items if item.is_completed)
        completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0.0
        
        # Determine status
        if completion_percentage == 0:
            status = "not_started"
        elif completion_percentage < 100:
            status = "in_progress"
        else:
            status = "completed"
        
        return {
            "total_items": total_items,
            "completed_items": completed_items,
            "pending_items": total_items - completed_items,
            "completion_percentage": round(completion_percentage, 2),
            "status": status,
            "breakdown_by_category": self._get_checklist_breakdown(checklist_items)
        }
    
    def _get_checklist_breakdown(self, checklist_items: List) -> Dict:
        """Break down checklist by category"""
        categories = {}
        for item in checklist_items:
            category = item.item_category or "other"
            if category not in categories:
                categories[category] = {"total": 0, "completed": 0}
            
            categories[category]["total"] += 1
            if item.is_completed:
                categories[category]["completed"] += 1
        
        for category in categories:
            total = categories[category]["total"]
            completed = categories[category]["completed"]
            categories[category]["percentage"] = (completed / total * 100) if total > 0 else 0.0
        
        return categories
    
    def get_compliance_dashboard(self, company_id: str, period: str = "current_month") -> Dict:
        """
        Get compliance dashboard with percentage tracking
        
        period: "current_month", "next_month", "current_quarter", "current_year"
        """
        today = date.today()
        
        if period == "current_month":
            start_date = date(today.year, today.month, 1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        elif period == "next_month":
            start_date = (date(today.year, today.month, 1) + relativedelta(months=1))
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        elif period == "current_year":
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        else:
            start_date = today - timedelta(days=30)
            end_date = today + timedelta(days=60)
        
        # Get all obligations in period
        obligations = self.db.query(models.StatutoryObligation).filter(
            and_(
                models.StatutoryObligation.company_id == company_id,
                models.StatutoryObligation.due_date >= start_date,
                models.StatutoryObligation.due_date <= end_date
            )
        ).order_by(models.StatutoryObligation.due_date).all()
        
        # Calculate statistics
        total_obligations = len(obligations)
        completed = sum(1 for o in obligations if o.status == "paid" or o.compliance_status == "completed")
        pending = sum(1 for o in obligations if o.status == "pending")
        overdue = sum(1 for o in obligations if o.status == "overdue" or (o.due_date < today and o.status == "pending"))
        
        overall_completion = (completed / total_obligations * 100) if total_obligations > 0 else 0.0
        
        # Upcoming deadlines (next 7 days)
        upcoming = [
            o for o in obligations 
            if o.due_date >= today and o.due_date <= today + timedelta(days=7) and o.status != "paid"
        ]
        
        # Get detailed compliance for each obligation
        detailed_obligations = []
        for obligation in obligations:
            compliance = self.calculate_compliance_percentage(obligation.id)
            detailed_obligations.append({
                "id": obligation.id,
                "type": obligation.obligation_type,
                "name": obligation.obligation_name,
                "due_date": obligation.due_date,
                "status": obligation.status,
                "compliance_status": obligation.compliance_status,
                "amount_due": obligation.amount_due,
                "amount_paid": obligation.amount_paid,
                "is_confirmed": obligation.confirmed_by_user,
                "compliance_percentage": compliance["completion_percentage"],
                "checklist_breakdown": compliance["breakdown_by_category"],
                "days_until_due": (obligation.due_date - today).days
            })
        
        return {
            "period": period,
            "period_start": start_date,
            "period_end": end_date,
            "summary": {
                "total_obligations": total_obligations,
                "completed": completed,
                "pending": pending,
                "overdue": overdue,
                "overall_completion_percentage": round(overall_completion, 2)
            },
            "upcoming_deadlines": [
                {
                    "obligation_id": o.id,
                    "name": o.obligation_name,
                    "due_date": o.due_date,
                    "days_until_due": (o.due_date - today).days,
                    "status": o.status
                }
                for o in upcoming
            ],
            "obligations": detailed_obligations
        }
    
    def check_and_send_alerts(self, company_id: str) -> List[models.Notification]:
        """Check for upcoming obligations and send alerts"""
        today = datetime.now().date()
        notifications_created = []
        
        # Get obligations that need alerts
        obligations = self.db.query(models.StatutoryObligation).filter(
            and_(
                models.StatutoryObligation.company_id == company_id,
                models.StatutoryObligation.status == "pending",
                models.StatutoryObligation.due_date >= today
            )
        ).all()
        
        for obligation in obligations:
            days_until_due = (obligation.due_date - today).days
            alert_days = obligation.alert_days_before or 5
            
            # Send alert if within alert window
            if days_until_due <= alert_days:
                # Check if already alerted today
                if obligation.last_alert_sent and obligation.last_alert_sent.date() == today:
                    continue
                
                # Create notification
                notification = self._create_statutory_alert_notification(
                    company_id=company_id,
                    obligation=obligation,
                    days_until_due=days_until_due
                )
                
                notifications_created.append(notification)
                
                # Update last alert sent
                obligation.last_alert_sent = datetime.now()
        
        if notifications_created:
            self.db.commit()
        
        logger.info(f"Created {len(notifications_created)} statutory alerts for company {company_id}")
        
        return notifications_created
    
    def _create_statutory_alert_notification(
        self,
        company_id: str,
        obligation: models.StatutoryObligation,
        days_until_due: int
    ) -> models.Notification:
        """Create a notification for statutory obligation alert"""
        # Determine priority and urgency
        if days_until_due <= 1:
            priority = "urgent"
            urgency_text = "URGENT: Due tomorrow!" if days_until_due == 1 else "CRITICAL: Due today!"
        elif days_until_due <= 3:
            priority = "high"
            urgency_text = f"Due in {days_until_due} days"
        else:
            priority = "normal"
            urgency_text = f"Due in {days_until_due} days"
        
        # Calculate compliance
        compliance = self.calculate_compliance_percentage(obligation.id)
        
        title = f"Statutory Obligation: {obligation.obligation_name}"
        message = f"""
{urgency_text}

{obligation.obligation_name} is due on {obligation.due_date.strftime('%d %B %Y')}.

Compliance Status: {compliance['completion_percentage']}% complete
({compliance['completed_items']}/{compliance['total_items']} checklist items completed)

Please ensure all requirements are met and payment is made before the due date to avoid penalties.
        """.strip()
        
        notification = models.Notification(
            company_id=company_id,
            notification_type="statutory_alert",
            title=title,
            message=message,
            reference_type="obligation",
            reference_id=obligation.id,
            priority=priority,
            delivery_channels=["in_app", "email"],
            action_url=f"/compliance/obligations/{obligation.id}"
        )
        
        self.db.add(notification)
        
        return notification
    
    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """Get last day of month"""
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)
        return last_day.day
