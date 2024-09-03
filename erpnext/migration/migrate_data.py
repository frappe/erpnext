import frappe
from sqlalchemy.orm import Session
from Goldfish.config import get_db
from Goldfish.models import doctype, item, accounts, stock, crm, manufacturing

def migrate_data():
    db: Session = next(get_db())

    try:
        # Migrate DocTypes
        migrate_doctypes(db)

        # Migrate Items
        migrate_items(db)

        # Migrate Accounts
        migrate_accounts(db)

        # Migrate Stock
        migrate_stock(db)

        # Migrate CRM
        migrate_crm(db)

        # Migrate Manufacturing
        migrate_manufacturing(db)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {str(e)}")
    finally:
        db.close()

def migrate_doctypes(db: Session):
    frappe_doctypes = db.query(doctype.DocType).all()
    for frappe_doctype in frappe_doctypes:
        db_doctype = doctype.DocType(
            name=frappe_doctype.name,
            module=frappe_doctype.module,
            is_submittable=frappe_doctype.is_submittable,
            is_tree=frappe_doctype.is_tree,
            is_single=frappe_doctype.is_single,
            custom=frappe_doctype.custom
        )
        db.add(db_doctype)
    db.flush()

def migrate_items(db: Session):
    frappe_items = db.query(item.Item).all()
    for frappe_item in frappe_items:
        db_item = item.Item(
            name=frappe_item.name,
            item_code=frappe_item.item_code,
            item_name=frappe_item.item_name,
            item_group=frappe_item.item_group,
            stock_uom=frappe_item.stock_uom,
            disabled=frappe_item.disabled,
            is_stock_item=frappe_item.is_stock_item,
            has_variants=frappe_item.has_variants,
            variant_of=frappe_item.variant_of,
            valuation_rate=frappe_item.valuation_rate,
            description=frappe_item.description
        )
        db.add(db_item)
    db.flush()

def migrate_accounts(db: Session):
    # Migrate Accounts
    frappe_accounts = db.query(accounts.Account).all()
    for frappe_account in frappe_accounts:
        db_account = accounts.Account(
            name=frappe_account.name,
            account_name=frappe_account.account_name,
            parent_account=frappe_account.parent_account,
            root_type=frappe_account.root_type,
            is_group=frappe_account.is_group,
            company=frappe_account.company
        )
        db.add(db_account)
    db.flush()

    # Migrate Journal Entries
    frappe_journal_entries = db.query(accounts.JournalEntry).all()
    for frappe_je in frappe_journal_entries:
        db_je = accounts.JournalEntry(
            name=frappe_je.name,
            posting_date=frappe_je.posting_date,
            company=frappe_je.company,
            total_debit=frappe_je.total_debit,
            total_credit=frappe_je.total_credit
        )
        db.add(db_je)

        # Migrate Journal Entry Accounts
        je_accounts = db.query(accounts.JournalEntryAccount).filter(accounts.JournalEntryAccount.parent == frappe_je.name).all()
        for je_account in je_accounts:
            db_je_account = accounts.JournalEntryAccount(
                name=je_account.name,
                parent=frappe_je.name,
                account=je_account.account,
                debit=je_account.debit,
                credit=je_account.credit
            )
            db.add(db_je_account)
    db.flush()

def migrate_stock(db: Session):
    # Migrate Stock Entries
    frappe_stock_entries = db.query(stock.StockEntry).all()
    for frappe_se in frappe_stock_entries:
        db_se = stock.StockEntry(
            name=frappe_se.name,
            posting_date=frappe_se.posting_date,
            company=frappe_se.company,
            purpose=frappe_se.purpose
        )
        db.add(db_se)

        # Migrate Stock Entry Detail
        se_items = db.query(stock.StockEntryDetail).filter(stock.StockEntryDetail.parent == frappe_se.name).all()
        for se_item in se_items:
            db_se_item = stock.StockEntryDetail(
                name=se_item.name,
                parent=frappe_se.name,
                item_code=se_item.item_code,
                qty=se_item.qty,
                basic_rate=se_item.basic_rate
            )
            db.add(db_se_item)

    db.flush()

    # Migrate Purchase Receipts
    frappe_prs = db.query(stock.PurchaseReceipt).all()
    for frappe_pr in frappe_prs:
        db_pr = stock.PurchaseReceipt(
            name=frappe_pr.name,
            supplier=frappe_pr.supplier,
            posting_date=frappe_pr.posting_date,
            company=frappe_pr.company
        )
        db.add(db_pr)

        # Migrate Purchase Receipt Items
        pr_items = db.query(stock.PurchaseReceiptItem).filter(stock.PurchaseReceiptItem.parent == frappe_pr.name).all()
        for pr_item in pr_items:
            db_pr_item = stock.PurchaseReceiptItem(
                name=pr_item.name,
                parent=frappe_pr.name,
                item_code=pr_item.item_code,
                qty=pr_item.qty,
                rate=pr_item.rate
            )
            db.add(db_pr_item)

    db.flush()

def migrate_crm(db: Session):
    # Implement CRM migration logic using SQLAlchemy queries
    pass

def migrate_manufacturing(db: Session):
    # Implement manufacturing migration logic using SQLAlchemy queries
    pass

if __name__ == "__main__":
    migrate_data()