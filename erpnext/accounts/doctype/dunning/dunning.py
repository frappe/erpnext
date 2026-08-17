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
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate

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
						"The currency of invoice {0} ({1}) is different from the currency of this dunning ({2})."
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

	def get_unpaid_base_dunning_amount(self):
		"""Interest and dunning fee that is still to be collected, in company currency."""
		if not self.base_dunning_amount:
			return 0.0

		return flt(
			flt(self.base_dunning_amount) - get_paid_dunning_amount(self.name),
			self.precision("base_dunning_amount"),
		)

	def get_unpaid_dunning_amount(self):
		"""Interest and dunning fee that is still to be collected, in the dunning currency."""
		return flt(
			self.get_unpaid_base_dunning_amount() / (flt(self.conversion_rate) or 1),
			self.precision("dunning_amount"),
		)

	def get_unpaid_overdue_payments(self):
		"""Overdue payments with their outstanding as of now, not as of dunning creation."""
		return [
			(row, outstanding)
			for row in self.overdue_payments
			if (outstanding := get_current_outstanding(row)) > 0
		]

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
			"Payment Entry",
		]

	@frappe.whitelist()
	def get_dunning_letter_text(self):
		DOCTYPE = "Dunning Letter Text"
		FIELDS = ["body_text", "closing_text", "language"]

		if not self.dunning_type:
			return

		filters = {"parent": self.dunning_type, "is_default_language": 1}

		if self.language:
			filters.pop("is_default_language")
			filters["language"] = self.language

		letter_text = frappe.db.get_value(DOCTYPE, filters, FIELDS, as_dict=True)

		if not letter_text:
			msg = (
				_("Dunning Letter for Dunning Type {0} in language '{1}' not found.").format(
					frappe.bold(self.dunning_type), frappe.bold(self.language)
				)
				if self.language
				else _("Dunning Letter for Dunning Type {0} not found.").format(
					frappe.bold(self.dunning_type)
				)
			)
			frappe.msgprint(msg, alert=True, indicator="yellow")

		self.body_text = (
			frappe.render_template(letter_text.body_text, self.as_dict(), restrict_globals=True)
			if letter_text
			else None
		)
		self.closing_text = (
			frappe.render_template(letter_text.closing_text, self.as_dict(), restrict_globals=True)
			if letter_text
			else None
		)
		self.language = letter_text.language if letter_text else self.language


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

		set_dunning_status(dunning, has_outstanding, respect_manual_resolution=True)


def update_dunnings_linked_to_payment(payment_entry):
	"""Refresh dunnings whose interest and fee are settled by this payment."""
	dunnings = {row.dunning for row in payment_entry.get("deductions") if row.dunning}

	for name in dunnings:
		dunning = frappe.get_doc("Dunning", name)
		if dunning.docstatus != 1:
			continue

		set_dunning_status(dunning, bool(dunning.get_unpaid_overdue_payments()))


def set_dunning_status(dunning, has_outstanding_payments: bool, respect_manual_resolution: bool = False):
	"""A dunning is only resolved once the invoiced sum *and* its interest and fee are paid."""
	has_unpaid_dunning_amount = dunning.get_unpaid_dunning_amount() > 0
	new_status = "Unresolved" if has_outstanding_payments or has_unpaid_dunning_amount else "Resolved"

	# resolving by hand waives the interest, only an invoice that is owed again reopens it
	if respect_manual_resolution and dunning.status == "Resolved" and not has_outstanding_payments:
		return

	if dunning.status != new_status:
		dunning.status = new_status
		dunning.flags.ignore_permissions = True
		dunning.save()


def get_paid_dunning_amount(dunning: str) -> float:
	"""Interest and fee collected for this dunning, in company currency."""
	deduction = frappe.qb.DocType("Payment Entry Deduction")
	payment_entry = frappe.qb.DocType("Payment Entry")

	paid = (
		frappe.qb.from_(deduction)
		.join(payment_entry)
		.on(payment_entry.name == deduction.parent)
		.select(Sum(deduction.amount))
		.where((deduction.dunning == dunning) & (payment_entry.docstatus == 1))
	).run()

	# the dunning amount is booked as a negative deduction, against the income account
	return -flt(paid[0][0]) if paid else 0.0


def get_current_outstanding(overdue_payment) -> float:
	"""Outstanding of an overdue payment as of now, in the invoice's transaction currency."""
	invoice = frappe.db.get_value(
		"Sales Invoice",
		overdue_payment.sales_invoice,
		["outstanding_amount", "currency", "party_account_currency"],
		as_dict=True,
	)
	schedule_outstanding = (
		flt(frappe.db.get_value("Payment Schedule", overdue_payment.payment_schedule, "outstanding"))
		if overdue_payment.payment_schedule
		else flt(overdue_payment.outstanding)
	)

	if flt(invoice.outstanding_amount) <= 0 or schedule_outstanding <= 0:
		return 0.0

	outstanding = min(schedule_outstanding, flt(overdue_payment.outstanding))
	if invoice.currency == invoice.party_account_currency:
		outstanding = min(outstanding, flt(invoice.outstanding_amount))

	return outstanding


def get_linked_dunnings_as_per_state(sales_invoice, state):
	dunning = frappe.qb.DocType("Dunning")
	overdue_payment = frappe.qb.DocType("Overdue Payment")

	return (
		frappe.qb.from_(dunning)
		.join(overdue_payment)
		.on(overdue_payment.parent == dunning.name)
		.select(dunning.name)
		.distinct()
		.where(
			(dunning.status == state)
			& (dunning.docstatus != 2)
			& (overdue_payment.sales_invoice == sales_invoice)
		)
	).run(as_dict=True)
