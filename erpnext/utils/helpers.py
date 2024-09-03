import uuid
from datetime import datetime

def generate_name(prefix: str = ""):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

def now_datetime():
    return datetime.utcnow()

def format_currency(amount: float, currency: str = "USD"):
    return f"{currency} {amount:.2f}"

# Add more utility functions as needed