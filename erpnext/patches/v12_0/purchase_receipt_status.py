""" This patch fixes old purchase receipts (PR) where even after submitting
	the PR, the `status` remains "Draft". `per_billed` field was copied over from previous
	doc (PO), hence it is recalculated for setting new correct status of PR.
"""

import frappe

logger = frappe.logger("patch", allow_site=True, file_count=50)

def execute():
	affected_purchase_receipts = frappe.db.sql(
		"""select name from `tabPurchase Receipt`
		where status = 'Draft' and per_billed = 100 and docstatus = 1"""
	)

	if not affected_purchase_receipts:
		return

	logger.info("purchase_receipt_status: begin patch, PR count: {}"
				.format(len(affected_purchase_receipts)))

	frappe.reload_doc("stock", "doctype", "Purchase Receipt")
	frappe.reload_doc("stock", "doctype", "Purchase Receipt Item")


	for pr in affected_purchase_receipts:
		pr_name = pr[0]
		logger.info("purchase_receipt_status: patching PR - {}".format(pr_name))

		pr_doc = frappe.get_doc("Purchase Receipt", pr_name)

		pr_doc.update_billing_status(update_modified=False)
		pr_doc.set_status(update=True, update_modified=False)
