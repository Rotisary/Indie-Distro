from loguru import logger

from .base import BaseService
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
            raise ValueError({
                "status_code": response.status_code,
                "error_message": response.text
            })
        
        logger.info(f"Subaccount created successfully")
        data = {
            "account_reference": response.json()['data']['account_reference'],
            "barter_id": response.json()['data']['barter_id'],
            "created_at": response.json()['data']['created_at']
        }
        return data
    

    def delete_subaccount(self, account_reference: str):
        endpoint = f"payout-subaccounts/{account_reference}"
        data = {}
        response = self.post(endpoint, data)
        if response.status_code != 200:
            logger.error(f"Failed to delete subaccount: {response.text}")
            raise ValueError({
                "status_code": response.status_code,
                "error_message": response.text
            })
        
        logger.info(f"Subaccount deleted successfully")
        status = response.json()['status']
        return status