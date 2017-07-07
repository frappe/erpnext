
from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import cint
from frappe.utils.nestedset import rebuild_tree

def execute():
	"""
	Patch Reference:
		1. check whether warehouse is associated to company or not
		2. if warehouse is associated with company
			a. create warehouse group for company
			b. set warehouse group as parent to other warehouses and set is_group as 0
		3. if warehouses is not associated with company
			a. get distinct companies from stock ledger entries
			b. if sle have only company,
				i. set default company to all warehouse
				ii. repeat 2.a and 2.b
			c. if have multiple companies,
				i. create group warehouse without company
				ii. repeat 2.b
	"""
	
	frappe.reload_doc("stock", "doctype", "warehouse")

	if check_is_warehouse_associated_with_company():
		for company in frappe.get_all("Company", fields=["name", "abbr"]):
			make_warehouse_nestedset(company)
	else:
		sle_against_companies = frappe.db.sql_list("""select distinct company from `tabStock Ledger Entry`""")

		if len(sle_against_companies) == 1:
			company = frappe.db.get_value("Company", sle_against_companies[0], 
				fieldname=["name", "abbr"], as_dict=1)
			set_company_to_warehouse(company.name)
			make_warehouse_nestedset(company)

		elif len(sle_against_companies) > 1:
			make_warehouse_nestedset()

def check_is_warehouse_associated_with_company():
	warehouse_associcated_with_company = False

	for warehouse in frappe.get_all("Warehouse", fields=["name", "company"]):
		if warehouse.company:
			warehouse_associcated_with_company = True

	return warehouse_associcated_with_company

def make_warehouse_nestedset(company=None):
	validate_parent_account_for_warehouse(company)
	stock_account_group = get_stock_account_group(company.name)
	enable_perpetual_inventory = cint(erpnext.is_perpetual_inventory_enabled(company)) or 0
	if not stock_account_group and enable_perpetual_inventory:
		return

	if company:
		warehouse_group = "{0} - {1}".format(_("All Warehouses"), company.abbr)
		ignore_mandatory = False
	else:
		warehouse_group = _("All Warehouses")
		ignore_mandatory = True

	if not frappe.db.get_value("Warehouse", warehouse_group):
		create_default_warehouse_group(company, stock_account_group, ignore_mandatory)

	set_parent_to_warehouse(warehouse_group, company)
	if enable_perpetual_inventory:
		set_parent_to_warehouse_account(company)

def validate_parent_account_for_warehouse(company=None):
	if not company:
		return

	if cint(erpnext.is_perpetual_inventory_enabled(company.name)):
		parent_account = frappe.db.sql("""select name from tabAccount
			where account_type='Stock' and company=%s and is_group=1
			and (warehouse is null or warehouse = '')""", company.name)

		if not parent_account:
			current_parent_accounts_for_warehouse = frappe.db.sql("""select parent_account from tabAccount
				where account_type='Warehouse' and (warehouse is not null or warehouse != '') """)

			if current_parent_accounts_for_warehouse:
				frappe.db.set_value("Account", current_parent_accounts_for_warehouse[0][0], "account_type", "Stock")

def create_default_warehouse_group(company=None, stock_account_group=None, ignore_mandatory=False):
	wh = frappe.get_doc({
		"doctype": "Warehouse",
		"warehouse_name": _("All Warehouses"),
		"is_group": 1,
		"company": company.name if company else "",
		"parent_warehouse": ""
	})

	if ignore_mandatory:
		wh.flags.ignore_mandatory = ignore_mandatory

	wh.insert(ignore_permissions=True)

def set_parent_to_warehouse(warehouse_group, company=None):
	frappe.db.sql(""" update tabWarehouse set parent_warehouse = %s, is_group = 0
		where (is_group = 0 or is_group is null or is_group = '') and ifnull(company, '') = %s
		""",(warehouse_group, company.name if company else ""))

	rebuild_tree("Warehouse", "parent_warehouse")

def set_parent_to_warehouse_account(company):
	frappe.db.sql(""" update tabAccount set parent_account = %s
		where is_group = 0 and account_type = "Warehouse"
		and (warehouse is not null or warehouse != '') and company = %s
		""",("{0} - {1}".format(_("All Warehouses"), company.abbr), company.name))

	rebuild_tree("Account", "parent_account")

def set_company_to_warehouse(company):
	frappe.db.sql("update tabWahouse set company=%s", company)

def get_stock_account_group(company):
	stock_account_group = frappe.db.get_all('Account', filters = {'company': company, 'is_group': 1,
		'account_type': 'Stock', 'root_type': 'Asset'}, limit=1)
			
	if not stock_account_group:
		stock_account_group = frappe.db.get_all('Account', filters = {'company': company, 'is_group': 1,
				'parent_account': '', 'root_type': 'Asset'}, limit=1)

	return stock_account_group[0].name if stock_account_group else None