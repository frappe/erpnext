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

		address_display: DF.SmallText | None
		amended_from: DF.Link | None
		base_dunning_amount: DF.Currency
		body_text: DF.TextEditor | None
		closing_text: DF.TextEditor | None
		company: DF.Link
		company_address: DF.Link | None
		company_address_display: DF.SmallText | None
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
					).format(row.sales_invoice, invoice_currency, self.currency)
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


def resolve_dunning(doc, state):
	"""
	Check if all payments have been made and resolve dunning, if yes. Called
	when a Payment Entry is submitted.
	"""
	for reference in doc.references:
		# Consider partial and full payments:
		# Submitting full payment: outstanding_amount will be 0
		# Submitting 1st partial payment: outstanding_amount will be the pending installment
		# Cancelling full payment: outstanding_amount will revert to total amount
		# Cancelling last partial payment: outstanding_amount will revert to pending amount
		submit_condition = reference.outstanding_amount < reference.total_amount
		cancel_condition = reference.outstanding_amount <= reference.total_amount

		if reference.reference_doctype == "Sales Invoice" and (
			submit_condition if doc.docstatus == 1 else cancel_condition
		):
			state = "Resolved" if doc.docstatus == 2 else "Unresolved"
			dunnings = get_linked_dunnings_as_per_state(reference.reference_name, state)

			for dunning in dunnings:
				resolve = True
				dunning = frappe.get_doc("Dunning", dunning.get("name"))
				for overdue_payment in dunning.overdue_payments:
					outstanding_inv = frappe.get_value(
						"Sales Invoice", overdue_payment.sales_invoice, "outstanding_amount"
					)
					outstanding_ps = frappe.get_value(
						"Payment Schedule", overdue_payment.payment_schedule, "outstanding"
					)
					resolve = False if (outstanding_ps > 0 and outstanding_inv > 0) else True

				dunning.status = "Resolved" if resolve else "Unresolved"
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
