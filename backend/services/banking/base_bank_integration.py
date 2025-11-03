from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel

class BankTransaction(BaseModel):
    transaction_id: str
    transaction_date: date
    posting_date: Optional[date] = None
    description: str
    transaction_type: str
    amount: float
    balance_after: Optional[float] = None
    reference_number: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_account: Optional[str] = None
    currency: str = "ZMW"

class BankBalance(BaseModel):
    account_number: str
    available_balance: float
    ledger_balance: float
    currency: str = "ZMW"
    as_of_date: datetime

class BankConnectionStatus(BaseModel):
    is_connected: bool
    status_message: str
    last_sync_at: Optional[datetime] = None
    error_details: Optional[Dict[str, Any]] = None

class BaseBankIntegration(ABC):
    def __init__(self, api_username: str, api_key: str, api_endpoint: str, **kwargs):
        self.api_username = api_username
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        self.additional_config = kwargs
        self.bank_code = self.get_bank_code()
        self.bank_name = self.get_bank_name()
    
    @abstractmethod
    def get_bank_code(self) -> str:
        pass
    
    @abstractmethod
    def get_bank_name(self) -> str:
        pass
    
    @abstractmethod
    async def test_connection(self) -> BankConnectionStatus:
        pass
    
    @abstractmethod
    async def get_account_balance(self, account_number: str) -> BankBalance:
        pass
    
    @abstractmethod
    async def fetch_transactions(
        self, 
        account_number: str, 
        from_date: date, 
        to_date: date
    ) -> List[BankTransaction]:
        pass
    
    @abstractmethod
    async def get_account_statement(
        self, 
        account_number: str, 
        from_date: date, 
        to_date: date
    ) -> Dict[str, Any]:
        pass
    
    def encrypt_credentials(self, value: str) -> str:
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def decrypt_credentials(self, encrypted_value: str) -> str:
        import base64
        return base64.b64decode(encrypted_value.encode()).decode()
    
    async def normalize_transaction(self, raw_transaction: Dict[str, Any]) -> BankTransaction:
        return BankTransaction(
            transaction_id=str(raw_transaction.get("id", raw_transaction.get("transaction_id"))),
            transaction_date=self._parse_date(raw_transaction.get("date", raw_transaction.get("transaction_date"))),
            posting_date=self._parse_date(raw_transaction.get("posting_date")) if raw_transaction.get("posting_date") else None,
            description=raw_transaction.get("description", raw_transaction.get("narrative", "")),
            transaction_type=self._determine_transaction_type(raw_transaction),
            amount=float(raw_transaction.get("amount", 0)),
            balance_after=float(raw_transaction.get("balance")) if raw_transaction.get("balance") else None,
            reference_number=raw_transaction.get("reference", raw_transaction.get("ref")),
            counterparty_name=raw_transaction.get("counterparty_name"),
            counterparty_account=raw_transaction.get("counterparty_account"),
            currency=raw_transaction.get("currency", "ZMW")
        )
    
    def _parse_date(self, date_str: Any) -> date:
        if isinstance(date_str, date):
            return date_str
        if isinstance(date_str, datetime):
            return date_str.date()
        if isinstance(date_str, str):
            from dateutil import parser
            return parser.parse(date_str).date()
        return date.today()
    
    def _determine_transaction_type(self, transaction: Dict[str, Any]) -> str:
        amount = float(transaction.get("amount", 0))
        txn_type = transaction.get("type", "").lower()
        
        if "debit" in txn_type or amount < 0:
            return "debit"
        elif "credit" in txn_type or amount > 0:
            return "credit"
        elif "fee" in txn_type or "charge" in txn_type:
            return "fee"
        elif "interest" in txn_type:
            return "interest"
        else:
            return "credit" if amount >= 0 else "debit"
