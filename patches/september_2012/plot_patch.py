# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
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
	dt = [
		["Item Group", "parent_item_group"], 
		["Customer Group", "parent_customer_group"],
		["Territory", "parent_territory"],
		["Account", "parent_account"], 
		["Cost Center", "parent_cost_center"],
		["Sales Person", "parent_sales_person"]
	]
	for d in dt:
		rebuild_tree(d[0], d[1])
		webnotes.conn.commit()
		webnotes.conn.begin()
	
def add_analytics_role():
	from webnotes.model.doc import Document
	Document("Role", fielddata={
		"name": "Analytics",
		"role_name": "Analytics",
		"module": "Setup",
	}).save(1);