from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class MobileMoneyTransactionModel(BaseModel):
    external_transaction_id: str
    transaction_date: datetime
    transaction_type: str  # collection, disbursement, transfer
    direction: str  # inbound, outbound
    amount: float
    currency: str = "ZMW"
    fee: float = 0.0
    counterparty_name: Optional[str] = None
    counterparty_phone: Optional[str] = None
    description: Optional[str] = None
    reference_number: Optional[str] = None
    status: str = "completed"

class MobileMoneyBalance(BaseModel):
    provider_name: str
    phone_number: str
    available_balance: float
    currency: str = "ZMW"
    as_of_date: datetime

class MobileMoneyConnectionStatus(BaseModel):
    is_connected: bool
    status_message: str
    last_sync_at: Optional[datetime] = None
    error_details: Optional[Dict[str, Any]] = None

class BaseMobileMoneyIntegration(ABC):
    def __init__(
        self,
        phone_number: str,
        api_username: str,
        api_key: str,
        api_secret: str,
        api_endpoint: str,
        merchant_code: Optional[str] = None,
        **kwargs
    ):
        self.phone_number = phone_number
        self.api_username = api_username
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_endpoint = api_endpoint
        self.merchant_code = merchant_code
        self.additional_config = kwargs
        self.provider_code = self.get_provider_code()
        self.provider_name = self.get_provider_name()
    
    @abstractmethod
    def get_provider_code(self) -> str:
        """Return provider code (mtn, airtel, zamtel)"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider display name"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> MobileMoneyConnectionStatus:
        """Test API connection and credentials"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> MobileMoneyBalance:
        """Get current balance for the mobile money account"""
        pass
    
    @abstractmethod
    async def fetch_transactions(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> List[MobileMoneyTransactionModel]:
        """Fetch transaction history"""
        pass
    
    @abstractmethod
    async def initiate_collection(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Initiate money collection (customer pays merchant)"""
        pass
    
    @abstractmethod
    async def initiate_disbursement(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Initiate money disbursement (merchant pays customer)"""
        pass
    
    @abstractmethod
    async def check_transaction_status(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        """Check status of a transaction"""
        pass
    
    def encrypt_credentials(self, value: str) -> str:
        """Encrypt sensitive credentials"""
        import base64
        return base64.b64encode(value.encode()).decode()
    
    def decrypt_credentials(self, encrypted_value: str) -> str:
        """Decrypt credentials"""
        import base64
        return base64.b64decode(encrypted_value.encode()).decode()
    
    async def normalize_transaction(
        self, 
        raw_transaction: Dict[str, Any]
    ) -> MobileMoneyTransactionModel:
        """Normalize raw transaction data to standard format"""
        return MobileMoneyTransactionModel(
            external_transaction_id=str(raw_transaction.get("id", raw_transaction.get("transaction_id"))),
            transaction_date=self._parse_datetime(raw_transaction.get("date", raw_transaction.get("created_at"))),
            transaction_type=self._normalize_type(raw_transaction.get("type")),
            direction=self._determine_direction(raw_transaction),
            amount=float(raw_transaction.get("amount", 0)),
            currency=raw_transaction.get("currency", "ZMW"),
            fee=float(raw_transaction.get("fee", raw_transaction.get("charge", 0))),
            counterparty_name=raw_transaction.get("counterparty_name", raw_transaction.get("customer_name")),
            counterparty_phone=raw_transaction.get("counterparty_phone", raw_transaction.get("phone")),
            description=raw_transaction.get("description", raw_transaction.get("narrative")),
            reference_number=raw_transaction.get("reference"),
            status=raw_transaction.get("status", "completed")
        )
    
    def _parse_datetime(self, date_str: Any) -> datetime:
        """Parse datetime from various formats"""
        if isinstance(date_str, datetime):
            return date_str
        if isinstance(date_str, str):
            from dateutil import parser
            return parser.parse(date_str)
        return datetime.utcnow()
    
    def _normalize_type(self, txn_type: str) -> str:
        """Normalize transaction type"""
        if not txn_type:
            return "transfer"
        
        txn_type = txn_type.lower()
        if "collect" in txn_type or "payment" in txn_type:
            return "collection"
        elif "disburse" in txn_type or "payout" in txn_type:
            return "disbursement"
        else:
            return "transfer"
    
    def _determine_direction(self, transaction: Dict[str, Any]) -> str:
        """Determine transaction direction"""
        txn_type = transaction.get("type", "").lower()
        amount = float(transaction.get("amount", 0))
        
        if "collect" in txn_type or "debit" in txn_type or "received" in txn_type:
            return "inbound"
        elif "disburse" in txn_type or "credit" in txn_type or "sent" in txn_type:
            return "outbound"
        else:
            return "inbound" if amount >= 0 else "outbound"
