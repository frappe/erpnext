from typing import Optional
from .base_bank_integration import BaseBankIntegration
from .zanaco_integration import ZanacoIntegration
from .absa_integration import ABSAIntegration
from .stanbic_integration import StanbicIntegration
from .fnb_integration import FNBIntegration
from .atlas_mara_integration import AtlasMaraIntegration

class BankIntegrationFactory:
    """
    Factory class to create appropriate bank integration instances
    based on bank code
    """
    
    BANK_INTEGRATIONS = {
        "zanaco": ZanacoIntegration,
        "absa": ABSAIntegration,
        "stanbic": StanbicIntegration,
        "fnb": FNBIntegration,
        "atlas_mara": AtlasMaraIntegration,
    }
    
    @classmethod
    def create(
        cls,
        bank_code: str,
        api_username: str,
        api_key: str,
        api_endpoint: str,
        **kwargs
    ) -> Optional[BaseBankIntegration]:
        """
        Create and return a bank integration instance
        
        Args:
            bank_code: Code identifying the bank (zanaco, absa, stanbic, fnb, atlas_mara)
            api_username: API username/client ID
            api_key: API key/secret
            api_endpoint: Base API endpoint URL
            **kwargs: Additional configuration parameters
        
        Returns:
            BaseBankIntegration instance or None if bank code is invalid
        """
        integration_class = cls.BANK_INTEGRATIONS.get(bank_code.lower())
        
        if not integration_class:
            raise ValueError(f"Unsupported bank code: {bank_code}")
        
        return integration_class(
            api_username=api_username,
            api_key=api_key,
            api_endpoint=api_endpoint,
            **kwargs
        )
    
    @classmethod
    def get_supported_banks(cls) -> dict:
        """
        Get list of all supported bank codes and their display names
        
        Returns:
            Dictionary mapping bank codes to bank names
        """
        banks = {}
        for code, integration_class in cls.BANK_INTEGRATIONS.items():
            # Instantiate temporarily to get bank name
            temp_instance = integration_class("", "", "")
            banks[code] = temp_instance.get_bank_name()
        
        return banks
