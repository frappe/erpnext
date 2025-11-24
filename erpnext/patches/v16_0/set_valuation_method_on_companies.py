import frappe


def execute():
	valuation_method = frappe.get_single_value("Stock Settings", "valuation_method")
	for company in frappe.get_all("Company", pluck="name"):
		frappe.db.set_value("Company", company, "valuation_method", valuation_method)
