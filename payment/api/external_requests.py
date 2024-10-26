from rave_python import Rave, RaveExceptions
import requests
import os

from users.models import Bank


rave = Rave(os.getenv('FLW_PUBLIC_KEY'), os.getenv('FLW_SECRET_KEY'), usingEnv=False)

# def external_fund_transfer(bank, account_number, amount, narration, reference, debit_account):
    # body = {
    #   "account_bank": bank,
    #   "account_number": account_number,
    #   "amount": amount,
    #   "narration": narration,
    #   "currency": "NGN",
    #   "reference": reference,
    #   "callback_url": "https://www.flutterwave.com/ng/",
    #   "debit_currency": "NGN",
    #   "debit_subaccount": debit_account
    # }

    # try:
    #   payment = rave.Transfer.initiate(body)
    # except RaveExceptions.IncompletePaymentDetailsError as e:
    #   error = {
    #       'message': e.err['errMsg'],
    #       'transaction id': e.
    #   }


# body = {
#   "account_bank": "044",
#   "account_number": '0690000031',
#   "amount": 500,
#   "narration": 'test payment',
#   "currency": "NGN",
#   "reference": '8877BST12SDDY',
#   "callback_url": "https://www.flutterwave.com/ng/",
#   "debit_currency": "NGN",
#   "debit_subaccount": 'PSA5E40702CB02158691'
# }

# try:
#   payment = rave.Transfer.initiate(body)
#   print(payment)
# except RaveExceptions.IncompletePaymentDetailsError as e:
#   error = {
#       'message': e.err['errMsg'],
#       'transaction id': e.err['flwRef']
#   }
#   print(error)

try:
  res2 = rave.Transfer.fetch("8877BST12SDDY")
  print(res2)
except RaveExceptions.TransferFetchError as e:
    print(e.err["errMsg"])
    print(e.err["flwRef"])
