import frappe
from frappe.utils import cint


def execute():
	"""Back-fill the new party name visibility setting from the earlier naming convention.

	Older reports showed the party name column when the party was *not* named after its
	name field, i.e. when naming was by "Naming Series" or "Auto Name". Preserve that
	behaviour so existing installs keep seeing the column they saw before.
	"""
	non_name_based = ("Naming Series", "Auto Name")

	cust_naming = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	supp_naming = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	frappe.db.set_single_value(
		"Selling Settings", "show_customer_name_in_reports", cint(cust_naming in non_name_based)
	)
	frappe.db.set_single_value(
		"Buying Settings", "show_supplier_name_in_reports", cint(supp_naming in non_name_based)
	)
