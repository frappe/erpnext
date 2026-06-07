# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Payment schedule and payment terms helpers."""

import frappe
from frappe import _
from frappe.utils import DateTimeLikeObject, add_days, add_months, cint, flt, get_last_day, getdate

from erpnext.accounts.party import get_party_account_currency


class PaymentScheduleService:
	def __init__(self, doc):
		self.doc = doc

	def set_payment_schedule(self) -> None:
		doc = self.doc
		if (doc.doctype == "Sales Invoice" and doc.is_pos) or doc.get("is_opening") == "Yes":
			doc.payment_terms_template = ""
			return

		party_account_currency = doc.get("party_account_currency")
		if not party_account_currency:
			party_type, party = doc.get_party()
			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, doc.company)

		posting_date = doc.get("bill_date") or doc.get("posting_date") or doc.get("transaction_date")
		due_date = doc.get("due_date") or posting_date

		base_grand_total = flt(doc.get("base_rounded_total") or doc.base_grand_total)
		grand_total = flt(doc.get("rounded_total") or doc.grand_total)
		automatically_fetch_payment_terms = 0

		if doc.doctype in ("Sales Invoice", "Purchase Invoice", "Sales Order"):
			po_or_so, doctype, fieldname = self.get_order_details()
			automatically_fetch_payment_terms = cint(
				frappe.get_single_value("Accounts Settings", "automatically_fetch_payment_terms")
			)
			if doc.doctype != "Sales Order":
				base_grand_total = base_grand_total - flt(doc.base_write_off_amount)
				grand_total = grand_total - flt(doc.write_off_amount)

		if doc.get("total_advance"):
			if party_account_currency == doc.company_currency:
				base_grand_total -= doc.get("total_advance")
				grand_total = flt(base_grand_total / doc.get("conversion_rate"), doc.precision("grand_total"))
			else:
				grand_total -= doc.get("total_advance")
				base_grand_total = flt(
					grand_total * doc.get("conversion_rate"), doc.precision("base_grand_total")
				)

		if not doc.get("payment_schedule"):
			if (
				doc.doctype in ["Sales Invoice", "Purchase Invoice", "Sales Order"]
				and automatically_fetch_payment_terms
				and self.linked_order_has_payment_terms(po_or_so, fieldname, doctype)
			):
				self.fetch_payment_terms_from_order(
					po_or_so, doctype, grand_total, base_grand_total, automatically_fetch_payment_terms
				)
				if doc.get("payment_terms_template"):
					doc.ignore_default_payment_terms_template = 1
			elif doc.get("payment_terms_template"):
				data = get_payment_terms(
					doc.payment_terms_template, posting_date, grand_total, base_grand_total
				)
				for item in data:
					doc.append("payment_schedule", item)
			elif doc.doctype not in ["Purchase Receipt"]:
				doc.append(
					"payment_schedule",
					dict(
						due_date=due_date,
						invoice_portion=100,
						payment_amount=grand_total,
						base_payment_amount=base_grand_total,
					),
				)

		allocate_payment_based_on_payment_terms = frappe.db.get_value(
			"Payment Terms Template",
			doc.payment_terms_template,
			"allocate_payment_based_on_payment_terms",
		)

		if not (
			automatically_fetch_payment_terms
			and allocate_payment_based_on_payment_terms
			and self.linked_order_has_payment_terms(po_or_so, fieldname, doctype)
		):
			for d in doc.get("payment_schedule"):
				if d.invoice_portion:
					d.payment_amount = flt(
						grand_total * flt(d.invoice_portion) / 100, d.precision("payment_amount")
					)
					d.base_payment_amount = flt(
						base_grand_total * flt(d.invoice_portion) / 100, d.precision("base_payment_amount")
					)
					d.outstanding = d.payment_amount
					d.base_outstanding = d.base_payment_amount
				elif not d.invoice_portion:
					d.base_payment_amount = flt(
						d.payment_amount * doc.get("conversion_rate"), d.precision("base_payment_amount")
					)
					d.base_outstanding = d.base_payment_amount
		else:
			self.fetch_payment_terms_from_order(
				po_or_so, doctype, grand_total, base_grand_total, automatically_fetch_payment_terms
			)
			doc.ignore_default_payment_terms_template = 1

	def get_order_details(self) -> tuple:
		doc = self.doc
		if not doc.get("items"):
			return None, None, None
		if doc.doctype == "Sales Invoice":
			prev_doc = doc.get("items")[0].get("sales_order")
			prev_doctype = "Sales Order"
			prev_doctype_name = "sales_order"
		elif doc.doctype == "Purchase Invoice":
			prev_doc = doc.get("items")[0].get("purchase_order")
			prev_doctype = "Purchase Order"
			prev_doctype_name = "purchase_order"
		else:
			prev_doc = doc.get("items")[0].get("prevdoc_docname")
			prev_doctype = "Quotation"
			prev_doctype_name = "prevdoc_docname"
		return prev_doc, prev_doctype, prev_doctype_name

	def linked_order_has_payment_terms(self, po_or_so, fieldname, doctype) -> bool:
		if po_or_so and self.all_items_have_same_po_or_so(po_or_so, fieldname):
			if linked_order_has_payment_terms_template(po_or_so, doctype):
				return True
			elif linked_order_has_payment_schedule(po_or_so):
				return True
		return False

	def all_items_have_same_po_or_so(self, po_or_so, fieldname) -> bool:
		for item in self.doc.get("items"):
			if item.get(fieldname) != po_or_so:
				return False
		return True

	def fetch_payment_terms_from_order(
		self,
		po_or_so,
		po_or_so_doctype,
		grand_total,
		base_grand_total,
		automatically_fetch_payment_terms,
	) -> None:
		"""Fetch Payment Terms from Purchase/Sales Order when creating a new invoice."""
		doc = self.doc
		po_or_so = frappe.get_cached_doc(po_or_so_doctype, po_or_so)

		doc.payment_schedule = []
		doc.payment_terms_template = po_or_so.payment_terms_template
		posting_date = doc.get("bill_date") or doc.get("posting_date") or doc.get("transaction_date")

		for schedule in po_or_so.payment_schedule:
			payment_schedule = {
				"payment_term": schedule.payment_term,
				"due_date": schedule.due_date,
				"invoice_portion": schedule.invoice_portion,
				"mode_of_payment": schedule.mode_of_payment,
				"description": schedule.description,
				"paid_amount": schedule.paid_amount,
			}

			if automatically_fetch_payment_terms:
				if schedule.due_date_based_on:
					payment_schedule["due_date"] = get_due_date(schedule, posting_date)
					payment_schedule["due_date_based_on"] = schedule.due_date_based_on
					payment_schedule["credit_days"] = cint(schedule.credit_days)
					payment_schedule["credit_months"] = cint(schedule.credit_months)

				if schedule.discount_validity_based_on and flt(schedule.discount):
					payment_schedule["discount_date"] = get_discount_date(schedule, posting_date)
					payment_schedule["discount_validity_based_on"] = schedule.discount_validity_based_on
					payment_schedule["discount_validity"] = cint(schedule.discount_validity)

				payment_schedule["payment_amount"] = flt(
					grand_total * flt(payment_schedule["invoice_portion"]) / 100,
					schedule.precision("payment_amount"),
				)
				payment_schedule["base_payment_amount"] = flt(
					base_grand_total * flt(payment_schedule["invoice_portion"]) / 100,
					schedule.precision("base_payment_amount"),
				)
				payment_schedule["outstanding"] = payment_schedule["payment_amount"]
			else:
				payment_schedule["base_payment_amount"] = flt(
					schedule.base_payment_amount * doc.get("conversion_rate"),
					schedule.precision("base_payment_amount"),
				)

			if schedule.discount_type == "Percentage":
				payment_schedule["discount_type"] = schedule.discount_type
				payment_schedule["discount"] = schedule.discount

			if not schedule.invoice_portion:
				payment_schedule["payment_amount"] = schedule.payment_amount

			doc.append("payment_schedule", payment_schedule)

	def set_due_date(self) -> None:
		due_dates = [d.due_date for d in self.doc.get("payment_schedule") if d.due_date]
		if due_dates:
			self.doc.due_date = max(due_dates)

	def validate_payment_schedule_dates(self) -> None:
		dates = []
		li = []
		doc = self.doc

		if doc.doctype == "Sales Invoice" and doc.is_pos:
			return

		for d in doc.get("payment_schedule"):
			if not flt(d.discount):
				d.discount_date = None
			d.validate_from_to_dates("discount_date", "due_date")
			if doc.doctype in ["Sales Order", "Quotation"] and getdate(d.due_date) < getdate(
				doc.transaction_date
			):
				frappe.throw(
					_("Row {0}: Due Date in the Payment Terms table cannot be before Posting Date").format(
						d.idx
					)
				)
			elif d.due_date in dates:
				li.append(_("{0} in row {1}").format(d.due_date, d.idx))
			dates.append(d.due_date)

		if li:
			frappe.throw(
				_("Rows with duplicate due dates in other rows were found: {0}").format(
					"<br>" + "<br>".join(li)
				),
				title=_("Payment Schedule"),
			)

	def validate_payment_schedule_amount(self) -> None:
		doc = self.doc
		if (doc.doctype == "Sales Invoice" and doc.is_pos) or doc.get("is_opening") == "Yes":
			return

		party_account_currency = doc.get("party_account_currency")
		if not party_account_currency:
			party_type, party = doc.get_party()
			if party_type and party:
				party_account_currency = get_party_account_currency(party_type, party, doc.company)

		if doc.get("payment_schedule"):
			total = 0
			base_total = 0
			for d in doc.get("payment_schedule"):
				total += flt(d.payment_amount, d.precision("payment_amount"))
				base_total += flt(d.base_payment_amount, d.precision("base_payment_amount"))

			base_grand_total = flt(doc.get("base_rounded_total") or doc.base_grand_total)
			grand_total = flt(doc.get("rounded_total") or doc.grand_total)

			if doc.doctype in ("Sales Invoice", "Purchase Invoice"):
				base_grand_total = base_grand_total - flt(doc.base_write_off_amount)
				grand_total = grand_total - flt(doc.write_off_amount)

			if doc.get("total_advance"):
				if party_account_currency == doc.company_currency:
					base_grand_total -= doc.get("total_advance")
					grand_total = flt(
						base_grand_total / doc.get("conversion_rate"), doc.precision("grand_total")
					)
				else:
					grand_total -= doc.get("total_advance")
					base_grand_total = flt(
						grand_total * doc.get("conversion_rate"), doc.precision("base_grand_total")
					)

			if (
				abs(flt(total, doc.precision("grand_total")) - flt(grand_total, doc.precision("grand_total")))
				> 0.1
				or abs(
					flt(base_total, doc.precision("base_grand_total"))
					- flt(base_grand_total, doc.precision("base_grand_total"))
				)
				> 0.1
			):
				frappe.throw(
					_("Total Payment Amount in Payment Schedule must be equal to Grand / Rounded Total")
				)


def linked_order_has_payment_terms_template(po_or_so, doctype) -> str | None:
	return frappe.get_value(doctype, po_or_so, "payment_terms_template")


def linked_order_has_payment_schedule(po_or_so) -> list:
	return frappe.get_all("Payment Schedule", filters={"parent": po_or_so})


def get_payment_terms(
	terms_template: str,
	posting_date: DateTimeLikeObject | None = None,
	grand_total: float | None = None,
	base_grand_total: float | None = None,
	bill_date: DateTimeLikeObject | None = None,
) -> list:
	if not terms_template:
		return

	terms_doc = frappe.get_doc("Payment Terms Template", terms_template)
	schedule = []
	for d in terms_doc.get("terms"):
		d = frappe._dict(d.as_dict())
		term_details = get_payment_term_details(d, posting_date, grand_total, base_grand_total, bill_date)
		schedule.append(term_details)

	return schedule


@frappe.whitelist()
def get_payment_term_details(
	term: str | frappe._dict,
	posting_date: DateTimeLikeObject | None = None,
	grand_total: float | None = None,
	base_grand_total: float | None = None,
	bill_date: DateTimeLikeObject | None = None,
) -> frappe._dict:
	term_details = frappe._dict()
	if isinstance(term, str):
		term = frappe.get_doc("Payment Term", term)
	else:
		term_details.payment_term = term.payment_term

	for field in [
		"description",
		"invoice_portion",
		"discount_type",
		"discount",
		"mode_of_payment",
		"due_date_based_on",
		"credit_days",
		"credit_months",
		"discount_validity_based_on",
		"discount_validity",
	]:
		term_details[field] = term.get(field)

	term_details.payment_amount = flt(term.invoice_portion) * flt(grand_total) / 100
	term_details.base_payment_amount = flt(term.invoice_portion) * flt(base_grand_total) / 100
	term_details.outstanding = term_details.payment_amount
	term_details.base_outstanding = term_details.base_payment_amount

	has_discount = flt(term.get("discount"))
	date = bill_date or posting_date
	if date:
		term_details.due_date = get_due_date(term, date)
		term_details.discount_date = get_discount_date(term, date) if has_discount else None

	if posting_date and getdate(term_details.due_date) < getdate(posting_date):
		term_details.due_date = posting_date

	return term_details


def get_due_date(term, posting_date=None, bill_date=None):
	due_date = None
	date = bill_date or posting_date
	if term.due_date_based_on == "Day(s) after invoice date":
		due_date = add_days(date, cint(term.credit_days))
	elif term.due_date_based_on == "Day(s) after the end of the invoice month":
		due_date = add_days(get_last_day(date), cint(term.credit_days))
	elif term.due_date_based_on == "Month(s) after the end of the invoice month":
		due_date = get_last_day(add_months(date, cint(term.credit_months)))
	return due_date


def get_discount_date(term, posting_date=None, bill_date=None):
	discount_validity = None
	date = bill_date or posting_date
	if term.discount_validity_based_on == "Day(s) after invoice date":
		discount_validity = add_days(date, cint(term.discount_validity))
	elif term.discount_validity_based_on == "Day(s) after the end of the invoice month":
		discount_validity = add_days(get_last_day(date), cint(term.discount_validity))
	elif term.discount_validity_based_on == "Month(s) after the end of the invoice month":
		discount_validity = get_last_day(add_months(date, cint(term.discount_validity)))
	return discount_validity
