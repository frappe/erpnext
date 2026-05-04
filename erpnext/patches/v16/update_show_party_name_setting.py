import frappe


def execute():
	"""Update show_party_name_in_reports as per earlier settings of customer and supplier naming."""
	cust_naming = frappe.db.get_single_value("Selling Settings", "cust_master_name")
	supp_naming = frappe.db.get_single_value("Buying Settings", "supp_master_name")

	if cust_naming == "Naming Series" or supp_naming == "Naming Series":
		frappe.db.set_single_value("Accounts Settings", "show_party_name_in_reports", 1)
