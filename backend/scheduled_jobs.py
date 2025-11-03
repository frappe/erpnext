"""
Scheduled Background Jobs for ERIK ERP

Jobs:
1. Monthly Obligation Generation (1st of each month)
2. Compliance Alert Checking (Daily at 8 AM)
3. Statutory Deadline Reminders (Daily at 9 AM)
"""

import os
import logging
from datetime import date, datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from services.compliance.statutory_compliance import StatutoryComplianceService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def generate_monthly_obligations_job():
    """
    Job: Generate statutory obligations for the current month
    Schedule: 1st day of each month at 1:00 AM
    """
    logger.info("Starting monthly obligation generation job...")
    
    db = SessionLocal()
    try:
        today = date.today()
        year = today.year
        month = today.month
        
        companies = db.query(models.Company).filter(models.Company.is_active == True).all()
        
        total_generated = 0
        for company in companies:
            try:
                compliance_service = StatutoryComplianceService(db, company.id)
                obligations = compliance_service.generate_monthly_obligations(year, month)
                total_generated += len(obligations)
                logger.info(f"Generated {len(obligations)} obligations for company {company.name}")
            except Exception as e:
                logger.error(f"Error generating obligations for company {company.id}: {str(e)}")
        
        logger.info(f"Monthly obligation generation completed. Total: {total_generated} obligations")
    
    except Exception as e:
        logger.error(f"Error in monthly obligation generation job: {str(e)}")
    finally:
        db.close()


def check_compliance_alerts_job():
    """
    Job: Check for upcoming statutory deadlines and send alerts
    Schedule: Daily at 8:00 AM
    """
    logger.info("Starting compliance alerts check job...")
    
    db = SessionLocal()
    try:
        companies = db.query(models.Company).filter(models.Company.is_active == True).all()
        
        total_alerts = 0
        for company in companies:
            try:
                compliance_service = StatutoryComplianceService(db, company.id)
                alerts_sent = compliance_service.check_and_send_alerts()
                total_alerts += alerts_sent
                logger.info(f"Sent {alerts_sent} alerts for company {company.name}")
            except Exception as e:
                logger.error(f"Error checking alerts for company {company.id}: {str(e)}")
        
        logger.info(f"Compliance alerts check completed. Total: {total_alerts} alerts sent")
    
    except Exception as e:
        logger.error(f"Error in compliance alerts job: {str(e)}")
    finally:
        db.close()


def send_statutory_reminders_job():
    """
    Job: Send reminders for upcoming statutory payments
    Schedule: Daily at 9:00 AM
    """
    logger.info("Starting statutory reminders job...")
    
    db = SessionLocal()
    try:
        today = date.today()
        alert_date = today + timedelta(days=3)
        
        obligations = db.query(models.StatutoryObligation).filter(
            models.StatutoryObligation.due_date == alert_date,
            models.StatutoryObligation.status.in_(['pending', 'submitted'])
        ).all()
        
        for obligation in obligations:
            try:
                notification = models.Notification(
                    company_id=obligation.company_id,
                    user_id=None,
                    title=f"Reminder: {obligation.obligation_type} due in 3 days",
                    message=f"{obligation.obligation_type} for {obligation.year}-{obligation.month:02d} is due on {obligation.due_date}. Amount: ZMW {obligation.amount}",
                    notification_type="alert",
                    priority="high",
                    related_type="statutory_obligation",
                    related_id=obligation.id
                )
                db.add(notification)
                db.commit()
                logger.info(f"Sent reminder for obligation {obligation.id}")
            except Exception as e:
                logger.error(f"Error sending reminder for obligation {obligation.id}: {str(e)}")
                db.rollback()
        
        logger.info(f"Statutory reminders completed. {len(obligations)} reminders sent")
    
    except Exception as e:
        logger.error(f"Error in statutory reminders job: {str(e)}")
    finally:
        db.close()


def cleanup_old_notifications_job():
    """
    Job: Clean up read notifications older than 30 days
    Schedule: Weekly on Sunday at 2:00 AM
    """
    logger.info("Starting old notifications cleanup job...")
    
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=30)
        
        deleted_count = db.query(models.Notification).filter(
            models.Notification.is_read == True,
            models.Notification.created_at < cutoff_date
        ).delete()
        
        db.commit()
        logger.info(f"Cleaned up {deleted_count} old notifications")
    
    except Exception as e:
        logger.error(f"Error in cleanup job: {str(e)}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Initialize and start the background scheduler"""
    
    logger.info("Initializing background job scheduler...")
    
    # Job 1: Generate monthly obligations (1st of month at 1:00 AM)
    scheduler.add_job(
        generate_monthly_obligations_job,
        CronTrigger(day=1, hour=1, minute=0),
        id='generate_monthly_obligations',
        name='Generate Monthly Statutory Obligations',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Monthly obligation generation (1st day, 1:00 AM)")
    
    # Job 2: Check compliance alerts (Daily at 8:00 AM)
    scheduler.add_job(
        check_compliance_alerts_job,
        CronTrigger(hour=8, minute=0),
        id='check_compliance_alerts',
        name='Check Compliance Alerts',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Compliance alerts (Daily, 8:00 AM)")
    
    # Job 3: Send statutory reminders (Daily at 9:00 AM)
    scheduler.add_job(
        send_statutory_reminders_job,
        CronTrigger(hour=9, minute=0),
        id='send_statutory_reminders',
        name='Send Statutory Reminders',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Statutory reminders (Daily, 9:00 AM)")
    
    # Job 4: Cleanup old notifications (Weekly on Sunday at 2:00 AM)
    scheduler.add_job(
        cleanup_old_notifications_job,
        CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='cleanup_notifications',
        name='Cleanup Old Notifications',
        replace_existing=True
    )
    logger.info("✓ Scheduled: Notification cleanup (Weekly, Sunday 2:00 AM)")
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background job scheduler started successfully!")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background job scheduler stopped")


def run_job_now(job_id):
    """Manually trigger a job (for testing)"""
    job = scheduler.get_job(job_id)
    if job:
        job.func()
        logger.info(f"Manually executed job: {job_id}")
    else:
        logger.error(f"Job not found: {job_id}")
