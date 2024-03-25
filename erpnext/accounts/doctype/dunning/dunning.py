# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe.utils import cint, flt, getdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.controllers.accounts_controller import AccountsController


class Dunning(AccountsController):
<<<<<<< HEAD
=======
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

>>>>>>> e055147849 (fix: address_display, text -> text editor (#40621))
	def validate(self):
		self.validate_overdue_days()
		self.validate_amount()
		if not self.income_account:
			self.income_account = frappe.db.get_value("Company", self.company, "default_income_account")

	def validate_overdue_days(self):
		self.overdue_days = (getdate(self.posting_date) - getdate(self.due_date)).days or 0

	def validate_amount(self):
		amounts = calculate_interest_and_amount(
			self.outstanding_amount, self.rate_of_interest, self.dunning_fee, self.overdue_days
		)
		if self.interest_amount != amounts.get("interest_amount"):
			self.interest_amount = flt(amounts.get("interest_amount"), self.precision("interest_amount"))
		if self.dunning_amount != amounts.get("dunning_amount"):
			self.dunning_amount = flt(amounts.get("dunning_amount"), self.precision("dunning_amount"))
		if self.grand_total != amounts.get("grand_total"):
			self.grand_total = flt(amounts.get("grand_total"), self.precision("grand_total"))

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		if self.dunning_amount:
			self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
			make_reverse_gl_entries(voucher_type=self.doctype, voucher_no=self.name)

	def make_gl_entries(self):
		if not self.dunning_amount:
			return
		gl_entries = []
		invoice_fields = [
			"project",
			"cost_center",
			"debit_to",
			"party_account_currency",
			"conversion_rate",
			"cost_center",
		]
		inv = frappe.db.get_value("Sales Invoice", self.sales_invoice, invoice_fields, as_dict=1)

		accounting_dimensions = get_accounting_dimensions()
		invoice_fields.extend(accounting_dimensions)

		dunning_in_company_currency = flt(self.dunning_amount * inv.conversion_rate)
		default_cost_center = frappe.get_cached_value("Company", self.company, "cost_center")

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": inv.debit_to,
					"party_type": "Customer",
					"party": self.customer,
					"due_date": self.due_date,
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


def resolve_dunning(doc, state):
	for reference in doc.references:
		if reference.reference_doctype == "Sales Invoice" and reference.outstanding_amount <= 0:
			dunnings = frappe.get_list(
				"Dunning",
				filters={"sales_invoice": reference.reference_name, "status": ("!=", "Resolved")},
				ignore_permissions=True,
			)

			for dunning in dunnings:
				frappe.db.set_value("Dunning", dunning.name, "status", "Resolved")


def calculate_interest_and_amount(outstanding_amount, rate_of_interest, dunning_fee, overdue_days):
	interest_amount = 0
	grand_total = flt(outstanding_amount) + flt(dunning_fee)
	if rate_of_interest:
		interest_per_year = flt(outstanding_amount) * flt(rate_of_interest) / 100
		interest_amount = (interest_per_year * cint(overdue_days)) / 365
		grand_total += flt(interest_amount)
	dunning_amount = flt(interest_amount) + flt(dunning_fee)
	return {
		"interest_amount": interest_amount,
		"grand_total": grand_total,
		"dunning_amount": dunning_amount,
	}


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
