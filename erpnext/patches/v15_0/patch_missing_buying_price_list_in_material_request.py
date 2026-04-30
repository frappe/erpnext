import frappe
import frappe.defaults


def execute():
	if frappe.db.has_column("Material Request", "buying_price_list") and (
		default_buying_price_list := frappe.defaults.get_defaults().buying_price_list
	):
		docs = frappe.get_all(
			"Material Request", filters={"buying_price_list": ["is", "not set"], "docstatus": 1}, pluck="name"
		)
		frappe.db.auto_commit_on_many_writes = 1
		try:
			for doc in docs:
				frappe.db.set_value("Material Request", doc, "buying_price_list", default_buying_price_list)
		finally:
			frappe.db.auto_commit_on_many_writes = 0
