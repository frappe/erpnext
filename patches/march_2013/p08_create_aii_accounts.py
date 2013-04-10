import webnotes
def execute():
	webnotes.reload_doc("setup", "doctype", "company")
	create_chart_of_accounts_if_not_exists()
	add_group_accounts()
	add_ledger_accounts()
	add_aii_cost_center()
	set_default_accounts()
	
def set_default_accounts():
	for company in webnotes.conn.sql_list("select name from `tabCompany`"):
		webnotes.get_obj("Company", company).set_default_accounts()
	
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
		["Cost of Goods Sold", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Adjustment", "Stock Expenses", "Ledger", "Expense Account"],
		["Expenses Included In Valuation", "Stock Expenses", "Ledger", "Expense Account"],
		["Stock Received But Not Billed", "Stock Liabilities", "Ledger", ""],
	]
	add_accounts(accounts_to_add)
	
	
def add_accounts(accounts_to_add, check_fn=None):	
	for company, abbr in webnotes.conn.sql("""select name, abbr from `tabCompany`"""):
		count = webnotes.conn.sql("""select count(name) from `tabAccount`
			where company=%s and ifnull(parent_account, '')=''""", company)[0][0]
		
		if count > 4:
			print "Company", company, \
				"has more than 4 root accounts. cannot apply patch to this company."
			continue
		
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
				
def add_aii_cost_center():
	for company, abbr in webnotes.conn.sql("""select name, abbr from `tabCompany`"""):
		if not webnotes.conn.exists("Cost Center", "Auto Inventory Accounting - %s" % abbr):
			parent_cost_center = webnotes.conn.get_value("Cost Center", 
				{"parent_cost_center['']": '', "company_name": company})
				
			if not parent_cost_center:
				print "Company", company, "does not have a root cost center"
				continue
			
			cc = webnotes.bean({
				"doctype": "Cost Center",
				"cost_center_name": "Auto Inventory Accounting",
				"parent_cost_center": parent_cost_center,
				"group_or_ledger": "Ledger",
				"company_name": company
			})
			cc.insert()
				
def create_chart_of_accounts_if_not_exists():
	for company in webnotes.conn.sql("select name from `tabCompany`"):
		if not webnotes.conn.sql("select * from `tabAccount` where company = %s", company[0]):
			webnotes.conn.sql("""update `tabCompany` set receivables_group = '', 
				payables_group = '' where name = %s""", company[0])
			webnotes.bean("Company", company[0]).save()
				