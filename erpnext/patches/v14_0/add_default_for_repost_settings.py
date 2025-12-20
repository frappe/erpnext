import frappe


def execute():
	"""
	Update Repost Accounting Ledger Settings with default values
	"""
	allowed_types = ["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"]
	repost_settings = frappe.get_doc("Repost Accounting Ledger Settings")
	for x in allowed_types:
		repost_settings.append("allowed_types", {"document_type": x, "allowed": True})
	repost_settings.save()
