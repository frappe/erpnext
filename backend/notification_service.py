import os
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service for sending email and SMS notifications.
    
    In production, configure these environment variables:
    - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD for email
    - SMS_API_KEY, SMS_API_URL for SMS (Twilio, Africa's Talking, etc.)
    """
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = os.getenv("SMTP_PORT", 587)
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sms_api_key = os.getenv("SMS_API_KEY")
        self.sms_api_url = os.getenv("SMS_API_URL")
        
    def send_notification(self, notification: models.Notification, user_email: str, user_phone: Optional[str], db: Session):
        """
        Send notification via configured channels (in_app, email, sms, all).
        Updates the notification record with delivery status.
        """
        
        # In-app notifications are always saved to database (already done)
        
        # Send email if channel is email or all
        if notification.channel in ['email', 'all']:
            email_sent = self._send_email(
                to_email=user_email,
                subject=notification.title,
                body=notification.message,
                action_url=notification.action_url,
                action_label=notification.action_label
            )
            
            if email_sent:
                notification.email_sent = True
                notification.email_sent_at = datetime.utcnow()
                db.commit()
        
        # Send SMS if channel is sms or all
        if notification.channel in ['sms', 'all'] and user_phone:
            sms_sent = self._send_sms(
                to_phone=user_phone,
                message=f"{notification.title}: {notification.message}"
            )
            
            if sms_sent:
                notification.sms_sent = True
                notification.sms_sent_at = datetime.utcnow()
                db.commit()
    
    def _send_email(self, to_email: str, subject: str, body: str, action_url: Optional[str] = None, action_label: Optional[str] = None) -> bool:
        """
        Send email notification.
        
        In production, this would use SMTP or a transactional email service.
        Currently logs the email for demonstration purposes.
        """
        
        try:
            # Check if SMTP is configured
            if self.smtp_host and self.smtp_user and self.smtp_password:
                # Production email sending with SMTP
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = self.smtp_user
                msg['To'] = to_email
                
                # Create HTML email body
                html_body = f"""
                <html>
                  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                      <div style="background: linear-gradient(135deg, #1a1f36 0%, #0a0f24 100%); padding: 30px; border-radius: 10px; margin-bottom: 20px;">
                        <h1 style="color: #00D9A3; margin: 0;">ERIK ERP</h1>
                      </div>
                      <div style="background: #f5f5f5; padding: 30px; border-radius: 10px;">
                        <h2 style="color: #1a1f36; margin-top: 0;">{subject}</h2>
                        <p style="color: #555; font-size: 16px;">{body}</p>
                        {f'<a href="{action_url}" style="display: inline-block; background: #00D9A3; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin-top: 20px;">{action_label}</a>' if action_url and action_label else ''}
                      </div>
                      <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
                        <p>This is an automated notification from ERIK ERP</p>
                      </div>
                    </div>
                  </body>
                </html>
                """
                
                # Plain text fallback
                text_body = f"{subject}\n\n{body}"
                if action_url and action_label:
                    text_body += f"\n\n{action_label}: {action_url}"
                
                msg.attach(MIMEText(text_body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
                
                with smtplib.SMTP(self.smtp_host, int(self.smtp_port)) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                
                logger.info(f"Email sent to {to_email}: {subject}")
                return True
            else:
                # Demo mode - log email instead of sending
                logger.info(f"""
                ============ EMAIL NOTIFICATION (Demo Mode) ============
                To: {to_email}
                Subject: {subject}
                Body: {body}
                Action: {action_label} ({action_url})
                ========================================================
                """)
                # In demo mode, we still mark as sent for testing purposes
                return True
                
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def _send_sms(self, to_phone: str, message: str) -> bool:
        """
        Send SMS notification.
        
        In production, this would integrate with:
        - Twilio (global)
        - Africa's Talking (African markets)
        - Zamtel/MTN/Airtel SMS gateways (Zambia-specific)
        
        Currently logs the SMS for demonstration purposes.
        """
        
        try:
            # Check if SMS API is configured
            if self.sms_api_key and self.sms_api_url:
                # Production SMS sending
                import requests
                
                # Example for generic SMS API
                response = requests.post(
                    self.sms_api_url,
                    headers={'Authorization': f'Bearer {self.sms_api_key}'},
                    json={
                        'to': to_phone,
                        'message': message
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    logger.info(f"SMS sent to {to_phone}")
                    return True
                else:
                    logger.error(f"SMS API returned status {response.status_code}")
                    return False
            else:
                # Demo mode - log SMS instead of sending
                logger.info(f"""
                ============ SMS NOTIFICATION (Demo Mode) =============
                To: {to_phone}
                Message: {message}
                ========================================================
                """)
                # In demo mode, we still mark as sent for testing purposes
                return True
                
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_phone}: {str(e)}")
            return False

# Singleton instance
notification_service = NotificationService()
