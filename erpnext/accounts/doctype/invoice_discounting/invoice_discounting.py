# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import flt, getdate, nowdate
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.general_ledger import make_gl_entries

class InvoiceDiscounting(AccountsController):
	def validate(self):
		self.validate_mandatory()
		self.calculate_total_amount()
		self.set_status()

	def validate_mandatory(self):
		if self.docstatus == 1 and not (self.loan_start_date and self.loan_period):
			frappe.throw(_("Loan Start Date and Loan Period are mandatory to submit the Invoice Discounting"))

	def calculate_total_amount(self):
		self.total_amount = sum([flt(d.outstanding_amount) for d in self.invoices])

	def on_submit(self):
		self.make_gl_entries()

	def on_cancel(self):
		self.set_status()
		self.make_gl_entries()

	def set_status(self):
		self.status = "Draft"
		if self.docstatus == 1:
			self.status = "Sanctioned"
		elif self.docstatus == 2:
			self.status = "Cancelled"

	def make_gl_entries(self):
		company_currency = frappe.get_cached_value('Company',  self.company, "default_currency")

		gl_entries = []
		for d in self.invoices:
			inv = frappe.db.get_value("Sales Invoice", d.sales_invoice,
				["debit_to", "party_account_currency", "conversion_rate", "cost_center"], as_dict=1)

			if d.outstanding_amount:
				outstanding_in_company_currency = flt(d.outstanding_amount * inv.conversion_rate,
					d.precision("outstanding_amount"))
				ar_credit_account_currency = frappe.get_cached_value("Account", self.accounts_receivable_credit, "currency")

				gl_entries.append(self.get_gl_dict({
					"account": inv.debit_to,
					"party_type": "Customer",
					"party": d.customer,
					"against": self.accounts_receivable_credit,
					"credit": outstanding_in_company_currency,
					"credit_in_account_currency": outstanding_in_company_currency \
						if inv.party_account_currency==company_currency else d.outstanding_amount,
					"cost_center": inv.cost_center,
					"against_voucher": d.sales_invoice,
					"against_voucher_type": "Sales Invoice"
				}, inv.party_account_currency))

				gl_entries.append(self.get_gl_dict({
					"account": self.accounts_receivable_credit,
					"party_type": "Customer",
					"party": d.customer,
					"against": inv.debit_to,
					"debit": outstanding_in_company_currency,
					"debit_in_account_currency": outstanding_in_company_currency \
						if ar_credit_account_currency==company_currency else d.outstanding_amount,
					"cost_center": inv.cost_center,
					"against_voucher": d.sales_invoice,
					"against_voucher_type": "Sales Invoice"
				}, ar_credit_account_currency))

		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding='No')

	def create_disbursement_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = 'Journal Entry'
		je.company = self.company
		je.remark = 'Loan Disbursement entry against Invoice Discounting: ' + self.name

		je.append("accounts", {
			"account": self.bank_account,
			"debit_in_account_currency": flt(self.total_amount) - flt(self.bank_charges),
		})

		je.append("accounts", {
			"account": self.bank_charges_account,
			"debit_in_account_currency": flt(self.bank_charges)
		})

		je.append("accounts", {
			"account": self.short_term_loan,
			"credit_in_account_currency": flt(self.total_amount),
			"reference_type": "Invoice Discounting",
			"reference_name": self.name
		})

		for d in self.invoices:
			je.append("accounts", {
				"account": self.accounts_receivable_discounted,
				"debit_in_account_currency": flt(d.outstanding_amount),
				"reference_type": "Invoice Discounting",
				"reference_name": self.name,
				"party_type": "Customer",
				"party": d.customer
			})

			je.append("accounts", {
				"account": self.accounts_receivable_credit,
				"credit_in_account_currency": flt(d.outstanding_amount),
				"reference_type": "Invoice Discounting",
				"reference_name": self.name,
				"party_type": "Customer",
				"party": d.customer
			})

		return je.as_dict()

	def close_loan(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = 'Journal Entry'
		je.company = self.company
		je.remark = 'Loan Settlement entry against Invoice Discounting: ' + self.name

		je.append("accounts", {
			"account": self.short_term_loan,
			"debit_in_account_currency": flt(self.total_amount),
			"reference_type": "Invoice Discounting",
			"reference_name": self.name,
		})

		je.append("accounts", {
			"account": self.bank_account,
			"credit_in_account_currency": flt(self.total_amount)
		})

		if getdate(self.loan_end_date) > getdate(nowdate()):
			for d in self.invoices:
				je.append("accounts", {
					"account": self.accounts_receivable_discounted,
					"credit_in_account_currency": flt(d.outstanding_amount),
					"reference_type": "Invoice Discounting",
					"reference_name": self.name,
					"party_type": "Customer",
					"party": d.customer
				})

				je.append("accounts", {
					"account": self.accounts_receivable_unpaid,
					"debit_in_account_currency": flt(d.outstanding_amount),
					"reference_type": "Invoice Discounting",
					"reference_name": self.name,
					"party_type": "Customer",
					"party": d.customer
				})

		return je.as_dict()

@frappe.whitelist()
def get_invoices(filters):
	filters = frappe._dict(json.loads(filters))
	cond = []
	if filters.customer:
		cond.append("customer=%(customer)s")
	if filters.from_date:
		cond.append("posting_date >= %(from_date)s")
	if filters.to_date:
		cond.append("posting_date <= %(to_date)s")
	if filters.min_amount:
		cond.append("base_grand_total >= %(min_amount)s")
	if filters.max_amount:
		cond.append("base_grand_total <= %(max_amount)s")

	where_condition = ""
	if cond:
		where_condition += " and " + " and ".join(cond)

	return frappe.db.sql("""
		select
			name as sales_invoice,
			customer,
			posting_date,
			outstanding_amount
		from `tabSales Invoice`
		where
			docstatus = 1
			and outstanding_amount > 0
			%s
	""" % where_condition, filters, as_dict=1)