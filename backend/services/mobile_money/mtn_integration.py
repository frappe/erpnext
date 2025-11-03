import httpx
from typing import List, Dict, Any
from datetime import datetime
from .base_mobile_money import (
    BaseMobileMoneyIntegration,
    MobileMoneyTransactionModel,
    MobileMoneyBalance,
    MobileMoneyConnectionStatus
)

class MTNMoneyIntegration(BaseMobileMoneyIntegration):
    """
    Integration service for MTN Mobile Money Zambia
    API Documentation: https://momodeveloper.mtn.com
    """
    
    def get_provider_code(self) -> str:
        return "mtn"
    
    def get_provider_name(self) -> str:
        return "MTN Mobile Money"
    
    async def test_connection(self) -> MobileMoneyConnectionStatus:
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "X-Reference-Id": self.merchant_code,
                    "X-Target-Environment": "production",
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # Get API user details to test connection
                response = await client.get(
                    f"{self.api_endpoint}/v1_0/apiuser",
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
                "X-Reference-Id": self.merchant_code,
                "X-Target-Environment": "production",
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Authorization": f"Bearer {await self._get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/collection/v1_0/account/balance",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            return MobileMoneyBalance(
                provider_name=self.provider_name,
                phone_number=self.phone_number,
                available_balance=float(data.get("availableBalance", 0)),
                currency=data.get("currency", "ZMW"),
                as_of_date=datetime.utcnow()
            )
    
    async def fetch_transactions(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> List[MobileMoneyTransactionModel]:
        # MTN MoMo API doesn't have native transaction history endpoint
        # Transactions are typically pushed via webhooks
        # This is a placeholder for demonstration
        return []
    
    async def initiate_collection(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Request to pay (customer pays merchant)"""
        import uuid
        
        async with httpx.AsyncClient() as client:
            headers = {
                "X-Reference-Id": str(uuid.uuid4()),
                "X-Target-Environment": "production",
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Authorization": f"Bearer {await self._get_access_token()}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": str(amount),
                "currency": "ZMW",
                "externalId": reference,
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": description,
                "payeeNote": description
            }
            
            response = await client.post(
                f"{self.api_endpoint}/collection/v1_0/requesttopay",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            return {
                "success": response.status_code == 202,
                "transaction_id": headers["X-Reference-Id"],
                "status": "pending",
                "message": "Collection request initiated"
            }
    
    async def initiate_disbursement(
        self,
        phone_number: str,
        amount: float,
        reference: str,
        description: str
    ) -> Dict[str, Any]:
        """Transfer money to customer"""
        import uuid
        
        async with httpx.AsyncClient() as client:
            headers = {
                "X-Reference-Id": str(uuid.uuid4()),
                "X-Target-Environment": "production",
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Authorization": f"Bearer {await self._get_access_token()}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "amount": str(amount),
                "currency": "ZMW",
                "externalId": reference,
                "payee": {
                    "partyIdType": "MSISDN",
                    "partyId": phone_number
                },
                "payerMessage": description,
                "payeeNote": description
            }
            
            response = await client.post(
                f"{self.api_endpoint}/disbursement/v1_0/transfer",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            return {
                "success": response.status_code == 202,
                "transaction_id": headers["X-Reference-Id"],
                "status": "pending",
                "message": "Disbursement initiated"
            }
    
    async def check_transaction_status(
        self,
        transaction_id: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {
                "X-Target-Environment": "production",
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Authorization": f"Bearer {await self._get_access_token()}",
                "Content-Type": "application/json"
            }
            
            response = await client.get(
                f"{self.api_endpoint}/collection/v1_0/requesttopay/{transaction_id}",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
    
    async def _get_access_token(self) -> str:
        """Get OAuth access token for API calls"""
        # Simplified - in production, cache token and refresh when expired
        async with httpx.AsyncClient() as client:
            headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Authorization": f"Basic {self._create_basic_auth()}"
            }
            
            response = await client.post(
                f"{self.api_endpoint}/collection/token/",
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            data = response.json()
            return data.get("access_token")
    
    def _create_basic_auth(self) -> str:
        """Create Basic Auth header"""
        import base64
        credentials = f"{self.api_username}:{self.api_secret}"
        return base64.b64encode(credentials.encode()).decode()
