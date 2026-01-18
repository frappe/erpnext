import frappe
from frappe.utils import cint


def execute():
	frappe.db.set_single_value(
		"Stock Settings",
		"update_price_list_based_on",
		(
			"Price List Rate"
			if cint(frappe.db.get_single_value("Selling Settings", "editable_price_list_rate"))
			else "Rate"
		),
	)
