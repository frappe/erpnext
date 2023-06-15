# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""
# Accounting

1. Payment of outstanding invoices with dunning amount

		- Debit full amount to bank
		- Credit invoiced amount to receivables
		- Credit dunning amount to interest and similar revenue

		-> Resolves dunning automatically
"""
from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import getdate

from erpnext.controllers.accounts_controller import AccountsController


class Dunning(AccountsController):
	def validate(self):
		self.validate_same_currency()
		self.validate_overdue_payments()
		self.validate_totals()
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


def resolve_dunning(doc, state):
	"""
	Check if all payments have been made and resolve dunning, if yes. Called
	when a Payment Entry is submitted.
	"""
	for reference in doc.references:
		# Consider partial and full payments
		if (
			reference.reference_doctype == "Sales Invoice"
			and reference.outstanding_amount < reference.total_amount
		):
			unresolved_dunnings = get_unresolved_dunnings(reference.reference_name)

			for dunning_name in unresolved_dunnings:
				resolve = True
				dunning = frappe.get_doc("Dunning", dunning_name)
				for overdue_payment in dunning.overdue_payments:
					outstanding_inv = frappe.get_value(
						"Sales Invoice", overdue_payment.sales_invoice, "outstanding_amount"
					)
					outstanding_ps = frappe.get_value(
						"Payment Schedule", overdue_payment.payment_schedule, "outstanding"
					)
					if outstanding_ps > 0 and outstanding_inv > 0:
						resolve = False

				if resolve:
					dunning.status = "Resolved"
					dunning.save()


def get_unresolved_dunnings(sales_invoice):
	dunning = frappe.qb.DocType("Dunning")
	overdue_payment = frappe.qb.DocType("Overdue Payment")

	return (
		frappe.qb.from_(dunning)
		.join(overdue_payment)
		.on(overdue_payment.parent == dunning.name)
		.select(dunning.name)
		.where(
			(dunning.status != "Resolved")
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
