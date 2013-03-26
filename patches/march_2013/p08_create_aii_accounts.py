import webnotes
def execute():
	accounts_to_add = [
		["Stock Assets", "Current Assets", "Group", ""],
		["Stock In Hand", "Stock Assets", "Ledger", ""],
		["Stock Debit But Not Billed", "Stock Assets", "Ledger", ""],
		["Stock Expenses", "Direct Expenses", "Group", "Expense Account"],
		["Cost of Goods Sold", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Adjustment", "Stock Expenses", "Ledger", "Expense Account"],
		["Expenses Included In Valuation", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Liabilities", "Current Liabilities", "Group", ""],
		["Stock Received But Not Billed", "Stock Liabilities", "Ledger", ""],
	]
	
	for company, abbr in webnotes.conn.sql_list("""select name, abbr from `tabCompany`"""):
		for account_name, parent_account_name, group_or_ledger, account_type in accounts_to_add:
			if not webnotes.conn.exists("Account", "%s - %s" % (account_name, abbr)):
				account = webnotes.bean({
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": "%s - %s" % (parent_account_name, abbr),
					"group_or_ledger": group_or_ledger,
					"account_type": account_type,
					"company": company
				})
				account.insert()