# import requests
# import os


# def create_flw_subaccount(sub_account, wallet_instance, name, email, phone_number):
#     body = {
#         "account_name": name,
#         "email": email,
#         "mobilenumber": phone_number,
#         "country": "NG" 
#     }

#     headers = {
#         "Authorization": f"Bearer {os.getenv('FLW_SECRET_KEY')}"
#     }
#     url = 'https://api.flutterwave.com/v3/payout-subaccounts'

#     SA_response = requests.post(url, headers=headers, json=body)

#     if SA_response.status_code != 200:
#         error = {
#             "status_code": SA_response.status_code,
#             "error_message": SA_response.text
#         }
#         raise ValueError(error)
#     else:
#         subaccount = sub_account.objects.create(
#             wallet = wallet_instance,
#             account_reference = SA_response.json()['data']['account_reference'],
#             barter_id = SA_response.json()['data']['barter_id'],
#             virtual_account_number = SA_response.json()['data']['nuban'],
#             virtual_bank_name = SA_response.json()['data']['bank_name'],
#             created_at = SA_response.json()['data']['created_at']
#         )

#         return subaccount