import frappe

def execute():
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt_item')
	frappe.reload_doc('stock', 'doctype', 'purchase_receipt')

	purchase_receipts = frappe.db.sql("""
		SELECT
			 parent from `tabPurchase Receipt Item`
		WHERE
			material_request is not null
			AND docstatus=1
		""",as_dict=1)

	purchase_receipts = set([d.parent for d in purchase_receipts])

	for pr in purchase_receipts:
		doc = frappe.get_doc("Purchase Receipt", pr)
		doc.update_previous_doc_status()
