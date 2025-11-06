from loguru import logger

from .base import BaseService
from core.utils.exceptions import exceptions
from config import env


class FlutterwaveService(BaseService):
    """
    A service class to interact with the Flutterwave API.
    """
    def __init__(self):
        super().__init__(
            base_url="https://api.flutterwave.com/v3",
            api_key=env.str("FLW_SECRET_KEY"),
        )


    def create_subaccount(self, account_name: str, email: str, mobile_number: str, country: str="NG"):
        endpoint = "payout-subaccounts"
        data = {
            "account_name": account_name,
            "email": email,
            "mobilenumber": mobile_number,
            "country": country
        }
        response = self.post(endpoint, data)
        if response.status_code != 200:
            logger.error(f"Failed to create subaccount: {response.text}")
            raise exceptions.CustomException(
                message=response.text,
                status_code=response.status_code
            )
        
        logger.info(f"Subaccount created successfully")
        data = {
            "account_reference": response.json()['data']['account_reference'],
            "barter_id": response.json()['data']['barter_id'],
            "created_at": response.json()['data']['created_at']
        }
        return data
    

    def delete_subaccount(self, account_reference: str):
        endpoint = f"payout-subaccounts/{account_reference}"
        response = self.delete(endpoint)
        if response.status_code != 200:
            logger.error(f"Failed to delete subaccount: {response.text}")
            raise exceptions.CustomException(
                message=response.text,
                status_code=response.status_code
            )
        
        logger.info(f"Subaccount deleted successfully")
        status = response.json()['status']
        return status
    

    def fetch_static_virtual_account(self, account_reference: str, wallet):
        endpoint = f"payout-subaccounts/{account_reference}/static-account"
        response = self.get(endpoint)
        if response.status_code != 200:
            logger.error(f"Failed to fetch static virtual account: {response.text}")
            raise exceptions.CustomException(
                message=response.text,
                status_code=response.status_code
            )
        
        logger.info(f"virtual account fetched successfully")
        wallet.virtual_account_number = response.json()['data']['static_account']
        wallet.virtual_bank_name = response.json()['data']['bank_name']
        wallet.virtual_bank_code = response.json()['data']['bank_code']
        wallet.save(update_fields=[
            'virtual_account_number', 
            'virtual_bank_name',
            'virtual_bank_code'
        ])
        return wallet