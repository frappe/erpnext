# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, cint, cstr
from frappe import _
from frappe.model.document import Document
from erpnext.setup.utils import get_exchange_rate
from erpnext import get_company_currency
from erpnext.stock.get_item_details import get_item_tax_map
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_accounting_dimensions
from six import string_types
import json


class ExpenseEntry(Document):
	def validate(self):
		self.check_duplicate_bill_no()
		self.validate_accounts()
		self.validate_total_amount()
		self.set_missing_values()
		self.calculate_taxes()
		self.calculate_totals()

	def before_submit(self):
		self.set_missing_bill_dates()

	def on_submit(self):
		self.make_journal_entries()

	def on_cancel(self):
		self.cancel_journal_entries()

	def check_duplicate_bill_no(self):
		unique_bill_no_party = []

		for d in self.accounts:
			if d.bill_no and d.supplier:
				key = (d.bill_no, d.supplier)
				if key in unique_bill_no_party:
					frappe.throw(_("Row {0}: Bill No {1} for Supplier {2} is a duplicate").format(d.idx, d.bill_no, d.supplier))
				else:
					unique_bill_no_party.append(key)

				exp_entrty_with_duplicate = has_duplicate_bill_no(d.bill_no, d.supplier)
				if exp_entrty_with_duplicate:
					frappe.throw(_("Row {0}: Bill No {1} for Supplier {2} already exists in {3}").format(
						d.idx, d.bill_no, d.supplier, ", ".join(exp_entrty_with_duplicate)))

	def validate_accounts(self):
		if self.payable_account and frappe.get_cached_value("Account", self.payable_account, "account_type") != 'Payable':
			frappe.throw(_("Incorrect Account Type for Payable Account {0}").format(self.payable_account))
		if self.paid_from_account and frappe.get_cached_value("Account", self.paid_from_account, "account_type") not in ['Bank', 'Cash', 'Equity']:
			frappe.throw(_("Incorrect Account Type for Paid From Account {0}").format(self.paid_from_account))

		for d in self.accounts:
			if d.supplier and not self.payable_account:
				frappe.throw(_("Row {0}: Payable Account is mandatory if supplier is provided").format(d.idx))
			if not d.supplier and not self.paid_from_account:
				frappe.throw(_("Row {0}: Paid From Account is mandatory if supplier is not provided").format(d.idx))

	def validate_total_amount(self):
		for d in self.accounts:
			if not d.total_amount:
				frappe.throw(_("Row #{0}: Total Amount cannot be 0").format(d.idx))

	def set_missing_values(self):
		company_currency = get_company_currency(self.company)
		self.payable_account_currency = frappe.get_cached_value("Account", self.payable_account, "account_currency") \
			if self.payable_account else company_currency

		for d in self.accounts:
			if self.payable_account_currency == company_currency:
				d.exchange_rate = 1.0
			elif not d.exchange_rate or d.exchange_rate == 1.0:
				d.exchange_rate = get_exchange_rate(self.payable_account_currency, company_currency, d.bill_date or self.transaction_date)
				if not d.exchange_rate:
					frappe.throw(_("Could not find Exchange Rate from {0} to {1} on {2}").format(
						self.payable_account_currency, company_currency, d.bill_date or self.transaction_date))

	def set_missing_bill_dates(self):
		for d in self.accounts:
			if not d.bill_date:
				d.bill_date = self.transaction_date

	def calculate_taxes(self):
		for d in self.accounts:
			d.tax_rate = get_item_tax_map(self.company, d.item_tax_template)
			tax_map = json.loads(d.tax_rate or '{}')
			tax_amount = 0
			for tax_account, tax_rate in tax_map.items():
				if tax_rate:
					tax_amount += flt(d.total_amount) - flt(d.total_amount) / (1 + flt(tax_rate) / 100)

			d.tax_amount = flt(tax_amount, d.precision("tax_amount"))

	def calculate_totals(self):
		for d in self.accounts:
			d.total_amount = flt(d.total_amount, d.precision('total_amount'))
			d.base_total_amount = flt(flt(d.total_amount) * flt(d.exchange_rate), d.precision('base_total_amount'))

			d.tax_amount = flt(d.tax_amount, d.precision('tax_amount'))
			d.base_tax_amount = flt(flt(d.tax_amount) * flt(d.exchange_rate), d.precision('base_tax_amount'))

			d.expense_amount = flt(flt(d.total_amount) - flt(d.tax_amount), d.precision('expense_amount'))
			d.base_expense_amount = flt(flt(d.base_total_amount) - flt(d.base_tax_amount), d.precision('base_expense_amount'))

		total_fields = [
			['total', 'total_amount'],
			['total_tax_amount', 'tax_amount'],
			['total_expense_amount', 'expense_amount'],
		]
		for target_f, source_f in total_fields:
			self.set(target_f, flt(sum([d.get(source_f) for d in self.accounts]), self.precision(target_f)))
			self.set("base_" + target_f, flt(sum([d.get("base_" + source_f) for d in self.accounts]), self.precision("base_" + target_f)))

	def make_journal_entries(self):
		for d in self.accounts:
			bill_jv = None
			if d.supplier:
				bill_jv = self.make_bill_journal_entry(d)
			if self.paid_from_account:
				self.make_payment_journal_entry(d, bill_jv)

	def make_bill_journal_entry(self, d):
		company_currency = get_company_currency(self.company)
		multi_currency = 1 if self.payable_account_currency != company_currency else 0

		doc = self.get_journal_entry(d, multi_currency, self.journal_entry_series)
		self.append_expense_entry(doc, d)
		self.append_tax_entry(doc, d)
		self.append_supplier_credit_entry(doc, d)

		doc.insert()
		doc.submit()
		return doc

	def make_payment_journal_entry(self, d, bill_jv):
		company_currency = get_company_currency(self.company)
		paid_from_account_currency = frappe.get_cached_value("Account", self.paid_from_account, "account_currency")
		multi_currency = 1 if paid_from_account_currency != company_currency else 0

		payment_account_type = frappe.get_cached_value("Account", self.paid_from_account, "account_type")
		naming_series = None
		if payment_account_type == "Bank":
			naming_series = self.bank_entry_series
		elif payment_account_type == "Cash":
			naming_series = self.cash_entry_series

		doc = self.get_journal_entry(d, multi_currency, naming_series=naming_series)

		if bill_jv:
			self.append_supplier_debit_entry(doc, d, bill_jv)
		else:
			self.append_expense_entry(doc, d)
			self.append_tax_entry(doc, d)

		self.append_payment_entry(doc, d)

		doc.insert()
		doc.submit()
		return doc

	def get_journal_entry(self, d, multi_currency, naming_series=None):
		doc = frappe.new_doc("Journal Entry")
		doc.update({
			"expense_entry_name": self.name,
			"company": self.company,
			"posting_date": d.bill_date or self.transaction_date,
			"bill_no": d.bill_no or self.name,
			"bill_date": d.bill_date or self.transaction_date,
			"cheque_no": d.bill_no or self.name,
			"cheque_date": d.bill_date or self.transaction_date,
			"multi_currency": multi_currency,
			"user_remark": d.remarks
		})

		if naming_series:
			doc.naming_series = naming_series

		self.set_accounting_dimensions(self, doc)

		return doc

	def append_expense_entry(self, doc, d):
		expense_account_currency = frappe.get_cached_value("Account", d.expense_account, "account_currency")
		row = doc.append("accounts", {
			"account": d.expense_account,
			"account_currency": expense_account_currency,
			"debit_in_account_currency": d.expense_amount if self.payable_account_currency == expense_account_currency
				else d.base_expense_amount,
			"debit": d.base_expense_amount,
			"exchange_rate": d.base_expense_amount/d.expense_amount if self.payable_account_currency == expense_account_currency else 1.0,
			"cost_center": d.cost_center,
			"project": d.project
		})

		self.set_accounting_dimensions(d, row)

	def append_tax_entry(self, doc, d):
		if not d.tax_amount:
			return

		tax_map = json.loads(d.tax_rate or '{}')
		tax_map = {acc: rate for (acc, rate) in tax_map.items() if rate}
		remaining_tax_amount = d.tax_amount

		for i, (tax_account, tax_rate) in enumerate(tax_map.items()):
			if i == len(tax_map) - 1:
				tax_amount = flt(remaining_tax_amount, d.precision('tax_amount'))
			else:
				tax_amount = flt(flt(d.total_amount) - flt(d.total_amount) / (1 + flt(tax_rate) / 100), d.precision('tax_amount'))

			tax_account_currency = frappe.get_cached_value("Account", tax_account, "account_currency")
			if tax_amount:
				row = doc.append("accounts", {
					"account": tax_account,
					"account_currency": tax_account_currency,
					"debit_in_account_currency": tax_amount if self.payable_account_currency == tax_account_currency
						else d.base_tax_amount,
					"debit": d.base_tax_amount,
					"exchange_rate": d.exchange_rate if self.payable_account_currency == tax_account_currency else 1.0,
					"cost_center": d.cost_center,
					"project": d.project
				})

				self.set_accounting_dimensions(d, row)

	def append_supplier_credit_entry(self, doc, d):
		row = doc.append("accounts", {
			"account": self.payable_account,
			"account_currency": self.payable_account_currency,
			"party_type": "Supplier",
			"party": d.supplier,
			"credit_in_account_currency": flt(d.total_amount),
			"credit": flt(d.base_total_amount),
			"exchange_rate": d.exchange_rate,
			"cost_center": d.cost_center,
			"project": d.project
		})

		self.set_accounting_dimensions(d, row)

	def append_supplier_debit_entry(self, doc, d, bill_jv):
		row = doc.append("accounts", {
			"account": self.payable_account,
			"account_currency": self.payable_account_currency,
			"party_type": "Supplier",
			"party": d.supplier,
			"debit_in_account_currency": flt(d.total_amount),
			"debit": flt(d.base_total_amount),
			"exchange_rate": d.exchange_rate,
			"cost_center": d.cost_center,
			"project": d.project,
			"reference_type": "Journal Entry",
			"reference_name": bill_jv.name
		})

		self.set_accounting_dimensions(d, row)

	def append_payment_entry(self, doc, d):
		paid_from_account_currency = frappe.get_cached_value("Account", self.paid_from_account, "account_currency")
		row = doc.append("accounts", {
			"account": self.paid_from_account,
			"account_currency": paid_from_account_currency,
			"credit_in_account_currency": d.total_amount if self.payable_account_currency == paid_from_account_currency
				else d.base_total_amount,
			"credit": d.base_total_amount,
			"exchange_rate": d.exchange_rate if self.payable_account_currency == paid_from_account_currency else 1.0,
			"cost_center": d.cost_center,
			"project": d.project
		})

		self.set_accounting_dimensions(d, row)

	def set_accounting_dimensions(self, source, target):
		if not hasattr(self, 'acccounting_dimensions'):
			self.accounting_dimensions = get_accounting_dimensions()
			self.accounting_dimensions += ['cost_center', 'project']
			self.accounting_dimensions = list(set(self.accounting_dimensions))

		for dimension in self.accounting_dimensions:
			target.set(dimension, source.get(dimension))

	def cancel_journal_entries(self):
		je_names = [d.name for d in frappe.get_all("Journal Entry", fields=['name', 'docstatus'],
			filters={"expense_entry_name": self.name, "docstatus": 1})]

		cancel_later = []
		for name in je_names:
			doc = frappe.get_doc("Journal Entry", name)
			for d in doc.accounts:
				if d.reference_type == "Journal Entry" and d.reference_name in je_names:
					doc.cancel()
					break

			if doc.docstatus == 1:
				cancel_later.append(doc)

		for doc in cancel_later:
			doc.cancel()



@frappe.whitelist()
def has_duplicate_bill_no(bill_no, supplier):
	data = frappe.db.sql_list("""
		select distinct expd.parent
		from `tabExpense Entry Detail` as expd
		where expd.bill_no=%s and expd.supplier=%s and expd.docstatus=1
	""", (bill_no, supplier))

	return data


@frappe.whitelist()
def get_default_expense_account(supplier):
	return frappe.get_cached_value("Supplier", supplier, "expense_account")


@frappe.whitelist()
def get_exchange_rates(bill_dates, from_currency, to_currency):
	if isinstance(bill_dates, string_types):
		bill_dates = json.loads(bill_dates)

	bill_dates = set(bill_dates)
	out = {}
	for date in bill_dates:
		out[date] = get_exchange_rate(from_currency, to_currency, date)

	return out
