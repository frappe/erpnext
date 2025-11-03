from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

class BankingService:
    """
    Universal banking integration service for Zambian banks:
    - ZANACO (Zambia National Commercial Bank)
    - ABSA Bank Zambia
    - FNB Zambia (First National Bank)
    - Stanbic Bank Zambia
    """
    
    def __init__(self):
        self.bank_adapters = {
            'zanaco': ZANACOAdapter(),
            'absa': ABSAAdapter(),
            'fnb': FNBAdapter(),
            'stanbic': StanbicAdapter()
        }
    
    def test_connection(self, bank_code: str, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test bank API connection"""
        adapter = self.bank_adapters.get(bank_code)
        if not adapter:
            return {"success": False, "error": f"Unsupported bank: {bank_code}"}
        
        try:
            result = adapter.test_connection(credentials)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fetch_transactions(
        self, 
        bank_code: str, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """Fetch transactions from bank API"""
        adapter = self.bank_adapters.get(bank_code)
        if not adapter:
            return {"success": False, "error": f"Unsupported bank: {bank_code}"}
        
        try:
            transactions = adapter.fetch_transactions(
                credentials, account_number, from_date, to_date
            )
            return {"success": True, "transactions": transactions}
        except Exception as e:
            return {"success": False, "error": str(e), "transactions": []}
    
    def get_account_balance(
        self, 
        bank_code: str, 
        credentials: Dict[str, str],
        account_number: str
    ) -> Dict[str, Any]:
        """Get current account balance"""
        adapter = self.bank_adapters.get(bank_code)
        if not adapter:
            return {"success": False, "error": f"Unsupported bank: {bank_code}"}
        
        try:
            balance = adapter.get_account_balance(credentials, account_number)
            return {"success": True, "balance": balance}
        except Exception as e:
            return {"success": False, "error": str(e)}


class BankAdapter:
    """Base adapter for bank API integration"""
    
    def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test API connection"""
        raise NotImplementedError
    
    def fetch_transactions(
        self, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch transactions from bank"""
        raise NotImplementedError
    
    def get_account_balance(self, credentials: Dict[str, str], account_number: str) -> Dict[str, Any]:
        """Get account balance"""
        raise NotImplementedError
    
    def normalize_transaction(self, raw_transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Convert bank-specific format to standard format"""
        return {
            "bank_transaction_id": raw_transaction.get("id") or raw_transaction.get("reference"),
            "transaction_date": raw_transaction.get("date") or raw_transaction.get("value_date"),
            "posting_date": raw_transaction.get("posting_date"),
            "description": raw_transaction.get("description") or raw_transaction.get("narrative"),
            "transaction_type": raw_transaction.get("type") or raw_transaction.get("dr_cr"),
            "amount": abs(float(raw_transaction.get("amount", 0))),
            "balance_after": raw_transaction.get("balance"),
            "reference_number": raw_transaction.get("reference"),
            "counterparty_name": raw_transaction.get("counterparty") or raw_transaction.get("payee"),
            "category": self._categorize_transaction(raw_transaction)
        }
    
    def _categorize_transaction(self, transaction: Dict[str, Any]) -> str:
        """Auto-categorize transaction based on description"""
        description = (transaction.get("description") or "").lower()
        
        if any(word in description for word in ["payment", "pay", "purchase"]):
            return "payment"
        elif any(word in description for word in ["transfer", "tfr", "trf"]):
            return "transfer"
        elif any(word in description for word in ["withdrawal", "atm", "cash"]):
            return "withdrawal"
        elif any(word in description for word in ["deposit", "credit"]):
            return "deposit"
        elif any(word in description for word in ["fee", "charge", "commission"]):
            return "fee"
        else:
            return "other"


class ZANACOAdapter(BankAdapter):
    """ZANACO Bank API Adapter"""
    
    def __init__(self):
        self.base_url = "https://api.zanaco.co.zm/v1"  # Placeholder URL
        self.bank_name = "ZANACO"
    
    def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test ZANACO API connection"""
        # DEMO MODE: Return success without actual API call
        return {
            "status": "connected",
            "bank": self.bank_name,
            "message": "Connection successful (demo mode)"
        }
    
    def fetch_transactions(
        self, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch ZANACO transactions"""
        # DEMO MODE: Return sample transactions
        demo_transactions = self._generate_demo_transactions(from_date, to_date)
        return [self.normalize_transaction(t) for t in demo_transactions]
    
    def get_account_balance(self, credentials: Dict[str, str], account_number: str) -> Dict[str, Any]:
        """Get ZANACO account balance"""
        # DEMO MODE: Return demo balance
        return {
            "available_balance": 150000.00,
            "current_balance": 152500.00,
            "currency": "ZMW",
            "account_number": account_number
        }
    
    def _generate_demo_transactions(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """Generate demo transactions for testing"""
        transactions = []
        current_date = from_date
        balance = 150000.00
        
        while current_date <= to_date:
            # Generate 1-3 transactions per day
            for i in range(1, 3):
                amount = (i * 1000) + (current_date.day * 100)
                transaction_type = "credit" if i % 2 == 0 else "debit"
                
                if transaction_type == "credit":
                    balance += amount
                else:
                    balance -= amount
                
                transactions.append({
                    "id": f"ZANACO-{current_date.strftime('%Y%m%d')}-{i:03d}",
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": f"Demo transaction {i}",
                    "type": transaction_type,
                    "amount": amount if transaction_type == "credit" else -amount,
                    "balance": balance,
                    "reference": f"REF{current_date.strftime('%Y%m%d')}{i}"
                })
            
            current_date += timedelta(days=1)
        
        return transactions


class ABSAAdapter(BankAdapter):
    """ABSA Bank Zambia API Adapter"""
    
    def __init__(self):
        self.base_url = "https://api.absa.co.zm/v1"  # Placeholder URL
        self.bank_name = "ABSA"
    
    def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        return {
            "status": "connected",
            "bank": self.bank_name,
            "message": "Connection successful (demo mode)"
        }
    
    def fetch_transactions(
        self, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        demo_transactions = self._generate_demo_transactions(from_date, to_date)
        return [self.normalize_transaction(t) for t in demo_transactions]
    
    def get_account_balance(self, credentials: Dict[str, str], account_number: str) -> Dict[str, Any]:
        return {
            "available_balance": 200000.00,
            "current_balance": 205000.00,
            "currency": "ZMW",
            "account_number": account_number
        }
    
    def _generate_demo_transactions(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        transactions = []
        current_date = from_date
        balance = 200000.00
        
        while current_date <= to_date:
            for i in range(1, 2):
                amount = (i * 1500) + (current_date.day * 150)
                transaction_type = "credit" if i % 2 == 0 else "debit"
                
                if transaction_type == "credit":
                    balance += amount
                else:
                    balance -= amount
                
                transactions.append({
                    "id": f"ABSA-{current_date.strftime('%Y%m%d')}-{i:03d}",
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": f"ABSA Demo transaction {i}",
                    "type": transaction_type,
                    "amount": amount if transaction_type == "credit" else -amount,
                    "balance": balance,
                    "reference": f"ABS{current_date.strftime('%Y%m%d')}{i}"
                })
            
            current_date += timedelta(days=1)
        
        return transactions


class FNBAdapter(BankAdapter):
    """FNB Zambia API Adapter"""
    
    def __init__(self):
        self.base_url = "https://api.fnbzambia.co.zm/v1"  # Placeholder URL
        self.bank_name = "FNB"
    
    def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        return {
            "status": "connected",
            "bank": self.bank_name,
            "message": "Connection successful (demo mode)"
        }
    
    def fetch_transactions(
        self, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        demo_transactions = self._generate_demo_transactions(from_date, to_date)
        return [self.normalize_transaction(t) for t in demo_transactions]
    
    def get_account_balance(self, credentials: Dict[str, str], account_number: str) -> Dict[str, Any]:
        return {
            "available_balance": 180000.00,
            "current_balance": 182000.00,
            "currency": "ZMW",
            "account_number": account_number
        }
    
    def _generate_demo_transactions(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        transactions = []
        current_date = from_date
        balance = 180000.00
        
        while current_date <= to_date:
            for i in range(1, 3):
                amount = (i * 1200) + (current_date.day * 120)
                transaction_type = "credit" if i % 2 == 0 else "debit"
                
                if transaction_type == "credit":
                    balance += amount
                else:
                    balance -= amount
                
                transactions.append({
                    "id": f"FNB-{current_date.strftime('%Y%m%d')}-{i:03d}",
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": f"FNB Demo transaction {i}",
                    "type": transaction_type,
                    "amount": amount if transaction_type == "credit" else -amount,
                    "balance": balance,
                    "reference": f"FNB{current_date.strftime('%Y%m%d')}{i}"
                })
            
            current_date += timedelta(days=1)
        
        return transactions


class StanbicAdapter(BankAdapter):
    """Stanbic Bank Zambia API Adapter"""
    
    def __init__(self):
        self.base_url = "https://api.stanbicbank.co.zm/v1"  # Placeholder URL
        self.bank_name = "Stanbic"
    
    def test_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        return {
            "status": "connected",
            "bank": self.bank_name,
            "message": "Connection successful (demo mode)"
        }
    
    def fetch_transactions(
        self, 
        credentials: Dict[str, str],
        account_number: str,
        from_date: datetime,
        to_date: datetime
    ) -> List[Dict[str, Any]]:
        demo_transactions = self._generate_demo_transactions(from_date, to_date)
        return [self.normalize_transaction(t) for t in demo_transactions]
    
    def get_account_balance(self, credentials: Dict[str, str], account_number: str) -> Dict[str, Any]:
        return {
            "available_balance": 220000.00,
            "current_balance": 225000.00,
            "currency": "ZMW",
            "account_number": account_number
        }
    
    def _generate_demo_transactions(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        transactions = []
        current_date = from_date
        balance = 220000.00
        
        while current_date <= to_date:
            for i in range(1, 4):
                amount = (i * 1800) + (current_date.day * 180)
                transaction_type = "credit" if i % 2 == 0 else "debit"
                
                if transaction_type == "credit":
                    balance += amount
                else:
                    balance -= amount
                
                transactions.append({
                    "id": f"STANBIC-{current_date.strftime('%Y%m%d')}-{i:03d}",
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": f"Stanbic Demo transaction {i}",
                    "type": transaction_type,
                    "amount": amount if transaction_type == "credit" else -amount,
                    "balance": balance,
                    "reference": f"STB{current_date.strftime('%Y%m%d')}{i}"
                })
            
            current_date += timedelta(days=1)
        
        return transactions
