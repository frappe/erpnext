from erpnext.administration_dashboard.tally_migration.models.entry import Entry
from erpnext.administration_dashboard.tally_migration.models.account import Account
from erpnext.administration_dashboard.tally_migration.models.constants.entry_types import *
from erpnext.administration_dashboard.tally_migration.models.constants.import_types import *
from erpnext.administration_dashboard.tally_migration.services.accounts_service import is_sundry_debtor, is_sundry_creditor, is_bank_account, is_of_type

def get_voucher_type(entry: Entry, accounts: list[Account]) -> tuple[str, str]:
  account_names = [t.account for t in entry.transactions if isinstance(t.account, str) and t.account.strip()]
  if any(isinstance(a, str) and "Unit" in a and "MGPL" in a for a in account_names):
      return INTER_COMPANY, JOURNAL_ENTRY_IMPORT

  credit_transactions = list(filter(lambda x: x.credit_amount, entry.transactions))
  debit_transactions = list(filter(lambda x: x.debit_amount, entry.transactions))

  if is_sundry_creditor(accounts, credit_transactions):
    if any(isinstance(t.account, str) and is_of_type(t.account, "Purchase Account", accounts) for t in debit_transactions):
      return PURCHASE_INVOICE, PURCHASE_INVOICE_IMPORT

  if is_sundry_debtor(accounts, credit_transactions):
      # if the debit account is a bank
      if is_bank_account(accounts, debit_transactions):
        return RECEIPT, PAYMENT_ENTRY_IMPORT

      if any("GST" in t.account and t.debit_amount for t in entry.transactions): #TODO : Look up later
        return CREDIT_NOTE, JOURNAL_ENTRY_IMPORT
  
  if is_sundry_creditor(accounts, debit_transactions):
      if is_bank_account(accounts, credit_transactions):
        return PAYMENT, PAYMENT_ENTRY_IMPORT

      if any(isinstance(t.account, str) and is_of_type(t.account, "Purchase Account", accounts) for t in credit_transactions):
        return DEBIT_NOTE, JOURNAL_ENTRY_IMPORT
  
  if is_bank_account(accounts, entry.transactions, check_all=True) or (is_bank_account(accounts, entry.transactions) and any("cash" in t.account.lower() for t in entry.transactions)):
    return CONTRA, JOURNAL_ENTRY_IMPORT

  if any(isinstance(t.account, str) and "cash" in t.account.lower() for t in entry.transactions):
    return CASH, JOURNAL_ENTRY_IMPORT

  return JOURNAL, JOURNAL_ENTRY_IMPORT