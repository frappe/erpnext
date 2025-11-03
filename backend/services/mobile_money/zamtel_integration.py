import httpx
from typing import List, Dict, Any
from datetime import datetime
from .base_mobile_money import (
    BaseMobileMoneyIntegration,
    MobileMoneyTransactionModel,
    MobileMoneyBalance,
    MobileMoneyConnectionStatus
)

class ZamtelKwachaIntegration(BaseMobileMoneyIntegration):
    """
    Integration service for Zamtel Kwacha
    API Documentation: https://developer.zamtel.co.zm (simulated)
    """
    
    def get_provider_code(self) -> str:
        return "zamtel"
    
    def get_provider_name(self) -> str:
        return "Zamtel Kwacha"
    
    async def test_connection(self) -> MobileMoneyConnectionStatus:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "X-API-Username": self.api_username,
                    "Content-Type": "application/json"
                }
                
                response = await client.get(
                    f"{self.api_endpoint}/api/v1/auth/verify",
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return MobileMoneyConnectionStatus(
                        is_connected=True,
                        status_message="Connection successful",
                        last_sync_at=datetime.utcnow()
                    )
                else:
                    return MobileMoneyConnectionStatus(
                        is_connected=False,
                        status_message=f"Connection failed: {response.text}",
                        error_details={"status_code": response.status_code}
                    )
        except Exception as e:
            return MobileMoneyConnectionStatus(
                is_connected=False,
                status_message=f"Connection error: {str(e)}",
                error_details={"exception": str(e)}
            )
    
    async def get_balance(self) -> MobileMoneyBalance:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/wallet/balance",
                headers=headers,
                params={"phone": self.phone_number},
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return MobileMoneyBalance(
                provider_name=self.provider_name,
                phone_number=self.phone_number,
                available_balance=float(data.get("balance", 0)),
                currency="ZMW",
                as_of_date=datetime.utcnow()
            )
    
    async def fetch_transactions(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> List[MobileMoneyTransactionModel]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            params = {
                "phone": self.phone_number,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat()
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/transactions",
                headers=headers,
                params=params,
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("transactions", []):
                normalized = await self.normalize_transaction(txn)
                transactions.append(normalized)
            
            return transactions
    
    async def initiate_collection(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Collect payment from customer"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            payload = {
                "merchant_code": self.merchant_code,
                "customer_phone": phone_number,
                "amount": amount,
                "reference": reference,
                "description": description,
                "currency": "ZMW"
            }
            
            response = await client.post(
                f"{self.api_endpoint}/api/v1/payments/collect",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": data.get("status") == "success",
                "transaction_id": data.get("transaction_id"),
                "status": data.get("payment_status", "pending"),
                "message": data.get("message", "Collection initiated")
            }
    
    async def initiate_disbursement(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Send money to customer"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            payload = {
                "merchant_code": self.merchant_code,
                "recipient_phone": phone_number,
                "amount": amount,
                "reference": reference,
                "description": description,
                "currency": "ZMW"
            }
            
            response = await client.post(
                f"{self.api_endpoint}/api/v1/payments/disburse",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": data.get("status") == "success",
                "transaction_id": data.get("transaction_id"),
                "status": data.get("payment_status", "pending"),
                "message": data.get("message", "Disbursement initiated")
            }
    
    async def check_transaction_status(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-API-Username": self.api_username,
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/api/v1/transactions/{transaction_id}/status",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
