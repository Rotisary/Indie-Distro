# from rave_python import Rave, RaveExceptions, rave_transfer
# import requests
# import os

# from core.users.models import Bank


# rave = Rave(os.getenv('FLW_PUBLIC_KEY'), os.getenv('FLW_SECRET_KEY'), usingEnv=False)


# def validate_recipient_account(account_number, account_bank):
#     url =  'https://api.flutterwave.com/v3/accounts/resolve'
#     headers = {
#         "Authorization": f"Bearer {os.getenv('FLW_SECRET_KEY')}",
#         "Content-Type": "application/json"
#     }
#     body = {
#         "account_number": account_number,
#         "account_bank": account_bank
#     }
#     response = requests.post(url, headers=headers, json=body)
#     return response.json()


# def transfer_funds(bank, account_number, amount, narration, reference, recipient_name, debit_account):
#     body = {
#         "account_bank": bank,
#         "account_number": account_number,
#         "amount": amount,
#         "narration": narration,
#         "currency": "NGN",
#         "reference": reference,
#         "callback_url": "https://www.flutterwave.com/ng/",
#         "debit_currency": "NGN",
#         "beneficiary_name": recipient_name,
#         "debit_subaccount": debit_account
#     }

#     try:
#         payment = rave.Transfer.initiate(body)
#         return payment['data']['status'], payment
#     except RaveExceptions.IncompletePaymentDetailsError as e:
#         return {'error': str(e)}, {} # set the second response object to an empty dictionary to prevent unpacking error when exceptions are raised 
#     except RaveExceptions.InitiateTransferError as e:
#         return {'error': str(e)}, {}
#     except RaveExceptions.ServerError as e:
#         return {'error': str(e)}, {}