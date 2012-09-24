import webnotes
def execute():
	set_master_name_in_accounts()
	set_customer_in_sales_invoices()
	reset_lft_rgt()
	add_analytics_role()

def set_master_name_in_accounts():
	accounts = webnotes.conn.sql("""select name, account_name, master_type from tabAccount
		where ifnull(master_name, '')=''""", as_dict=1)
	for acc in accounts:
		if acc["master_type"] in ["Customer", "Supplier"]:
			master = webnotes.conn.sql("""select name from `tab%s`
				where name=%s """ % (acc["master_type"], "%s"), acc["account_name"])
			if master:
				webnotes.conn.sql("""update `tabAccount`
					set master_name=%s where name=%s""", (master[0][0], acc["name"]))
	
def set_customer_in_sales_invoices():
	webnotes.conn.sql("""update `tabSales Invoice` si
		set si.customer=(select a.master_name from `tabAccount` a where a.name=si.debit_to)
		where ifnull(si.customer, '')=''""")
		
def reset_lft_rgt():
	from webnotes.utils.nestedset import rebuild_tree
	
	rebuild_tree("Item Group", "parent_item_group")
	rebuild_tree("Customer Group", "parent_customer_group")
	rebuild_tree("Territory", "parent_territory")
	rebuild_tree("Account", "parent_account")
	rebuild_tree("Cost Center", "parent_cost_center")
	rebuild_tree("Sales Person", "parent_sales_person")
	
def add_analytics_role():
	from webnotes.model.doc import Document
	Document("Role", fielddata={
		"name": "Analytics",
		"role_name": "Analytics",
		"module": "Setup",
	}).save(1);