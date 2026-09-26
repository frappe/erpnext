# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Purchase Receipt and Purchase Order billing sync and provisional-entry cancellation for Purchase Invoice."""

import frappe
from frappe import qb
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext.stock.doctype.purchase_receipt.services.billing_status import (
	get_invoiced_qty_and_amount,
	get_purchase_receipts_against_po_details,
	is_billed_by_qty,
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

		if not is_billed_by_qty():
			for pr in set(updated_pr):
				pr_doc = frappe.get_lazy_doc("Purchase Receipt", pr)
				update_billing_percentage(pr_doc, update_modified=update_modified)
			return

		self.update_billing_status_in_receipts_on_po_lines(set(updated_pr), update_modified)

	def update_billing_status_in_receipts_on_po_lines(self, updated_pr: set, update_modified: bool) -> None:
		"""Order invoices are spread over every receipt on the line, so all of them are refreshed from one split."""
		pr_docs = [
			frappe.get_lazy_doc("Purchase Receipt", pr) for pr in updated_pr | self.get_receipts_on_po_lines()
		]

		pr_items = []
		for pr_doc in pr_docs:
			pr_items.extend(pr_doc.items)

		bill_for_rejected = frappe.db.get_single_value(
			"Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"
		)
		invoiced = get_invoiced_qty_and_amount(pr_items, bill_for_rejected)

		for pr_doc in pr_docs:
			update_billing_percentage(
				pr_doc,
				update_modified=update_modified,
				adjust_incoming_rate=True,
				invoiced=invoiced,
			)

	def get_receipts_on_po_lines(self) -> set:
		po_details = list({d.po_detail for d in self.doc.get("items") if d.po_detail})
		if not po_details:
			return set()

		return {pr_item.parent for pr_item in get_purchase_receipts_against_po_details(po_details)}

	def update_billing_status_in_po(self) -> None:
		doc = self.doc
		if not is_billed_by_qty() or (doc.is_return and not doc.update_billed_amount_in_purchase_order):
			return

		for purchase_order in {item.purchase_order for item in doc.items if item.purchase_order}:
			frappe.get_doc("Purchase Order", purchase_order).update_billing_percentage()

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
