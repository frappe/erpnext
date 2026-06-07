# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Purchase Receipt billing sync and provisional-entry cancellation for Purchase Invoice."""

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.stock.doctype.purchase_receipt.services.billing_status import (
	update_billed_amount_based_on_po,
	update_billing_percentage,
)


class BillingStatusService:
	def __init__(self, doc):
		self.doc = doc

	def update_billing_status_in_pr(self, update_modified: bool = True) -> None:
		doc = self.doc
		if doc.is_return and not doc.update_billed_amount_in_purchase_receipt:
			return

		updated_pr = []
		po_details = []

		pr_details_billed_amt = self.get_pr_details_billed_amt()

		for d in doc.get("items"):
			if d.pr_detail:
				frappe.db.set_value(
					"Purchase Receipt Item",
					d.pr_detail,
					"billed_amt",
					flt(pr_details_billed_amt.get(d.pr_detail)),
					update_modified=update_modified,
				)
				updated_pr.append(d.purchase_receipt)
			elif d.po_detail:
				po_details.append(d.po_detail)

		if po_details:
			updated_pr += update_billed_amount_based_on_po(po_details, update_modified)

		adjust_incoming_rate = frappe.db.get_single_value(
			"Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate"
		)

		for pr in set(updated_pr):
			pr_doc = frappe.get_lazy_doc("Purchase Receipt", pr)
			update_billing_percentage(
				pr_doc, update_modified=update_modified, adjust_incoming_rate=adjust_incoming_rate
			)

	def get_pr_details_billed_amt(self) -> dict:
		# Get billed amount based on purchase receipt item reference (pr_detail) in purchase invoice

		pr_details_billed_amt = {}
		pr_details = [d.get("pr_detail") for d in self.doc.get("items") if d.get("pr_detail")]
		if pr_details:
			doctype = frappe.qb.DocType("Purchase Invoice Item")
			query = (
				frappe.qb.from_(doctype)
				.select(doctype.pr_detail, Sum(doctype.amount))
				.where(doctype.pr_detail.isin(pr_details) & doctype.docstatus == 1)
				.groupby(doctype.pr_detail)
			)

			pr_details_billed_amt = frappe._dict(query.run(as_list=1))

		return pr_details_billed_amt

	def cancel_provisional_entries(self) -> None:
		rows = set()
		purchase_receipts = set()
		for d in self.doc.items:
			if d.purchase_receipt:
				purchase_receipts.add(d.purchase_receipt)
				rows.add(d.name)

		if rows:
			# cancel gl entries
			gle = qb.DocType("GL Entry")
			gle_update_query = (
				qb.update(gle)
				.set(gle.is_cancelled, 1)
				.where(
					(gle.voucher_type == "Purchase Receipt")
					& (gle.voucher_no.isin(purchase_receipts))
					& (gle.voucher_detail_no.isin(rows))
				)
			)
			gle_update_query.run()
