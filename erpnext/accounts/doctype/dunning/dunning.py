# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""
# Accounting

1. Payment of outstanding invoices with dunning amount

		- Debit full amount to bank
		- Credit invoiced amount to receivables
		- Credit dunning amount to interest and similar revenue

		-> Resolves dunning automatically
"""

import json

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.utils import getdate

from erpnext.controllers.accounts_controller import AccountsController


class Dunning(AccountsController):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.overdue_payment.overdue_payment import OverduePayment

		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		base_dunning_amount: DF.Currency
		body_text: DF.TextEditor | None
		closing_text: DF.TextEditor | None
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.TextEditor | None
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		conversion_rate: DF.Float
		cost_center: DF.Link | None
		currency: DF.Link | None
		customer: DF.Link
		customer_address: DF.Link | None
		customer_name: DF.Data | None
		dunning_amount: DF.Currency
		dunning_fee: DF.Currency
		dunning_type: DF.Link | None
		grand_total: DF.Currency
		income_account: DF.Link | None
		language: DF.Link | None
		letter_head: DF.Link | None
		naming_series: DF.Literal["DUNN-.MM.-.YY.-"]
		overdue_payments: DF.Table[OverduePayment]
		posting_date: DF.Date
		posting_time: DF.Time | None
		rate_of_interest: DF.Float
		spacer: DF.Data | None
		status: DF.Literal["Draft", "Resolved", "Unresolved", "Cancelled"]
		total_interest: DF.Currency
		total_outstanding: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_same_currency()
		self.validate_overdue_payments()
		self.validate_totals()
		self.set_party_details()
		self.set_dunning_level()

	def validate_same_currency(self):
		"""
		Throw an error if invoice currency differs from dunning currency.
		"""
		for row in self.overdue_payments:
			invoice_currency = frappe.get_value("Sales Invoice", row.sales_invoice, "currency")
			if invoice_currency != self.currency:
				frappe.throw(
					_(
						"The currency of invoice {} ({}) is different from the currency of this dunning ({})."
					).format(
						frappe.get_desk_link(
							"Sales Invoice",
							row.sales_invoice,
						),
						invoice_currency,
						self.currency,
					)
				)

	def validate_overdue_payments(self):
		daily_interest = self.rate_of_interest / 100 / 365

		for row in self.overdue_payments:
			row.overdue_days = (getdate(self.posting_date) - getdate(row.due_date)).days or 0
			row.interest = row.outstanding * daily_interest * row.overdue_days

	def validate_totals(self):
		self.total_outstanding = sum(row.outstanding for row in self.overdue_payments)
		self.total_interest = sum(row.interest for row in self.overdue_payments)
		self.dunning_amount = self.total_interest + self.dunning_fee
		self.base_dunning_amount = self.dunning_amount * self.conversion_rate
		self.grand_total = self.total_outstanding + self.dunning_amount

	def set_party_details(self):
		from erpnext.accounts.party import _get_party_details

		party_details = _get_party_details(
			self.customer,
			ignore_permissions=self.flags.ignore_permissions,
			doctype=self.doctype,
			company=self.company,
			posting_date=self.get("posting_date"),
			fetch_payment_terms_template=False,
			party_address=self.customer_address,
			company_address=self.get("company_address"),
		)
		for field in [
			"customer_address",
			"address_display",
			"company_address",
			"contact_person",
			"contact_display",
			"contact_mobile",
		]:
			self.set(field, party_details.get(field))

		self.set("company_address_display", get_address_display(self.company_address))

	def set_dunning_level(self):
		for row in self.overdue_payments:
			past_dunnings = frappe.get_all(
				"Overdue Payment",
				filters={
					"payment_schedule": row.payment_schedule,
					"parent": ("!=", row.parent),
					"docstatus": 1,
				},
			)
			row.dunning_level = len(past_dunnings) + 1

	def on_cancel(self):
		super().on_cancel()
		self.ignore_linked_doctypes = [
			"GL Entry",
			"Stock Ledger Entry",
			"Repost Item Valuation",
			"Repost Payment Ledger",
			"Repost Payment Ledger Items",
			"Repost Accounting Ledger",
			"Repost Accounting Ledger Items",
			"Unreconcile Payment",
			"Unreconcile Payment Entries",
			"Payment Ledger Entry",
			"Serial and Batch Bundle",
		]


def update_linked_dunnings(doc, previous_outstanding_amount):
	if (
		doc.doctype != "Sales Invoice"
		or doc.is_return
		or previous_outstanding_amount == doc.outstanding_amount
	):
		return

	to_resolve = doc.outstanding_amount < previous_outstanding_amount
	state = "Unresolved" if to_resolve else "Resolved"
	dunnings = get_linked_dunnings_as_per_state(doc.name, state)
	if not dunnings:
		return

	dunnings = [frappe.get_doc("Dunning", dunning.name) for dunning in dunnings]
	invoices = set()
	payment_schedule_ids = set()

	for dunning in dunnings:
		for overdue_payment in dunning.overdue_payments:
			invoices.add(overdue_payment.sales_invoice)
			if overdue_payment.payment_schedule:
				payment_schedule_ids.add(overdue_payment.payment_schedule)

	invoice_outstanding_amounts = dict(
		frappe.get_all(
			"Sales Invoice",
			filters={"name": ["in", list(invoices)]},
			fields=["name", "outstanding_amount"],
			as_list=True,
		)
	)

	ps_outstanding_amounts = (
		dict(
			frappe.get_all(
				"Payment Schedule",
				filters={"name": ["in", list(payment_schedule_ids)]},
				fields=["name", "outstanding"],
				as_list=True,
			)
		)
		if payment_schedule_ids
		else {}
	)

	for dunning in dunnings:
		has_outstanding = False
		for overdue_payment in dunning.overdue_payments:
			invoice_outstanding = invoice_outstanding_amounts[overdue_payment.sales_invoice]
			ps_outstanding = ps_outstanding_amounts.get(overdue_payment.payment_schedule, 0)
			has_outstanding = invoice_outstanding > 0 and ps_outstanding > 0
			if has_outstanding:
				break

		new_status = "Resolved" if not has_outstanding else "Unresolved"

		if dunning.status != new_status:
			dunning.status = new_status
			dunning.save()


def get_linked_dunnings_as_per_state(sales_invoice, state):
	dunning = frappe.qb.DocType("Dunning")
	overdue_payment = frappe.qb.DocType("Overdue Payment")

	return (
		frappe.qb.from_(dunning)
		.join(overdue_payment)
		.on(overdue_payment.parent == dunning.name)
		.select(dunning.name)
		.where(
			(dunning.status == state)
			& (dunning.docstatus != 2)
			& (overdue_payment.sales_invoice == sales_invoice)
		)
	).run(as_dict=True)


@frappe.whitelist()
def get_dunning_letter_text(dunning_type: str, doc: str | dict, language: str | None = None) -> dict:
	DOCTYPE = "Dunning Letter Text"
	FIELDS = ["body_text", "closing_text", "language"]

	if isinstance(doc, str):
		doc = json.loads(doc)

	if not language:
		language = doc.get("language")

	letter_text = None
	if language:
		letter_text = frappe.db.get_value(
			DOCTYPE, {"parent": dunning_type, "language": language}, FIELDS, as_dict=1
		)

	if not letter_text:
		letter_text = frappe.db.get_value(
			DOCTYPE, {"parent": dunning_type, "is_default_language": 1}, FIELDS, as_dict=1
		)

	if not letter_text:
		return {}

	return {
		"body_text": frappe.render_template(letter_text.body_text, doc),
		"closing_text": frappe.render_template(letter_text.closing_text, doc),
		"language": letter_text.language,
	}
