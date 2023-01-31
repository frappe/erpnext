# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.controllers.accounts_controller import AccountsController


class InvoiceDiscounting(AccountsController):
	def validate(self):
		self.validate_mandatory()
		self.validate_invoices()
		self.calculate_total_amount()
		self.set_status()
		self.set_end_date()

	def set_end_date(self):
		if self.loan_start_date and self.loan_period:
			self.loan_end_date = add_days(self.loan_start_date, self.loan_period)

	def validate_mandatory(self):
		if self.docstatus == 1 and not (self.loan_start_date and self.loan_period):
			frappe.throw(_("Loan Start Date and Loan Period are mandatory to save the Invoice Discounting"))

	def validate_invoices(self):
		discounted_invoices = [
			record.sales_invoice
			for record in frappe.get_all(
				"Discounted Invoice", fields=["sales_invoice"], filters={"docstatus": 1}
			)
		]

		for record in self.invoices:
			if record.sales_invoice in discounted_invoices:
				frappe.throw(
					_("Row({0}): {1} is already discounted in {2}").format(
						record.idx, frappe.bold(record.sales_invoice), frappe.bold(record.parent)
					)
				)

			actual_outstanding = frappe.db.get_value(
				"Sales Invoice", record.sales_invoice, "outstanding_amount"
			)
			if record.outstanding_amount > actual_outstanding:
				frappe.throw(
					_(
						"Row({0}): Outstanding Amount cannot be greater than actual Outstanding Amount {1} in {2}"
					).format(
						record.idx, frappe.bold(actual_outstanding), frappe.bold(record.sales_invoice)
					)
				)

	def calculate_total_amount(self):
		self.total_amount = sum(flt(d.outstanding_amount) for d in self.invoices)

	def on_submit(self):
		self.update_sales_invoice()
		self.make_gl_entries()

	def on_cancel(self):
		self.set_status(cancel=1)
		self.update_sales_invoice()
		self.make_gl_entries()

	def set_status(self, status=None, cancel=0):
		if status:
			self.status = status
			self.db_set("status", status)
			for d in self.invoices:
				frappe.get_doc("Sales Invoice", d.sales_invoice).set_status(update=True, update_modified=False)
		else:
			self.status = "Draft"
			if self.docstatus == 1:
				self.status = "Sanctioned"
			elif self.docstatus == 2:
				self.status = "Cancelled"

		if cancel:
			self.db_set("status", self.status, update_modified=True)

	def update_sales_invoice(self):
		for d in self.invoices:
			if self.docstatus == 1:
				is_discounted = 1
			else:
				discounted_invoice = frappe.db.exists(
					{"doctype": "Discounted Invoice", "sales_invoice": d.sales_invoice, "docstatus": 1}
				)
				is_discounted = 1 if discounted_invoice else 0
			frappe.db.set_value("Sales Invoice", d.sales_invoice, "is_discounted", is_discounted)

	def make_gl_entries(self):
		company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

		gl_entries = []
		invoice_fields = ["debit_to", "party_account_currency", "conversion_rate", "cost_center"]
		accounting_dimensions = get_accounting_dimensions()

		invoice_fields.extend(accounting_dimensions)

		for d in self.invoices:
			inv = frappe.db.get_value("Sales Invoice", d.sales_invoice, invoice_fields, as_dict=1)

			if d.outstanding_amount:
				outstanding_in_company_currency = flt(
					d.outstanding_amount * inv.conversion_rate, d.precision("outstanding_amount")
				)
				ar_credit_account_currency = frappe.get_cached_value(
					"Account", self.accounts_receivable_credit, "currency"
				)

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": inv.debit_to,
							"party_type": "Customer",
							"party": d.customer,
							"against": self.accounts_receivable_credit,
							"credit": outstanding_in_company_currency,
							"credit_in_account_currency": outstanding_in_company_currency
							if inv.party_account_currency == company_currency
							else d.outstanding_amount,
							"cost_center": inv.cost_center,
							"against_voucher": d.sales_invoice,
							"against_voucher_type": "Sales Invoice",
						},
						inv.party_account_currency,
						item=inv,
					)
				)

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": self.accounts_receivable_credit,
							"party_type": "Customer",
							"party": d.customer,
							"against": inv.debit_to,
							"debit": outstanding_in_company_currency,
							"debit_in_account_currency": outstanding_in_company_currency
							if ar_credit_account_currency == company_currency
							else d.outstanding_amount,
							"cost_center": inv.cost_center,
							"against_voucher": d.sales_invoice,
							"against_voucher_type": "Sales Invoice",
						},
						ar_credit_account_currency,
						item=inv,
					)
				)

		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No")

	@frappe.whitelist()
	def create_disbursement_entry(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.remark = "Loan Disbursement entry against Invoice Discounting: " + self.name

		je.append(
			"accounts",
			{
				"account": self.bank_account,
				"debit_in_account_currency": flt(self.total_amount) - flt(self.bank_charges),
				"cost_center": erpnext.get_default_cost_center(self.company),
			},
		)

		if self.bank_charges:
			je.append(
				"accounts",
				{
					"account": self.bank_charges_account,
					"debit_in_account_currency": flt(self.bank_charges),
					"cost_center": erpnext.get_default_cost_center(self.company),
				},
			)

		je.append(
			"accounts",
			{
				"account": self.short_term_loan,
				"credit_in_account_currency": flt(self.total_amount),
				"cost_center": erpnext.get_default_cost_center(self.company),
				"reference_type": "Invoice Discounting",
				"reference_name": self.name,
			},
		)
		for d in self.invoices:
			je.append(
				"accounts",
				{
					"account": self.accounts_receivable_discounted,
					"debit_in_account_currency": flt(d.outstanding_amount),
					"cost_center": erpnext.get_default_cost_center(self.company),
					"reference_type": "Invoice Discounting",
					"reference_name": self.name,
					"party_type": "Customer",
					"party": d.customer,
				},
			)

			je.append(
				"accounts",
				{
					"account": self.accounts_receivable_credit,
					"credit_in_account_currency": flt(d.outstanding_amount),
					"cost_center": erpnext.get_default_cost_center(self.company),
					"reference_type": "Invoice Discounting",
					"reference_name": self.name,
					"party_type": "Customer",
					"party": d.customer,
				},
			)

		return je

	@frappe.whitelist()
	def close_loan(self):
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.company = self.company
		je.remark = "Loan Settlement entry against Invoice Discounting: " + self.name

		je.append(
			"accounts",
			{
				"account": self.short_term_loan,
				"debit_in_account_currency": flt(self.total_amount),
				"cost_center": erpnext.get_default_cost_center(self.company),
				"reference_type": "Invoice Discounting",
				"reference_name": self.name,
			},
		)

		je.append(
			"accounts",
			{
				"account": self.bank_account,
				"credit_in_account_currency": flt(self.total_amount),
				"cost_center": erpnext.get_default_cost_center(self.company),
			},
		)

		if getdate(self.loan_end_date) > getdate(nowdate()):
			for d in self.invoices:
				outstanding_amount = frappe.db.get_value(
					"Sales Invoice", d.sales_invoice, "outstanding_amount"
				)
				if flt(outstanding_amount) > 0:
					je.append(
						"accounts",
						{
							"account": self.accounts_receivable_discounted,
							"credit_in_account_currency": flt(outstanding_amount),
							"cost_center": erpnext.get_default_cost_center(self.company),
							"reference_type": "Invoice Discounting",
							"reference_name": self.name,
							"party_type": "Customer",
							"party": d.customer,
						},
					)

					je.append(
						"accounts",
						{
							"account": self.accounts_receivable_unpaid,
							"debit_in_account_currency": flt(outstanding_amount),
							"cost_center": erpnext.get_default_cost_center(self.company),
							"reference_type": "Invoice Discounting",
							"reference_name": self.name,
							"party_type": "Customer",
							"party": d.customer,
						},
					)

		return je


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

	return frappe.db.sql(
		"""
		select
			name as sales_invoice,
			customer,
			posting_date,
			outstanding_amount,
			debit_to
		from `tabSales Invoice` si
		where
			docstatus = 1
			and outstanding_amount > 0
			%s
			and not exists(select di.name from `tabDiscounted Invoice` di
				where di.docstatus=1 and di.sales_invoice=si.name)
	"""
		% where_condition,
		filters,
		as_dict=1,
	)


def get_party_account_based_on_invoice_discounting(sales_invoice):
	party_account = None
	invoice_discounting = frappe.db.sql(
		"""
		select par.accounts_receivable_discounted, par.accounts_receivable_unpaid, par.status
		from `tabInvoice Discounting` par, `tabDiscounted Invoice` ch
		where par.name=ch.parent
			and par.docstatus=1
			and ch.sales_invoice = %s
	""",
		(sales_invoice),
		as_dict=1,
	)
	if invoice_discounting:
		if invoice_discounting[0].status == "Disbursed":
			party_account = invoice_discounting[0].accounts_receivable_discounted
		elif invoice_discounting[0].status == "Settled":
			party_account = invoice_discounting[0].accounts_receivable_unpaid

	return party_account
