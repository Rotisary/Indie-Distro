from rest_framework.permissions import BasePermission


class WalletHasPin(BasePermission):
    message = 'your wallet is not ready yet, please set a pin'


    def has_permission(self, request, view):
        return request.user.wallet.wallet_pin
    

class WalletBalanceNotZero(BasePermission):
    message = 'insufficient funds, please fund your account'


    def has_permission(self, request, view):
        return not request.user.wallet.balance == 0
    

class TransactionDetailPerm(BasePermission):

    def has_object_permission(self, request, view, obj):
        return request.user == obj.sender or request.user.wallet == obj.recipient