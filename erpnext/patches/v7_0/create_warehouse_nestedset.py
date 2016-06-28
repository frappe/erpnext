import frappe
from frappe import _
from frappe.utils import cint

def execute():
	frappe.reload_doc("stock", "doctype", "warehouse")

	for company in frappe.get_all("Company", fields=["name", "abbr"]):
		validate_parent_account_for_warehouse(company)
		
		if not frappe.db.get_value("Warehouse", "{0} - {1}".format(_("All Warehouses"), company.abbr)):
			create_default_warehouse_group(company)
		
		for warehouse in frappe.get_all("Warehouse", filters={"company": company.name}, fields=["name", "create_account_under",
			"parent_warehouse", "is_group"]):
			set_parent_to_warehouses(warehouse, company)
			if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")):
				set_parent_to_warehouse_acounts(warehouse, company)

def set_parent_to_warehouses(warehouse, company):
	warehouse = frappe.get_doc("Warehouse", warehouse.name)
	warehouse.is_group = warehouse.is_group
	
	if not warehouse.parent_warehouse and warehouse.name != "{0} - {1}".format(_("All Warehouses"), company.abbr):
		warehouse.parent_warehouse = "{0} - {1}".format(_("All Warehouses"), company.abbr)
	
	warehouse.save(ignore_permissions=True)

def set_parent_to_warehouse_acounts(warehouse, company):
	account = frappe.db.get_value("Account", {"warehouse": warehouse.name})
	stock_group = frappe.db.get_value("Account", {"account_type": "Stock",
		"is_group": 1, "company": company.name})

	if account and account != "{0} - {1}".format(_("All Warehouses"), company.abbr):
		account = frappe.get_doc("Account", account)
		
		if warehouse.create_account_under == stock_group or not warehouse.create_account_under:
			if not warehouse.parent_warehouse:
				account.parent_account = "{0} - {1}".format(_("All Warehouses"), company.abbr)
			else:
				account.parent_account = frappe.db.get_value("Account", warehouse.parent_warehouse)

		account.save(ignore_permissions=True)

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
				doc = frappe.get_doc("Account", current_parent_accounts_for_warehouse[0][0])
				doc.account_type = "Stock"
				doc.warehouse = ""
				doc.save(ignore_permissions=True)
