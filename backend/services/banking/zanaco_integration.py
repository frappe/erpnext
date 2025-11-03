import httpx
from typing import List, Dict, Any
from datetime import date
from .base_bank_integration import (
    BaseBankIntegration, 
    BankTransaction, 
    BankBalance, 
    BankConnectionStatus
)

class ZanacoIntegration(BaseBankIntegration):
    """
    Integration service for ZANACO Bank (Zambia National Commercial Bank)
    API Documentation: https://developer.zanaco.co.zm (simulated)
    """
    
    def get_bank_code(self) -> str:
        return "zanaco"
    
    def get_bank_name(self) -> str:
        return "ZANACO"
    
    async def test_connection(self) -> BankConnectionStatus:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "X-API-Username": self.api_username,
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.api_endpoint}/v1/auth/verify",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return BankConnectionStatus(
                        is_connected=True,
                        status_message="Connection successful",
                        last_sync_at=None
                    )
                else:
                    return BankConnectionStatus(
                        is_connected=False,
                        status_message=f"Connection failed: {response.text}",
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
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v1/accounts/{account_number}/balance",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return BankBalance(
                account_number=account_number,
                available_balance=float(data.get("available_balance", 0)),
                ledger_balance=float(data.get("ledger_balance", 0)),
                currency=data.get("currency", "ZMW"),
                as_of_date=data.get("as_of_date")
            )
    
    async def fetch_transactions(
        self, 
        account_number: str, 
        from_date: date, 
        to_date: date
    ) -> List[BankTransaction]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            params = {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "account_number": account_number
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v1/accounts/{account_number}/transactions",
                headers=headers,
                params=params,
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("transactions", []):
                normalized_txn = await self.normalize_transaction(txn)
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
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            params = {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat()
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v1/accounts/{account_number}/statement",
                headers=headers,
                params=params,
                timeout=60.0
            )
            
            response.raise_for_status()
            return response.json()
