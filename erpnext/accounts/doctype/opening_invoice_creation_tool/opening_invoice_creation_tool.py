# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_years
from erpnext.accounts.general_ledger import make_gl_entries

class OpeningInvoiceCreationTool(Document):
	def onload(self):
		"""Load the Opening Invoice Summery"""
		summery, max_count = self.get_opening_invoice_summery()
		self.set_onload('opening_invoices_summery', summery)
		self.set_onload('max_count', max_count)

	def get_opening_invoice_summery(self):
		def prepare_invoice_summery(doctype, invoices):
			# add company wise sales / purchase invoice summery
			paid_amount = []
			outstanding_amount = []
			for invoice in invoices:
				company = invoice.pop("company")
				_summery = invoices_summery.get(company, {})
				_summery.update({
					"currency": company_wise_currency.get(company),
					doctype: invoice
				})
				invoices_summery.update({company: _summery})

				paid_amount.append(invoice.paid_amount)
				outstanding_amount.append(invoice.outstanding_amount)

			if paid_amount or outstanding_amount:
				max_count.update({
					doctype: {
						"max_paid": max(paid_amount) if paid_amount else 0.0,
						"max_due": max(outstanding_amount) if outstanding_amount else 0.0
					}
				})

		invoices_summery = {}
		max_count = {}
		fields = [
			"company", "count(name) as total_invoices", "sum(outstanding_amount) as outstanding_amount",
			 "sum(base_grand_total) - sum(outstanding_amount) as paid_amount"
		]
		companies = frappe.get_all("Company", fields=["name as company", "default_currency as currency"])
		if not companies:
			return None, None

		company_wise_currency = {row.company: row.currency for row in companies}
		for doctype in ["Sales Invoice", "Purchase Invoice"]:
			invoices = frappe.get_all(doctype, filters=dict(is_opening="Yes", docstatus=1),
				fields=fields, group_by="company")
			prepare_invoice_summery(doctype, invoices)

		return invoices_summery, max_count

	def make_invoices(self):
		names = []
		mandatory_error_msg = _("Row {idx}: {field} is required to create the Opening {invoice_type} Invoices")
		if not self.company:
			frappe.throw(_("Please select the Company"))

		for row in self.invoices:
			if not row.party:
				frappe.throw(mandatory_error_msg.format(
					idx=row.idx,
					field="Party",
					invoice_type=self.invoice_type
				))
			# set party type if not available
			if not row.party_type:
				row.party_type = "Customer" if self.invoice_type == "Sales" else "Supplier"

			if not row.posting_date:
				frappe.throw(mandatory_error_msg.format(
					idx=row.idx,
					field="Party",
					invoice_type=self.invoice_type
				))

			args = self.get_invoice_dict(row=row)
			if not args:
				continue

			doc = frappe.get_doc(args).insert()
			doc.submit()
			names.append(doc.name)

			# create GL entries
			if doc.base_grand_total:
				self.make_gl_entries(doc, party_type=row.party_type, party=row.party,
					outstanding_amount=flt(row.outstanding_amount))

			if(len(self.invoices) > 5):
				frappe.publish_realtime("progress",
					dict(progress=[row.idx, len(self.invoices)], title=_('Creating {0}').format(doc.doctype)),
					user=frappe.session.user)

		return names

	def get_invoice_dict(self, row=None):
		def get_item_dict():
			default_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or _("Nos")
			cost_center = frappe.db.get_value("Company", self.company, "cost_center")
			if not cost_center:
				frappe.throw(_("Please set the Default Cost Center in {0} company").format(frappe.bold(self.company)))
			rate = flt(row.net_total) / (flt(row.qty) or 1.0)

			return frappe._dict({
				"uom": default_uom,
				"rate": rate or 0.0,
				"qty": flt(row.qty) or 1.0,
				"conversion_factor": 1.0,
				"item_name": row.item_name or "Opening Item",
				"description": row.item_name or "Opening Item",
				income_expense_account_field: self.get_account(),
				"cost_center": cost_center
			})

		if not row:
			return None

		party_type = "Customer"
		income_expense_account_field = "income_account"
		if self.invoice_type == "Purchase":
			party_type = "Supplier"
			income_expense_account_field = "expense_account"

		item = get_item_dict()
		return frappe._dict({
			"items": [item],
			"is_opening": "Yes",
			"set_posting_time": 1,
			"company": self.company,
			"due_date": row.due_date,
			"posting_date": row.posting_date,
			frappe.scrub(party_type): row.party,
			"doctype": "Sales Invoice" if self.invoice_type == "Sales" \
				else "Purchase Invoice",
			"currency": frappe.db.get_value("Company", self.company, "default_currency")
		})

	def get_account(self):
		accounts = frappe.get_all("Account", filters={
			'company': self.company,
			'account_type': 'Temporary'
		})
		if not accounts:
			frappe.throw(_("Please add the Temporary Opening account in Chart of Accounts"))

		return accounts[0].name

	def make_gl_entries(self, doc, party_type, party, outstanding_amount=0.0):
		""" Make payment GL Entries for the invoices """
		if not doc:
			return

		gl_entries = []
		args = {
			'posting_date': doc.posting_date,
			'voucher_type': doc.doctype,
			'voucher_no': doc.name
		}
		gl_dict = self.get_gl_dict(doc.posting_date, args)

		# gl entry for party
		dr_or_cr = "credit" if party_type == "Customer" else "debit"
		amount = doc.grand_total - outstanding_amount
		amount_in_account_currency = flt(amount * doc.conversion_rate or 1.0)
		gle = gl_dict.copy()
		gle.update({
			"party": party,
			"party_type": party_type,
			"against": self.get_account(),
			"against_voucher": doc.name,
			"against_voucher_type": doc.doctype,
			dr_or_cr: amount_in_account_currency,
			dr_or_cr + "_in_account_currency": amount_in_account_currency,
			"account": doc.debit_to if doc.doctype == "Sales Invoice" else doc.credit_to
		})
		gl_entries.append(gle)

		dr_or_cr = "debit" if party_type == "Customer" else "credit"
		gle = gl_dict.copy()
		gle.update({
			"against": party,
			"account": self.get_account(),
			dr_or_cr: amount_in_account_currency,
			dr_or_cr + "_in_account_currency": amount_in_account_currency
		})
		gl_entries.append(gle)

		make_gl_entries(gl_entries)

	def get_gl_dict(self, posting_date, args):
		fiscal_years = get_fiscal_years(posting_date, company=self.company)
		if len(fiscal_years) > 1:
			frappe.throw(_("Multiple fiscal years exist for the date {0}. Please set company in Fiscal Year").format(formatdate(self.posting_date)))
		else:
			fiscal_year = fiscal_years[0][0]

		gl_dict = frappe._dict({
			'fiscal_year': fiscal_year,
			'company': self.company,
			'remarks': "No Remarks",
			'debit': 0,
			'credit': 0,
			'debit_in_account_currency': 0,
			'credit_in_account_currency': 0,
			'is_opening': "Yes",
			'party_type': None,
			'party': None
		})
		gl_dict.update(args)
		return gl_dict