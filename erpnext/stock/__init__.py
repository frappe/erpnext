from __future__ import unicode_literals
import frappe

install_docs = [
	{"doctype":"Role", "role_name":"Stock Manager", "name":"Stock Manager"},
	{"doctype":"Role", "role_name":"Item Manager", "name":"Item Manager"},
	{"doctype":"Role", "role_name":"Stock User", "name":"Stock User"},
	{"doctype":"Role", "role_name":"Quality Manager", "name":"Quality Manager"},
	{"doctype":"Item Group", "item_group_name":"All Item Groups", "is_group": 1},
	{"doctype":"Item Group", "item_group_name":"Default", 
		"parent_item_group":"All Item Groups", "is_group": 0},
]

def get_warehouse_account_map():
	if not frappe.flags.warehouse_account_map or frappe.flags.in_test:
		warehouse_account = frappe._dict()

		for d in frappe.get_all('Warehouse', filters = {"is_group": 0},
			fields = ["name", "account", "parent_warehouse", "company"]):
			if not d.account:
				d.account = get_warehouse_account(d.name, d.company)

			if d.account:
				d.account_currency = frappe.db.get_value('Account', d.account, 'account_currency')
				warehouse_account.setdefault(d.name, d)
			
		frappe.flags.warehouse_account_map = warehouse_account
	return frappe.flags.warehouse_account_map

def get_warehouse_account(warehouse, company):
	lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
	account = frappe.db.sql("""
		select
			account from `tabWarehouse`
		where
			lft <= %s and rgt >= %s and company = %s
			and account is not null and ifnull(account, '') !=''
		order by lft desc limit 1""", (lft, rgt, company), as_list=1)

	account = account[0][0] if account else None
	
	if not account:
		account = get_company_default_inventory_account(company)
	
	return account
	
def get_company_default_inventory_account(company):
	return frappe.db.get_value('Company', company, 'default_inventory_account')