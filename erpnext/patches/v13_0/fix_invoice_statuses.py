import frappe
from frappe.utils import flt, getdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	get_total_in_party_account_currency,
	is_overdue,
)

TODAY = getdate()


def execute():
	# This fix is not related to Party Specific Item,
	# but it is needed for code introduced after Party Specific Item was
	# If your DB doesn't have this doctype yet, you should be fine
	if not frappe.db.exists("DocType", "Party Specific Item"):
		return

	for doctype in ("Purchase Invoice", "Sales Invoice"):
		fields = [
			"name",
			"status",
			"due_date",
			"outstanding_amount",
			"grand_total",
			"base_grand_total",
			"rounded_total",
			"base_rounded_total",
			"disable_rounded_total",
		]
		if doctype == "Sales Invoice":
			fields.append("is_pos")

		invoices_to_update = frappe.get_all(
			doctype,
			fields=fields,
			filters={
				"docstatus": 1,
				"status": (
					"in",
					("Overdue", "Overdue and Discounted", "Partly Paid", "Partly Paid and Discounted"),
				),
				"outstanding_amount": (">", 0),
				"modified": (">", "2021-01-01")
				# an assumption is being made that only invoices modified
				# after 2021 got affected as incorrectly overdue.
				# required for performance reasons.
			},
		)

		invoices_to_update = {invoice.name: invoice for invoice in invoices_to_update}

		payment_schedule_items = frappe.get_all(
			"Payment Schedule",
			fields=("due_date", "payment_amount", "base_payment_amount", "parent"),
			filters={"parent": ("in", invoices_to_update)},
		)

		for item in payment_schedule_items:
			invoices_to_update[item.parent].setdefault("payment_schedule", []).append(item)

		status_map = {}

		for invoice in invoices_to_update.values():
			invoice.doctype = doctype
			doc = frappe.get_doc(invoice)
			correct_status = get_correct_status(doc)
			if not correct_status or doc.status == correct_status:
				continue

			status_map.setdefault(correct_status, []).append(doc.name)

		for status, docs in status_map.items():
			frappe.db.set_value(doctype, {"name": ("in", docs)}, "status", status, update_modified=False)


def get_correct_status(doc):
	outstanding_amount = flt(doc.outstanding_amount, doc.precision("outstanding_amount"))
	total = get_total_in_party_account_currency(doc)

	status = ""
	if is_overdue(doc, total):
		status = "Overdue"
	elif 0 < outstanding_amount < total:
		status = "Partly Paid"
	elif outstanding_amount > 0 and getdate(doc.due_date) >= TODAY:
		status = "Unpaid"

	if not status:
		return

	if doc.status.endswith(" and Discounted"):
		status += " and Discounted"

	return status
