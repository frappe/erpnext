import httpx
from typing import List, Dict, Any
from datetime import date, datetime
from .base_bank_integration import (
    BaseBankIntegration, 
    BankTransaction, 
    BankBalance, 
    BankConnectionStatus
)

class FNBIntegration(BaseBankIntegration):
    """
    Integration service for FNB (First National Bank) Zambia
    API Documentation: https://developer.fnb.co.zm (simulated)
    """
    
    def get_bank_code(self) -> str:
        return "fnb"
    
    def get_bank_name(self) -> str:
        return "FNB Zambia"
    
    async def test_connection(self) -> BankConnectionStatus:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Basic {self.api_key}",
                    "X-Username": self.api_username,
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.api_endpoint}/v2/health",
                    headers=headers,
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
                "Authorization": f"Basic {self.api_key}",
                "X-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v2/accounts/{account_number}/balances",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            balances = data.get("balances", {})
            
            return BankBalance(
                account_number=account_number,
                available_balance=float(balances.get("available_balance", 0)),
                ledger_balance=float(balances.get("book_balance", 0)),
                currency=balances.get("currency_code", "ZMW"),
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
                "Authorization": f"Basic {self.api_key}",
                "X-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v2/accounts/{account_number}/transactions",
                headers=headers,
                params={
                    "start_date": from_date.isoformat(),
                    "end_date": to_date.isoformat()
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("transaction_list", []):
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
                "Authorization": f"Basic {self.api_key}",
                "X-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/v2/accounts/{account_number}/statement",
                headers=headers,
                params={
                    "start_date": from_date.isoformat(),
                    "end_date": to_date.isoformat(),
                    "output_format": "json"
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            return response.json()
