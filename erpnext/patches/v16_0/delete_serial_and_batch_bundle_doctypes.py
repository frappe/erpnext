import frappe


def execute():
	# Stock Location Ledger has been the sole source of truth for serial/batch stock movement
	# for a while now - nothing creates a real Serial and Batch Bundle document anymore. Drop
	# both doctypes outright; this is a pre-release branch so no site needs a data migration.
	for doctype in ("Serial and Batch Bundle", "Serial and Batch Entry"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, ignore_missing=True, force=True)
