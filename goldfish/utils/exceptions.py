from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class GoldfishException(Exception):
    """Base exception class for Goldfish"""
    pass

# ... (rest of the file remains the same)