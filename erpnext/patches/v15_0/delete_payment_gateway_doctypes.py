import frappe


def execute():
	for dt in ("GoCardless Settings", "GoCardless Mandate", "Mpesa Settings"):
		frappe.delete_doc("DocType", dt, ignore_missing=True)
