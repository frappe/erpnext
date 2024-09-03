from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class GoldfishException(Exception):
    """Base exception class for Goldfish"""
    pass

class ValidationError(GoldfishException):
    """Raised when data validation fails"""
    pass

class NotFoundError(GoldfishException):
    """Raised when a requested resource is not found"""
    pass

class InsufficientStockError(GoldfishException):
    """Raised when there's not enough stock for an operation"""
    pass

class WorkflowError(GoldfishException):
    """Raised when there's an error in workflow operations"""
    pass

class AuthenticationError(GoldfishException):
    """Raised when there's an authentication error"""
    pass

class AuthorizationError(GoldfishException):
    """Raised when a user doesn't have the required permissions"""
    pass

class DatabaseError(GoldfishException):
    """Raised when there's a database-related error"""
    pass

async def Goldfish_exception_handler(request: Request, exc: GoldfishException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )