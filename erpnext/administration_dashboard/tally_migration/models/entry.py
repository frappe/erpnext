from datetime import datetime
from typing import List
from .transaction import Transaction

class Entry:
    def __init__(self, date: datetime, voucher_type: str | None, voucher_number: str, company: str, company_abbreviation: str, remark: str | None = None, is_multi_currency: bool = False, import_type: str | None = None):
        self.date = date
        self.voucher_type = voucher_type
        self.voucher_number = voucher_number
        self.company = company
        self.company_abbreviation = company_abbreviation
        self.remark = remark
        self.is_multi_currency = is_multi_currency
        self.import_type = import_type
        self.transactions: List[Transaction] = []

    def add_transaction(self, transaction: Transaction):
        self.transactions.append(transaction)

    def get_credit_account(self):
        return list(filter(lambda x: x.credit_amount, self.transactions))[0]
    
    def get_debit_account(self):
        return list(filter(lambda x: x.debit_amount, self.transactions))[0]
