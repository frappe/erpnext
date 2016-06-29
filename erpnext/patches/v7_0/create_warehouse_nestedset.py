import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import rebuild_tree

def execute():
	frappe.reload_doc("stock", "doctype", "warehouse")

	for company in frappe.get_all("Company", fields=["name", "abbr"]):
		validate_parent_account_for_warehouse(company)
		
		if not frappe.db.get_value("Warehouse", "{0} - {1}".format(_("All Warehouses"), company.abbr)):
			create_default_warehouse_group(company)
		
		set_parent_to_warehouse(company)
		if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
			set_parent_to_warehouse_acount(company)

def set_parent_to_warehouse(company):
	frappe.db.sql(""" update tabWarehouse set parent_warehouse = %s
		where (is_group = 0 or is_group is null or is_group = '') and ifnull(company, '') = %s
		""",("{0} - {1}".format(_("All Warehouses"), company.abbr), company.name))
	
	rebuild_tree("Warehouse", "parent_warehouse")

def set_parent_to_warehouse_acount(company):
	frappe.db.sql(""" update tabAccount set parent_account = %s
		where is_group = 0 and account_type = "Warehouse"
		and (warehouse is not null or warehouse != '') and company = %s
		""",("{0} - {1}".format(_("All Warehouses"), company.abbr), company.name))
	
	rebuild_tree("Account", "parent_account")

def create_default_warehouse_group(company):
	frappe.get_doc({
		"doctype": "Warehouse",
		"warehouse_name": _("All Warehouses"),
		"is_group": 1,
		"company": company.name,
		"parent_warehouse": ""
	}).insert(ignore_permissions=True)
	
def validate_parent_account_for_warehouse(company):
	if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):

		parent_account = frappe.db.sql("""select name from tabAccount
			where account_type='Stock' and company=%s and is_group=1
			and (warehouse is null or warehouse = '')""", company.name)

		if not parent_account:
			current_parent_accounts_for_warehouse = frappe.db.sql("""select parent_account from tabAccount
				where account_type='Warehouse' and (warehouse is not null or warehouse != '') """)

			if current_parent_accounts_for_warehouse:
				frappe.db.set_value("Account", current_parent_accounts_for_warehouse[0][0], "account_type", "Stock")
