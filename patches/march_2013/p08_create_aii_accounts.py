import webnotes
def execute():
	add_group_accounts()
	add_ledger_accounts()
	
def _check(parent_account, company):
	def _get_root(is_pl_account, debit_or_credit):
		res = webnotes.conn.sql("""select name from `tabAccount`
			where company=%s and is_pl_account = %s and debit_or_credit = %s
			and ifnull(parent_account, "") ="" """, (company, is_pl_account, debit_or_credit))
		return res and res[0][0] or None
		
	if not webnotes.conn.exists("Account", parent_account):
		if parent_account.startswith("Current Assets"):
			parent_account = _get_root("No", "Debit")
		elif parent_account.startswith("Direct Expenses"):
			parent_account = _get_root("Yes", "Debit")
		elif parent_account.startswith("Current Liabilities"):
			parent_account = _get_root("No", "Credit")

	return parent_account
	
	
def add_group_accounts():
	accounts_to_add = [
		["Stock Assets", "Current Assets", "Group", ""],
		["Stock Expenses", "Direct Expenses", "Group", "Expense Account"],
		["Stock Liabilities", "Current Liabilities", "Group", ""],
	]
		
	add_accounts(accounts_to_add, _check)
	
	
def add_ledger_accounts():
	accounts_to_add = [
		["Stock In Hand", "Stock Assets", "Ledger", ""],
		["Stock Debit But Not Billed", "Stock Assets", "Ledger", ""],
		["Cost of Goods Sold", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Adjustment", "Stock Expenses", "Ledger", "Expense Account"],
		["Expenses Included In Valuation", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Received But Not Billed", "Stock Liabilities", "Ledger", ""],
	]
	add_accounts(accounts_to_add)
	
	
def add_accounts(accounts_to_add, check_fn=None):	
	for company, abbr in webnotes.conn.sql("""select name, abbr from `tabCompany`"""):
		for account_name, parent_account_name, group_or_ledger, account_type in accounts_to_add:
			if not webnotes.conn.exists("Account", "%s - %s" % (account_name, abbr)):
				parent_account = "%s - %s" % (parent_account_name, abbr)
				if check_fn:
					parent_account = check_fn(parent_account, company)
				account = webnotes.bean({
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": parent_account,
					"group_or_ledger": group_or_ledger,
					"account_type": account_type,
					"company": company
				})
				account.insert()