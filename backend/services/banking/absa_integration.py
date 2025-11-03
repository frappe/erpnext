import httpx
from typing import List, Dict, Any
from datetime import date, datetime
from .base_bank_integration import (
    BaseBankIntegration, 
    BankTransaction, 
    BankBalance, 
    BankConnectionStatus
)

class ABSAIntegration(BaseBankIntegration):
    """
    Integration service for ABSA Bank Zambia
    API Documentation: https://developer.absa.co.zm (simulated)
    """
    
    def get_bank_code(self) -> str:
        return "absa"
    
    def get_bank_name(self) -> str:
        return "ABSA Bank Zambia"
    
    async def test_connection(self) -> BankConnectionStatus:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"ApiKey {self.api_key}",
                    "X-Client-Id": self.api_username,
                    "Content-Type": "application/json"
                }
                
                response = await client.post(
                    f"{self.api_endpoint}/oauth/token",
                    headers=headers,
                    json={"grant_type": "client_credentials"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return BankConnectionStatus(
                        is_connected=True,
                        status_message="Connection successful",
                        last_sync_at=datetime.utcnow()
                    )
                else:
                    return BankConnectionStatus(
                        is_connected=False,
                        status_message=f"Authentication failed: {response.text}",
                        error_details={"status_code": response.status_code}
                    )
        except Exception as e:
            return BankConnectionStatus(
                is_connected=False,
                status_message=f"Connection error: {str(e)}",
                error_details={"exception": str(e)}
            )
    
    async def get_account_balance(self, account_number: str) -> BankBalance:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"ApiKey {self.api_key}",
                "X-Client-Id": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/accounts/{account_number}",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return BankBalance(
                account_number=account_number,
                available_balance=float(data.get("availableBalance", 0)),
                ledger_balance=float(data.get("currentBalance", 0)),
                currency=data.get("currency", "ZMW"),
                as_of_date=datetime.utcnow()
            )
    
    async def fetch_transactions(
        self, 
        account_number: str, 
        from_date: date, 
        to_date: date
    ) -> List[BankTransaction]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"ApiKey {self.api_key}",
                "X-Client-Id": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/accounts/{account_number}/transactions",
                headers=headers,
                params={
                    "fromDate": from_date.isoformat(),
                    "toDate": to_date.isoformat()
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("transactions", []):
                normalized_txn = await self.normalize_transaction({
                    "id": txn.get("transactionId"),
                    "date": txn.get("transactionDate"),
                    "posting_date": txn.get("valueDate"),
                    "description": txn.get("description"),
                    "amount": txn.get("amount"),
                    "type": txn.get("creditDebitIndicator"),
                    "balance": txn.get("balanceAfter"),
                    "reference": txn.get("reference"),
                    "currency": txn.get("currency", "ZMW")
                })
                transactions.append(normalized_txn)
            
            return transactions
    
    async def get_account_statement(
        self, 
        account_number: str, 
        from_date: date, 
        to_date: date
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"ApiKey {self.api_key}",
                "X-Client-Id": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/accounts/{account_number}/statement",
                headers=headers,
                params={
                    "fromDate": from_date.isoformat(),
                    "toDate": to_date.isoformat(),
                    "format": "json"
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            return response.json()
