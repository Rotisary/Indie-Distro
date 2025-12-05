from loguru import logger

from .base import BaseService
from core.utils.exceptions import exceptions
from core.utils.exceptions.handlers import Handlers
from config import env
from core.users.models import User


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
        Handlers.handle_request_failure(
            response, f"Failed to create subaccount: {response.text}"
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
        Handlers.handle_request_failure(
            response, f"Failed to delete subaccount: {response.text}"
        )
        
        logger.info(f"Subaccount deleted successfully")
        status = response.json()['status']
        return status
    

    def fetch_static_virtual_account(self, account_reference: str, wallet):
        endpoint = f"payout-subaccounts/{account_reference}/static-account"
        response = self.get(endpoint) 
        Handlers.handle_request_failure(
            response, f"Failed to fetch static virtual account: {response.text}"
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


    def charge_nigerian_bank(self, user: User, amount, tx_reference: str):
        endpoint = "charges?type=mono"
        data = {
            "amount": amount,
            "email": user.email,
            "tx_ref": tx_reference,
            "currency": "NGN",
            "fullname": f"{user.first_name} {user.last_name}",
            "phone_number": user.phone_number
        }
        response = self.post(endpoint, data=data)
        Handlers.handle_request_failure(
            response, f"Failed to get auth url: {response.text}"
        )
        
        if response.json()["data"]["fraud_status"] != "ok":
            logger.error(f"Failed to complete bank charge. Fraud detected")
            raise exceptions.ClientPaymentException(
                message=f"Fraud detected. Failed to complete bank charge",
                errors="Fraud Detected"
            )
        
        logger.info(f"auth url fetch successful. Nigerian account charge in progress")
        data = {
            "flw_ref": response.json()["data"]["flw_ref"],
            "auth_model": response.json()["data"]["auth_model"],
            "meta": response.json()["data"]["meta"]
        }
        return data


    def make_transfer(
            self, 
            beneficiary: dict, 
            amount, 
            tx_reference: str,
            description: str,
            debit_subaccount: str=None
        ):
        endpoint = "transfers"
        data = {
            "account_bank": beneficiary.get("bank",  "flutterwave"),
            "account_number": beneficiary["account_number"],
            "amount": amount,
            "debit_subaccount": debit_subaccount,
            "beneficiary_name": f"{beneficiary.get("name", None)}",
            "currency": "NGN",
            "debit_currency": "NGN",
            "reference": tx_reference,
            "narration": description
        }
        response = self.post(endpoint, data=data)
        Handlers.handle_request_failure(
            response, f"Transfer Failed: {response.text}"
        )
        
        logger.info(f"Transfer successfully initiated")
        data = {
            "status": response.json()["status"],
            "requires_approval": response.json()["data"]["requires_approval"],
            "is_approved": response.json()["data"]["is_approved"]
        }
        return data
    