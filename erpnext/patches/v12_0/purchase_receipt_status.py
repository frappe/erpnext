""" This patch fixes old purchase receipts (PR) where even after submitting
	the PR, the `status` remains "Draft". `per_billed` field was copied over from previous
	doc (PO), hence it is recalculated for setting new correct status of PR.
"""

import frappe

def execute():
	affected_purchase_receipts = frappe.db.sql(
		"""select name from `tabPurchase Receipt`
		where status = 'Draft' and per_billed = 100 and docstatus = 1"""
	)

	if not affected_purchase_receipts:
		return


	for pr in affected_purchase_receipts:
		pr_name = pr[0]

		pr_doc = frappe.get_doc("Purchase Receipt", pr_name)

		pr_doc.update_billing_status(update_modified=False)
		pr_doc.set_status(update=True, update_modified=False)
