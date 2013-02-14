def make_test_records(verbose):
	from webnotes.test_runner import make_test_objects
		
	accounts = [
		# [account_name, parent_account, group_or_ledger]
		["_Test Account Bank Account", "Bank Accounts - _TC", "Ledger"],
		["_Test Account Stock Expenses", "Direct Expenses - _TC", "Group"],
		["_Test Account Shipping Charges", "_Test Account Stock Expenses - _TC", "Ledger"],
		["_Test Account Customs Duty", "_Test Account Stock Expenses - _TC", "Ledger"],
		["_Test Account Tax Assets", "Current Assets - _TC", "Group"],
		["_Test Account VAT", "_Test Account Tax Assets - _TC", "Ledger"],
		["_Test Account Service Tax", "_Test Account Tax Assets - _TC", "Ledger"],
		["_Test Account Cost for Goods Sold", "Expenses - _TC", "Ledger"],
		["_Test Account Excise Duty", "_Test Account Tax Assets - _TC", "Ledger"],
		["_Test Account Education Cess", "_Test Account Tax Assets - _TC", "Ledger"],
		["_Test Account S&H Education Cess", "_Test Account Tax Assets - _TC", "Ledger"],
		["_Test Account CST", "Direct Expenses - _TC", "Ledger"],
		["_Test Account Discount", "Direct Expenses - _TC", "Ledger"],
	]

	return make_test_objects("Account", [[{
			"doctype": "Account",
			"account_name": account_name,
			"parent_account": parent_account,
			"company": "_Test Company",
			"group_or_ledger": group_or_ledger
		}] for account_name, parent_account, group_or_ledger in accounts])