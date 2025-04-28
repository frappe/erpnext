import frappe


def execute():
	subscription_invoices = frappe.get_all(
		"Subscription Invoice", fields=["document_type", "invoice", "parent"]
	)

	for subscription_invoice in subscription_invoices:
		frappe.db.set_value(
			subscription_invoice.document_type,
			subscription_invoice.invoice,
			"subscription",
			subscription_invoice.parent,
<<<<<<< HEAD
			update_modified=False,
		)

	frappe.delete_doc_if_exists("DocType", "Subscription Invoice", force=1)
=======
		)

	frappe.delete_doc_if_exists("DocType", "Subscription Invoice")
>>>>>>> 7c4cf3e834 (Favicon.svg)
