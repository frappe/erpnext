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

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController


class Dunning(AccountsController):
	def onload(self):
		gl_entries_exist = frappe.db.exists(
			"GL Entry", {"voucher_no": self.name, "voucher_type": "Dunning"}
		)
		self.set_onload("gl_entries_exist", gl_entries_exist)

	def validate(self):
		self.validate_same_currency()
		self.validate_overdue_payments()
		self.validate_totals()
		self.set_party_details()
		self.set_dunning_level()

		if not self.income_account:
			self.income_account = frappe.db.get_value("Company", self.company, "default_income_account")

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

			customer = frappe.db.get_value("Sales Invoice", row.sales_invoice, "customer")
			if customer != self.customer:
				frappe.throw(
					title=_("Customer mismatch"),
					msg=_(
						"Row #{0}: The customer of {} ({}) is different from the customer of this dunning ({})."
					).format(
						row.idx, row.sales_invoice, frappe.bold(customer), frappe.bold(self.customer)
					),
				)

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

	def on_submit(self):
		post_gl_entries = not frappe.db.get_single_value(
			"Accounts Settings", "dunning_fees_as_additonal_income"
		)
		if post_gl_entries and self.dunning_amount:
			self.make_gl_entries()

	def on_cancel(self):
		gl_entries_exist = frappe.db.exists(
			"GL Entry", {"voucher_no": self.name, "voucher_type": "Dunning", "is_cancelled": 0}
		)
		if self.dunning_amount and gl_entries_exist:
			self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def make_gl_entries(self):
		gl_entries = []
		invoice_fields = self.get_invoice_fields()
		inv_name = self.overdue_payments[0].sales_invoice
		inv = frappe.db.get_value("Sales Invoice", inv_name, invoice_fields, as_dict=1)

		dunning_in_company_currency = frappe.utils.flt(self.dunning_amount * inv.conversion_rate)
		default_cost_center = frappe.get_cached_value("Company", self.company, "cost_center")
		due_date = max([row.due_date for row in self.overdue_payments])

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": inv.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": due_date,
					"against": self.income_account,
					"debit": dunning_in_company_currency,
					"debit_in_account_currency": self.dunning_amount,
					"against_voucher": self.name,
					"against_voucher_type": "Dunning",
					"cost_center": inv.cost_center or default_cost_center,
					"project": inv.project,
				},
				inv.party_account_currency,
				item=inv,
			)
		)
		gl_entries.append(
			self.get_gl_dict(
				{
					"account": self.income_account,
					"against": self.customer,
					"credit": dunning_in_company_currency,
					"cost_center": inv.cost_center or default_cost_center,
					"credit_in_account_currency": self.dunning_amount,
					"project": inv.project,
				},
				item=inv,
			)
		)

		make_gl_entries(
			gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False
		)

	def get_invoice_fields(self):
		"""Return fields to query from Sales Invoice."""
		invoice_fields = [
			"project",
			"cost_center",
			"debit_to",
			"party_account_currency",
			"conversion_rate",
			"cost_center",
		]
		accounting_dimensions = get_accounting_dimensions()
		invoice_fields.extend(accounting_dimensions)
		return invoice_fields


def resolve_dunning(doc, state):
	"""
	Check if all payments have been made and resolve dunning, if yes. Called
	when a Payment Entry is submitted.
	"""
	dunnings_to_resolve = set()
	for reference in doc.references:
		# Consider these values *AFTER* submission of Payment Entry:
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
			[dunnings_to_resolve.add(entry.get("name")) for entry in dunnings]

	payments_resolved = []
	for dunning_name in dunnings_to_resolve:
		# Dunning is resolved if all rows are paid
		dunning = frappe.get_doc("Dunning", dunning_name)
		payments_resolved = list(map(lambda row: is_row_resolved(row), dunning.overdue_payments))
		dunning.status = "Resolved" if all(payments_resolved) else "Unresolved"
		dunning.save()


def is_row_resolved(row):
	"""
	Return True if the row is resolved, else False.
	"""
	outstanding_inv = frappe.get_value("Sales Invoice", row.sales_invoice, "outstanding_amount")
	outstanding_ps_amount = frappe.get_value("Payment Schedule", row.payment_schedule, "outstanding")

	# If no payment term (full payment), only consider invoice outstanding amount [True and x = x]
	outstanding_in_ps = (outstanding_ps_amount > 0) if row.payment_term else True
	return False if (outstanding_in_ps and outstanding_inv > 0) else True


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
def get_dunning_letter_text(dunning_type, doc, language=None):
	if isinstance(doc, str):
		doc = json.loads(doc)
	if language:
		filters = {"parent": dunning_type, "language": language}
	else:
		filters = {"parent": dunning_type, "is_default_language": 1}
	letter_text = frappe.db.get_value(
		"Dunning Letter Text", filters, ["body_text", "closing_text", "language"], as_dict=1
	)
	if letter_text:
		return {
			"body_text": frappe.render_template(letter_text.body_text, doc),
			"closing_text": frappe.render_template(letter_text.closing_text, doc),
			"language": letter_text.language,
		}
