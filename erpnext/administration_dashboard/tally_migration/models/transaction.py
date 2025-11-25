class Transaction:
    def __init__(self, account: str, debit_amount: float, credit_amount: float, account_debit_amount: float, account_credit_amount: float, currency: str = 'INR', exchange_rate: float = 1.0, party: str | None = None, party_type: str | None = None, remark: str | None = None, reference: str | None = None, item_name: str | None = None, item_tax_template: float | None = None):
        self.account = account
        self.debit_amount = debit_amount
        self.credit_amount = credit_amount
        self.account_debit_amount = account_debit_amount
        self.account_credit_amount = account_credit_amount
        self.currency = currency
        self.exchange_rate = exchange_rate
        self.party = party
        self.party_type = party_type
        self.remark = remark
        self.reference = reference
        self.item_name = item_name or ""
        self.item_tax_template = item_tax_template or 0.0
