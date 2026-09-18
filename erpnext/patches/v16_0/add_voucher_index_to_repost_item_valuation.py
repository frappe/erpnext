import frappe


def execute():
	# on_doctype_update only runs when the DocType itself is re-synced, so existing sites need this.
	frappe.db.add_index("Repost Item Valuation", ["voucher_no", "voucher_type", "status"], "voucher_status")
