import pandas as pd
import re
from datetime import datetime
from erpnext.administration_dashboard.tally_migration.models.item import Item
from erpnext.administration_dashboard.tally_migration.models.extract import Extract
from erpnext.administration_dashboard.tally_migration.models.entry import Entry
from erpnext.administration_dashboard.tally_migration.models.account import Account
from erpnext.administration_dashboard.tally_migration.models.transaction import Transaction
from erpnext.administration_dashboard.tally_migration.models.party import Party
from erpnext.administration_dashboard.tally_migration.services.voucher_service import get_voucher_type

def safe_float(val):
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, str):
        val = val.replace("Dr", "").replace("Cr", "").strip()
        if not val:
            return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0
    return float(val)

def get_entries(source_sheet_path: str, accounts: list[Account], accounts_dict: dict[str, str], parties: list[Party], items_list: list[Item], items_dict: dict[str, str], company_name: str, company_abbreviation: str):
  if accounts is None:
      accounts = [] 

  # Read the contents of the Excel file (no header - positional indices used)
  df = pd.read_excel(source_sheet_path)

  # Declare the current_row number as the first row of the Excel
  current_row = 1
  col_len = 0

  if "Particulars" not in df.columns:
    while current_row < len(df) - 1 and df.iloc[current_row, 1] != "Particulars":
      current_row += 1

    for cell in df.iloc[current_row]:
      if "Credit" == cell:
        break

      col_len += 1

    current_row += 2

  else:
    for col in df.columns:
      if "Credit" == col:
        break
      col_len += 1

  credit_col = col_len
  debit_col = col_len - 1

  # Declare an empty array of objects for the Entries
  extract = Extract(
    source_filename=source_sheet_path.split('/')[-1].split('.')[0]
  )

  # Iterate through the entries in the Excel file until current row > length of entries
  while current_row < len(df) - 1:
      # Take the rows in the file from the current_row to the row before the one that 
      # contains a value in the fifth column, or the end of the list of rows
      next_entry_start = current_row + 1
      while (next_entry_start < len(df) - 1 and 
            pd.isna(df.iloc[next_entry_start, col_len - 3])):  # Check the third column from the last 
          next_entry_start += 1
      
      rows = df.iloc[current_row:next_entry_start]

      is_multi_currency_entry = False 

      # Safely get voucher number
      raw_voucher = rows.iat[0, col_len - 2]
      if pd.isna(raw_voucher):
          voucher_number = ""
      else:
          try:
              voucher_number = str(int(float(str(raw_voucher).replace("Cr", "").replace("Dr", "").strip())))
          except ValueError:
              voucher_number = str(raw_voucher)
      entry = Entry(
          date=rows.iat[0, 0],  # First column # type: ignore
          voucher_type=None,  # Default to None
          voucher_number=voucher_number,  # Sixth column # type: ignore
          company=company_name,
          company_abbreviation=company_abbreviation,
      )

      for idx, row in enumerate(rows.itertuples(index=False)):
          account_name = str(row[1]).strip() if not pd.isna(row[1]) else ""

          txn_ref: str | None = None
          txn_rem: str | None = None

          debit_amount = safe_float(getattr(row, f"_{debit_col}", 0))
          credit_amount = safe_float(getattr(row, f"_{credit_col}", 0))  

          if len(row) > 2 and row[2] == "@":
            continue

          if pd.isna(row[debit_col]) and pd.isna(row[credit_col]):
            if not pd.isna(row[1]) and pd.isna(row[2]):
              entry.remark = row[1]
            continue

          if debit_amount == 0 and credit_amount == 0 and idx == len(rows) - 1:
            narration_text = str(getattr(row, "Particulars", "")).strip()
            if narration_text:
              entry.remark = narration_text
            continue

          account_debit_amount = debit_amount 
          account_credit_amount = credit_amount 

          item_name = None
          item_tax_template = None

          if debit_amount == 0 and credit_amount == 0 and account_name!="New Ref":
            matched_item = next(
              (item for item in items_list if item.item_name.strip().lower() == account_name.lower()), 
              None
            )

            if matched_item:
              lookahead = idx + 1
              while lookahead < len(rows):
                  next_row = rows.iloc[lookahead]
                  next_debit = safe_float(next_row.iloc[debit_col])
                  next_credit = safe_float(next_row.iloc[credit_col])
                  if next_debit > 0 or next_credit > 0:
                      account_for_txn = str(next_row[1]).strip() if not pd.isna(next_row[1]) else ""
                      txn_ref = None
                      txn_rem = None
                      transaction = Transaction(
                          account=account_for_txn,
                          debit_amount=next_debit,
                          credit_amount=next_credit,
                          account_debit_amount=account_debit_amount,
                          account_credit_amount=account_credit_amount,
                          exchange_rate=1.0,
                          currency='INR',
                          reference=None,
                          remark=None,
                          item_name=matched_item.item_name,
                          item_tax_template=matched_item.item_tax_template # type: ignore
                      )
                      entry.add_transaction(transaction)
                      break
                  lookahead += 1
            else:
                if account_name not in extract.invalid_items and account_name != "New Ref":
                    extract.invalid_items.append(account_name)
            continue

          is_multi_currency_transaction = (idx + 1) < len(rows) and rows.iat[idx + 1, 2] == '@'
          is_multi_currency_entry = is_multi_currency_entry or is_multi_currency_transaction

          # Attempt to find the party using the actual name before updating the name using the account dictionary.
          # party = list(filter(lambda x: x.name.lower() == account_name.lower(), parties))
          party = list(filter(lambda x: x.name and account_name and x.name.lower() == account_name.lower(), parties))

          if not any(a.name.strip() == account_name for a in accounts) \
              and account_name not in accounts_dict.keys() \
              and account_name not in extract.invalid_accounts:
              extract.invalid_accounts.append(account_name)

          elif account_name in accounts_dict:
             account_name = accounts_dict[account_name]

          if is_multi_currency_transaction and debit_amount:
              account_debit_amount = safe_float(rows.iat[idx + 1, 1])

          if is_multi_currency_transaction and credit_amount:
              account_credit_amount = safe_float(rows.iat[idx + 1, 1])

          # If the required party is not found using the initial name, check using the fixed name
          # party = party or list(filter(lambda x: x.name.lower() == account_name.lower(), parties))
          party = party or list(filter(
              lambda x: x.name and account_name and x.name.lower() == account_name.lower(),
              parties
          ))

          transaction = Transaction(
              account=account_name,
              debit_amount=debit_amount,  # type: ignore
              credit_amount=credit_amount,  # type: ignore
              account_debit_amount=account_debit_amount,
              account_credit_amount=account_credit_amount,
              exchange_rate=float(rows.iat[idx + 1, 3]) if is_multi_currency_transaction else 1.0,  # type: ignore
              currency='USD' if is_multi_currency_transaction else 'INR',
              party=party[0].name if len(party) else None,
              party_type=party[0].type if len(party) else None,
              reference=txn_ref,
              remark=txn_rem,
              item_name=item_name,
              item_tax_template=item_tax_template
          )

          entry.add_transaction(transaction)
    
      entry.is_multi_currency = is_multi_currency_entry
      entry.voucher_type, entry.import_type = get_voucher_type(entry, accounts)
      extract.entries.append(entry)
      
      # Set current_row to next_entry_start
      current_row = next_entry_start

  return extract
