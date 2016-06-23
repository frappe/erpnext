import frappe
from frappe import _

def execute():
	frappe.reload_doc("stock", "doctype", "warehouse")
	for company in frappe.get_all("Company", fields=["name", "abbr"]):
		if not frappe.db.get_value("Warehouse", "{0} - {1}".format(_("All Warehouses"), company.abbr)):
			create_default_warehouse_group(company)
		
		for warehouse in frappe.get_all("Warehouse", {"company": company}, ["name", "create_account_under", "parent_warehouse"]):
			set_parent_to_warehouses(warehouse, company)
			set_parent_to_warehouse_acounts(warehouse, company)

def set_parent_to_warehouses(warehouse, company):
	warehouse = frappe.get_doc("Warehouse", warehouse.name)
	warehouse.is_group = "No"
	
	if not warehouse.parent_warehouse:
		warehouse.parent_warehouse = "{0} - {1}".format(_("All Warehouses"), company.abbr)
	
	warehouse.save()

def set_parent_to_warehouse_acounts(warehouse, company):
	account = frappe.db.get_value("Account", {"warehouse": warehouse.name})
	stock_group = frappe.db.get_value("Account", {"account_type": "Stock",
		"is_group": 1, "company": company.name})

	if account:
		account = frappe.get_doc("Account", account)

		if warehouse.create_account_under == stock_group or not warehouse.create_account_under:
			if not warehouse.parent_warehouse:
				account.parent_account = "{0} - {1}".format(_("All Warehouses"), company.abbr)
			else:
				account.parent_account = frappe.db.get_value("Account", {"warehouse": warehouse.parent_warehouse})
		account.save(ignore_permissions=True)

def create_default_warehouse_group(company):
	frappe.get_doc({
		"doctype": "Warehouse",
		"warehouse_name": _("All Warehouses"),
		"is_group": "Yes",
		"company": company.name,
		"parent_warehouse": ""
	}).insert(ignore_permissions=True)