import csv
from pathlib import Path
from erpnext.administration_dashboard.tally_migration.models.transaction import Transaction
from erpnext.administration_dashboard.tally_migration.models.item import Item
from erpnext.administration_dashboard.tally_migration.models.account import Account
from erpnext.administration_dashboard.tally_migration.models.party import Party

def load_accounts_from_csv(path: str | Path) -> list[Account]:
    """Load accounts from a CSV file and return a list of Account objects.

    The CSV is expected to have headers matching the Chart_Of_Accounts.csv file.
    """
    path = Path(path)
    accounts: list[Account] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            accounts.append(Account.from_dict(row))
    return accounts

def load_accounts_dict_from_csv(path: str | Path) -> dict[str, str]:
    path = Path(path)
    accounts_dict: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
      reader = csv.DictReader(fh)
      for row in reader:
        acct_not_found = row['ACCT_NOT_FOUND']
        acct_in_coa = row['ACCT_IN_COA']

        if acct_not_found not in accounts_dict.keys():
            accounts_dict[acct_not_found] = acct_in_coa

    return accounts_dict

def load_items_from_csv(path: str | Path) -> list[Item]:
    """Load items from a CSV file and return a list of Item objects."""
    path = Path(path)
    items: list[Item] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            item = Item.from_dict(row)
            items.append(item)
    return items

def load_items_dict_from_csv(path: str | Path) -> dict[str, str]:
    path = Path(path)
    items_dict: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
      reader = csv.DictReader(fh)
      for row in reader:
        item_not_found = row['ITEM_NOT_FOUND']
        item_in_coa = row['ITEM_IN_LIST']

        if item_not_found not in items_dict.keys():
            items_dict[item_not_found] = item_in_coa

    return items_dict


def load_parties_from_csv(path: str | Path, party_type: str) -> list[Party]:
    """Load parties (suppliers or customers) from a CSV file and return a list of Party objects.

    party_type should be either 'Supplier' or 'Customer'. The function will look for
    the appropriate name column in the CSV ('Supplier Name' or 'Customer Name').
    """
    path = Path(path)
    parties: list[Party] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            parties.append(Party.from_dict(row, party_type))
    return parties


def load_suppliers_from_csv(path: str | Path) -> list[Party]:
    return load_parties_from_csv(path, "Supplier")


def load_customers_from_csv(path: str | Path) -> list[Party]:
    return load_parties_from_csv(path, "Customer")

def load_all_parties_from_csv(supplier_list_path: str, customer_list_path: str):
   suppliers = load_suppliers_from_csv(supplier_list_path)
   customers = load_customers_from_csv(customer_list_path)

   parties: list[Party] = []
   parties.extend(suppliers)
   parties.extend(customers)

   return parties

def is_of_type(child_account_name: str, parent_account_name: str, accounts: list[Account]):
  filtered_accounts = list(filter(lambda x: x.name == child_account_name, accounts))
  if not any(filtered_accounts):
     return False

  account = filtered_accounts[0]
  if not account.parent:
    return False
  
  if parent_account_name.lower() in account.parent.lower():
    return True

  parent_account = list(filter(lambda x: x.id == account.parent, accounts))[0]
  return is_of_type(parent_account.name, parent_account_name, accounts)

def is_sundry_debtor(accounts: list[Account], transactions: list[Transaction], check_all: bool = False) -> bool:
    return is_any_of_type(accounts, transactions, "sundry debtor", check_all)

def is_sundry_creditor(accounts: list[Account], transactions: list[Transaction], check_all: bool = False) -> bool:
    return is_any_of_type(accounts, transactions, "sundry creditor", check_all)

def is_bank_account(accounts: list[Account], transactions: list[Transaction], check_all: bool = False) -> bool:
    return is_any_of_type(accounts, transactions, "bank account", check_all)

def is_any_of_type(accounts: list[Account], transactions: list[Transaction], type: str, check_all: bool) -> bool:
    account_names = list(map(lambda x: x.account, transactions))
    filtered_accounts = list(filter(lambda x: x.name in account_names, accounts))
    non_existent_accounts = list(filter(lambda x: x.name not in account_names, accounts))
    filter_method = all if check_all else any
    return filter_method(account.parent and type in account.parent.lower() for account in filtered_accounts) and (not check_all or not any(non_existent_accounts))
