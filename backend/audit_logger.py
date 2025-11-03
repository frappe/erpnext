"""
Audit logging utility for ERIK ERP.

Provides automatic audit trail tracking for all system actions.
Captures user actions, changes, IP addresses, and user agents.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

class AuditLogger:
    """
    Centralized audit logging service.
    
    Tracks all user actions across the system for compliance,
    security, and debugging purposes.
    """
    
    @staticmethod
    def log(
        db: Session,
        company_id: str,
        user_id: Optional[str],
        user_email: Optional[str],
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        request: Optional[Request] = None
    ) -> models.AuditLog:
        """
        Create an audit log entry.
        
        Args:
            db: Database session
            company_id: Company ID (multi-tenant)
            user_id: User who performed the action
            user_email: User email (cached for deleted users)
            action: Action type (CREATE, READ, UPDATE, DELETE, LOGIN, etc.)
            entity_type: Type of entity affected (Invoice, Employee, etc.)
            entity_id: ID of the entity affected
            changes: Before/after state changes (JSON)
            ip_address: Client IP address
            user_agent: Client user agent string
            status: success, failure, error
            error_message: Error details if status is failure/error
            request: FastAPI Request object (auto-extracts IP and user agent)
        
        Returns:
            Created AuditLog instance
        """
        try:
            # Extract IP and user agent from request if provided
            if request:
                if not ip_address:
                    ip_address = request.client.host if request.client else None
                if not user_agent:
                    user_agent = request.headers.get("user-agent")
            
            # Create audit log entry
            audit_log = models.AuditLog(
                company_id=company_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                changes=changes,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            logger.info(f"Audit log created: {action} on {entity_type} by {user_email}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            db.rollback()
            # Don't raise - audit logging should never break the main operation
            return None
    
    @staticmethod
    def log_login(
        db: Session,
        user: models.User,
        request: Request,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """Log user login attempt."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id if user.company_id else "system",
            user_id=user.id if status == "success" else None,
            user_email=user.email,
            action="LOGIN",
            status=status,
            error_message=error_message,
            request=request
        )
    
    @staticmethod
    def log_login_attempt(
        db: Session,
        email: str,
        request: Request,
        status: str = "failure",
        error_message: str = "Authentication failed"
    ):
        """
        Log login attempt for unknown or unauthenticated users.
        
        Critical for security compliance - logs ALL login attempts including:
        - Unknown usernames (credential stuffing detection)
        - Invalid passwords
        - Account lockouts
        - Brute force attempts
        
        Uses 'system' as company_id for unknown users to ensure
        all attempts are tracked even without company context.
        """
        return AuditLogger.log(
            db=db,
            company_id="system",  # Safe fallback for unknown users
            user_id=None,
            user_email=email,
            action="LOGIN_ATTEMPT",
            status=status,
            error_message=error_message,
            request=request
        )
    
    @staticmethod
    def log_logout(
        db: Session,
        user: models.User,
        request: Request
    ):
        """Log user logout."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="LOGOUT",
            request=request
        )
    
    @staticmethod
    def log_create(
        db: Session,
        user: models.User,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log entity creation."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="CREATE",
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"new": data},
            request=request
        )
    
    @staticmethod
    def log_update(
        db: Session,
        user: models.User,
        entity_type: str,
        entity_id: str,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log entity update with before/after state."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="UPDATE",
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"old": old_data, "new": new_data},
            request=request
        )
    
    @staticmethod
    def log_delete(
        db: Session,
        user: models.User,
        entity_type: str,
        entity_id: str,
        data: Dict[str, Any],
        request: Optional[Request] = None
    ):
        """Log entity deletion."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="DELETE",
            entity_type=entity_type,
            entity_id=entity_id,
            changes={"deleted": data},
            request=request
        )
    
    @staticmethod
    def log_read(
        db: Session,
        user: models.User,
        entity_type: str,
        entity_id: Optional[str] = None,
        request: Optional[Request] = None
    ):
        """Log entity read/view (for sensitive data)."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="READ",
            entity_type=entity_type,
            entity_id=entity_id,
            request=request
        )
    
    @staticmethod
    def log_export(
        db: Session,
        user: models.User,
        entity_type: str,
        format: str,
        filters: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None
    ):
        """Log data export."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="EXPORT",
            entity_type=entity_type,
            changes={"format": format, "filters": filters},
            request=request
        )
    
    @staticmethod
    def log_permission_change(
        db: Session,
        user: models.User,
        target_user_email: str,
        old_role: str,
        new_role: str,
        request: Optional[Request] = None
    ):
        """Log permission/role changes."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action="PERMISSION_CHANGE",
            entity_type="User",
            changes={
                "target_user": target_user_email,
                "old_role": old_role,
                "new_role": new_role
            },
            request=request
        )
    
    @staticmethod
    def log_failed_operation(
        db: Session,
        user: models.User,
        action: str,
        entity_type: str,
        error_message: str,
        request: Optional[Request] = None
    ):
        """Log failed operations for security monitoring."""
        return AuditLogger.log(
            db=db,
            company_id=user.company_id,
            user_id=user.id,
            user_email=user.email,
            action=action,
            entity_type=entity_type,
            status="failure",
            error_message=error_message,
            request=request
        )

# Global instance
audit_logger = AuditLogger()
