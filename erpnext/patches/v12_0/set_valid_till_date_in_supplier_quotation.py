import frappe
from frappe.utils import add_to_date


def execute():
	frappe.reload_doc("buying", "doctype", "supplier_quotation")
	for row in frappe.get_all(
		"Supplier Quotation",
		filters={"docstatus": ["<", 2]},
		fields=["name", "transaction_date"],
	):
		frappe.db.set_value(
			"Supplier Quotation",
			row.name,
			"valid_till",
			add_to_date(row.transaction_date, months=1, as_string=True),
			update_modified=False,
		)
