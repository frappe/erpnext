import httpx
from typing import List, Dict, Any
from datetime import datetime
from .base_mobile_money import (
    BaseMobileMoneyIntegration,
    MobileMoneyTransactionModel,
    MobileMoneyBalance,
    MobileMoneyConnectionStatus
)

class AirtelMoneyIntegration(BaseMobileMoneyIntegration):
    """
    Integration service for Airtel Money Zambia
    API Documentation: https://developers.airtel.africa
    """
    
    def get_provider_code(self) -> str:
        return "airtel"
    
    def get_provider_name(self) -> str:
        return "Airtel Money"
    
    async def test_connection(self) -> MobileMoneyConnectionStatus:
        try:
            token = await self._get_access_token()
            if token:
                return MobileMoneyConnectionStatus(
                    is_connected=True,
                    status_message="Connection successful",
                    last_sync_at=datetime.utcnow()
                )
            else:
                return MobileMoneyConnectionStatus(
                    is_connected=False,
                    status_message="Failed to obtain access token",
                    error_details={}
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
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Country": "ZM",
                "X-Currency": "ZMW",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/merchant/v1/balance",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return MobileMoneyBalance(
                provider_name=self.provider_name,
                phone_number=self.phone_number,
                available_balance=float(data.get("data", {}).get("balance", 0)),
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
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Country": "ZM",
                "X-Currency": "ZMW",
                "Content-Type": "application/json"
            }
            
            params = {
                "start_date": from_date.strftime("%Y-%m-%d"),
                "end_date": to_date.strftime("%Y-%m-%d")
            }
            
            response = await client.get(
                f"{self.api_endpoint}/merchant/v1/transactions",
                headers=headers,
                params=params,
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            transactions = []
            for txn in data.get("data", {}).get("transactions", []):
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
        """Push collection (customer pays merchant)"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Country": "ZM",
                "X-Currency": "ZMW",
                "Content-Type": "application/json"
            }
            
            payload = {
                "reference": reference,
                "subscriber": {
                    "country": "ZM",
                    "currency": "ZMW",
                    "msisdn": phone_number
                },
                "transaction": {
                    "amount": amount,
                    "country": "ZM",
                    "currency": "ZMW",
                    "id": reference
                }
            }
            
            response = await client.post(
                f"{self.api_endpoint}/merchant/v1/payments/",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": data.get("status", {}).get("success", False),
                "transaction_id": data.get("data", {}).get("transaction", {}).get("id"),
                "status": data.get("data", {}).get("transaction", {}).get("status", "pending"),
                "message": data.get("status", {}).get("message", "Collection initiated")
            }
    
    async def initiate_disbursement(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Disburse funds to customer"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Country": "ZM",
                "X-Currency": "ZMW",
                "Content-Type": "application/json"
            }
            
            payload = {
                "payee": {
                    "msisdn": phone_number
                },
                "reference": reference,
                "pin": self.api_secret,  # PIN for disbursement
                "transaction": {
                    "amount": amount,
                    "id": reference
                }
            }
            
            response = await client.post(
                f"{self.api_endpoint}/standard/v1/disbursements/",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "success": data.get("status", {}).get("success", False),
                "transaction_id": data.get("data", {}).get("transaction", {}).get("id"),
                "status": data.get("data", {}).get("transaction", {}).get("status", "pending"),
                "message": data.get("status", {}).get("message", "Disbursement initiated")
            }
    
    async def check_transaction_status(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {await self._get_access_token()}",
                "X-Country": "ZM",
                "X-Currency": "ZMW",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/standard/v1/payments/{transaction_id}",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def _get_access_token(self) -> str:
        """Get OAuth access token"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "client_id": self.api_username,
                "client_secret": self.api_key,
                "grant_type": "client_credentials"
            }
            
            response = await client.post(
                f"{self.api_endpoint}/auth/oauth2/token",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
