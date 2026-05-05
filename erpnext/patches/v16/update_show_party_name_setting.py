import frappe
from frappe.utils import cint


def execute():
	"""Update party name visibility setting based on earlier naming convention logic"""
	cust_naming = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	supp_naming = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	frappe.db.set_single_value(
		"Selling Settings", "show_customer_name_in_reports", cint(cust_naming == "Naming Series")
	)
	frappe.db.set_single_value(
		"Buying Settings", "show_supplier_name_in_reports", cint(supp_naming == "Naming Series")
	)
