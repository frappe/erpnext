from sqlalchemy.orm import Session
from Goldfish.models.accounts import Account, JournalEntry, JournalEntryAccount
from typing import List
from Goldfish.utils.exceptions import ValidationError, NotFoundError

def validate_account(db: Session, account: Account):
    if not account.account_name:
        raise ValidationError("Account name is required")
    
    if account.is_group and account.parent_account:
        parent = db.query(Account).filter(Account.name == account.parent_account).first()
        if not parent or not parent.is_group:
            raise ValidationError("Parent account must be a group account")

def create_journal_entry(db: Session, posting_date: datetime, company: str, accounts: List[JournalEntryAccount]) -> JournalEntry:
    if not accounts:
        raise ValidationError("Journal Entry must have at least one account entry")

    total_debit = sum(account.debit for account in accounts)
    total_credit = sum(account.credit for account in accounts)

    if total_debit != total_credit:
        raise ValidationError("Total debit must equal total credit")

    journal_entry = JournalEntry(
        posting_date=posting_date,
        company=company,
        total_debit=total_debit,
        total_credit=total_credit
    )
    db.add(journal_entry)
    db.flush()

    for account in accounts:
        db_account = JournalEntryAccount(
            parent=journal_entry.name,
            account=account.account,
            debit=account.debit,
            credit=account.credit
        )
        db.add(db_account)

    db.commit()
    return journal_entry

def get_account_balance(db: Session, account_name: str) -> float:
    account = db.query(Account).filter(Account.name == account_name).first()
    if not account:
        raise NotFoundError(f"Account {account_name} not found")
    
    debit_sum = db.query(JournalEntryAccount).filter(
        JournalEntryAccount.account == account_name
    ).with_entities(func.sum(JournalEntryAccount.debit)).scalar() or 0

    credit_sum = db.query(JournalEntryAccount).filter(
        JournalEntryAccount.account == account_name
    ).with_entities(func.sum(JournalEntryAccount.credit)).scalar() or 0

    return debit_sum - credit_sum