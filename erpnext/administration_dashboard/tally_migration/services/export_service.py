import secrets
import string
from pathlib import Path
import zipfile
import pandas as pd

from erpnext.administration_dashboard.tally_migration.models.account import Account
from erpnext.administration_dashboard.tally_migration.models.entry import Entry
from erpnext.administration_dashboard.tally_migration.models.constants.entry_types import *
from erpnext.administration_dashboard.tally_migration.models.constants.import_types import *
from erpnext.administration_dashboard.tally_migration.models.constants.export_headers import headers, number_series
from erpnext.administration_dashboard.tally_migration.services.accounts_service import is_of_type

def get_csv_entries(entries: list[Entry], accounts: list[Account]):
  journal_entries = [headers[JOURNAL_ENTRY_IMPORT]]
  payment_entries = [headers[PAYMENT_ENTRY_IMPORT]]
  purchase_invoices = [headers[PURCHASE_INVOICE_IMPORT]]

  for entry in entries:
    if entry.import_type == JOURNAL_ENTRY_IMPORT:
      rows = prepare_journal_entries(entry)
      journal_entries.extend(rows)

    elif entry.import_type == PAYMENT_ENTRY_IMPORT:
      rows = prepare_payment_entries(entry)
      payment_entries.extend(rows)

    elif entry.import_type == PURCHASE_INVOICE_IMPORT:
      rows = prepare_purchase_invoices(entry, accounts)
      purchase_invoices.extend(rows)

  return journal_entries, payment_entries, purchase_invoices

def save_as_file(csv_entries: list[str], filename: str, output_folder = "output"):
  # Ensure output folder exists
  folder = Path(output_folder)
  folder.mkdir(parents=True, exist_ok=True)

  # Split filename into name and extension
  p = Path(filename)
  name = p.stem
  suffix = p.suffix

  # Generate a 6-character random alphanumeric code
  alphabet = string.ascii_lowercase + string.digits
  code = ''.join(secrets.choice(alphabet) for _ in range(6))

  out_name = f"{name}_{code}{suffix}.csv"
  out_path = folder / out_name

  # Write csv entries (each item is assumed to be a full CSV row string)
  # Join with newline to create a valid CSV file
  with out_path.open("w", encoding="utf-8", newline="") as fh:
    for _, line in enumerate(csv_entries):
      fh.write(str(line))
      # write newline except possibly after last line (keep conventional newline)
      fh.write("\n")

  return str(out_path)

def archive_files(filepaths: list[str], filename_suffix: str, output_folder = "output"):
  # Ensure output folder exists
  folder = Path(output_folder)
  folder.mkdir(parents=True, exist_ok=True)

  # Base name for the archive
  out_filename = f"erpnext_import_{filename_suffix}"

  # Generate a 6-character random alphanumeric code
  alphabet = string.ascii_lowercase + string.digits
  code = ''.join(secrets.choice(alphabet) for _ in range(6))

  out_name = f"{out_filename}_{code}.zip"
  out_path = folder / out_name

  # Create zip file and add provided filepaths. Skip non-existent files.
  with zipfile.ZipFile(out_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
    for fp in filepaths:
      p = Path(fp)
      if not p.exists():
        # skip missing files
        continue
      # store only the filename inside the archive
      zf.write(p, arcname=p.name)

  return str(out_path)

def prepare_journal_entries(entry: Entry):
  rows: list[str] = []
  row_entries = [""]
  row_entries.append(number_series[JOURNAL_ENTRY_IMPORT])
  row_entries.append(entry.voucher_type or "")
  row_entries.append(entry.company)
  if isinstance(entry.date, str):
    entry_date = pd.to_datetime(entry.date, errors='coerce')  # converts invalid to NaT
  else:
    entry_date = pd.to_datetime(entry.date, errors='coerce') if entry.date is not None else None

  if pd.isna(entry_date):
    entry_date = None

  # Posting Date
  row_entries.append(entry_date.strftime('%Y-%m-%d') if entry_date else "")

  # row_entries.append(entry.date.strftime('%Y-%m-%d'))
  row_entries.append(entry.voucher_number)

  # Reference Date
  row_entries.append(entry_date.strftime('%Y-%m-%d') if entry_date else "")

  if entry.remark and '"' in entry.remark:
    entry.remark = entry.remark.replace('"', "'")

  row_entries.append(entry.remark or "")
  row_entries.append(str(1 if entry.is_multi_currency else 0))

  prefix_entries = 9
  for transaction in entry.transactions:
    if transaction.account != entry.transactions[0].account:
      for _ in range(prefix_entries):
        row_entries.append("")

    account_name = f'{transaction.account} - {entry.company_abbreviation}'.replace('"', "'")
    row_entries.append(account_name)
    row_entries.append(transaction.currency)
    row_entries.append(str(transaction.account_credit_amount))
    row_entries.append(str(transaction.account_debit_amount))
    row_entries.append(str(transaction.exchange_rate))
    row_entries.append(str(transaction.credit_amount))
    row_entries.append(str(transaction.debit_amount))
    row_entries.append(transaction.party if transaction.party else "")
    row_entries.append(transaction.party_type if transaction.party_type else "")
    # if transaction.reference and '"' in transaction.reference:
    #   transaction.reference = transaction.reference.replace('"', "'")

    # if transaction.remark and '"' in transaction.remark:
    #   transaction.remark = transaction.remark.replace('"', "'")

    # row_entries.append(transaction.reference or '')
    # row_entries.append(transaction.remark or '')

    row = ",".join(list(map(lambda x: f'"{x}"', row_entries)))
    rows.append(row)
    row_entries = []

  return rows

def prepare_payment_entries(entry: Entry):
  rows: list[str] = []
  row_entries = [""]
  credit_account = entry.get_credit_account()
  debit_account = entry.get_debit_account()
  row_entries.append(number_series[PAYMENT_ENTRY_IMPORT])
  row_entries.append(entry.voucher_type or "")
  row_entries.append(entry.company)
  # Posting date
  row_entries.append(entry.date.strftime('%Y-%m-%d'))
  # Reference number
  row_entries.append(entry.voucher_number)
  # Refernce date
  row_entries.append(entry.date.strftime('%Y-%m-%d'))
  row_entries.append(f"{credit_account.account} - {entry.company_abbreviation}")
  row_entries.append(credit_account.currency)
  row_entries.append(f"{debit_account.account} - {entry.company_abbreviation}")
  row_entries.append(debit_account.currency)
  row_entries.append(str(credit_account.credit_amount))
  row_entries.append(str(credit_account.exchange_rate))
  row_entries.append(str(debit_account.debit_amount))
  row_entries.append(str(debit_account.exchange_rate))

  if entry.voucher_type == PAYMENT:
    row_entries.append(debit_account.party or debit_account.account) # TODO: Use the supplier mapping if required.
    row_entries.append(debit_account.party_type or "Supplier")

  else:
    row_entries.append(credit_account.party or credit_account.account)
    row_entries.append(credit_account.party_type or "Customer")

  row = ",".join(list(map(lambda x: f'"{x}"', row_entries)))
  rows.append(row)

  return rows

def prepare_purchase_invoices(entry: Entry, accounts: list[Account]):
  rows: list[str] = []
  row_entries = [""]
  row_entries.append(number_series[PURCHASE_INVOICE_IMPORT])
  row_entries.append(entry.voucher_number)
  
  supplier = next((t.account for t in entry.transactions if t.credit_amount), "")
  row_entries.append(supplier)
  if isinstance(entry.date, str):
    entry_date = pd.to_datetime(entry.date, errors='coerce')  # converts invalid to NaT
  else:
    entry_date = pd.to_datetime(entry.date, errors='coerce') if entry.date is not None else None

  if pd.isna(entry_date):
    entry_date = None

  row_entries.append(entry_date.strftime('%Y-%m-%d') if entry_date else "")

  credit_account = next((t.account for t in entry.transactions if t.credit_amount), "")
  credit_account = f"{credit_account} - {entry.company_abbreviation}"
  row_entries.append(credit_account)

  has_igst = any(isinstance(t.account, str) and any(keyword in t.account.lower() for keyword in ["igst", "i-gst"])
    for t in entry.transactions)
  if has_igst:
      tax_template_name = f"Input GST Out-State - {entry.company_abbreviation}"
  else:
      tax_template_name = f"Input GST In-State - {entry.company_abbreviation}"

  row_entries.append(tax_template_name)
  row_entries.append(entry.company)
  
  for txn in entry.transactions:
    if txn.debit_amount is None or txn.debit_amount <= 0:
        continue
    if not (isinstance(txn.account, str) and is_of_type(txn.account, "Purchase Account", accounts)):
        continue

    item_row = row_entries.copy()
    item_row.append("")  # Id (Items)
    item_row.append("1") # Accepted Qty
    amount = txn.debit_amount or 0.0
    item_row.append(str(amount) if amount else "0")
    
    item_row.append(txn.item_name)  # "Item Name (Items)"
    item_row.append(str(amount) if amount else "0") # Rate (Items)
    item_row.append("Nos")  # "UOM (Items)"
    item_row.append("1") # "UOM Conversion Factor (Items)"
    
    item_row.append(txn.account)  # "Expense Head (Items)"
    item_row.append(txn.item_tax_template) 
    item_row.append("NET-90")

    row = ",".join(f'"{x}"' for x in item_row)
    rows.append(row)

  return rows
