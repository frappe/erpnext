# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_years
from erpnext.accounts.general_ledger import make_gl_entries

class OpeningInvoiceCreationTool(Document):
	def validate(self):
		self.make_invoices()

	def make_invoices(self):
		for row in self.invoices:
			args = self.get_invoice_dict(row=row)
			if not args:
				continue

			doc = frappe.get_doc(args).insert()
			doc.submit()

			self.make_gl_entries(doc, party_type=row.party_type, party=row.party,
				outstanding_amount=row.outstanding_amount or 0.0)

			if(len(self.invoices) > 5):
				frappe.publish_realtime("progress",
					dict(progress=[row.idx, len(self.invoices)], title=_('Creating {0}').format(doc.doctype)),
					user=frappe.session.user)

	def get_invoice_dict(self, row=None):
		def get_item_dict():
			default_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or _("Nos")

			return frappe._dict({
				"uom": default_uom,
				"conversion_factor": 1.0,
				"qty": row.qty or 1.0,
				"rate": row.net_total or 0.0,
				"item_name": row.item_name or "Opening Item",
				"description": row.item_name or "Opening Item",
				income_expense_account_field: self.get_account()
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
			"company": self.company,
			"due_date": row.posting_date,
			"posting_date": row.posting_date,
			frappe.scrub(party_type): row.party,
			"doctype": "Sales Invoice" if self.invoice_type == "Sales" \
				else "Purchase Invoice"
		})

	def get_account(self):
		accounts = frappe.get_all("Account", filters={'account_type': 'Temporary'})
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
		gle = gl_dict.copy()
		gle.update({
			"party": party,
			"party_type": party_type,
			"against": self.get_account(),
			"against_voucher": doc.name,
			"against_voucher_type": doc.doctype,
			dr_or_cr: doc.base_grand_total - outstanding_amount,
			dr_or_cr + "_in_account_currency": doc.grand_total - outstanding_amount,
			"account": doc.debit_to if doc.doctype == "Sales Invoice" else doc.credit_to
		})
		gl_entries.append(gle)

		dr_or_cr = "debit" if party_type == "Customer" else "credit"
		gle = gl_dict.copy()
		gle.update({
			"against": party,
			"account": self.get_account(),
			dr_or_cr: doc.base_grand_total - outstanding_amount,
			dr_or_cr + "_in_account_currency": doc.grand_total - outstanding_amount
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

	def get_gl_entries(self):
		gl_entries.append(
			self.get_gl_dict(doc.posting_date, {
				"account": self.debit_to,
				"party_type": "Customer",
				"party": self.customer,
				"against": self.against_income_account,
				"debit": grand_total_in_company_currency,
				"debit_in_account_currency": grand_total_in_company_currency \
					if self.party_account_currency==self.company_currency else self.grand_total,
				"against_voucher": self.return_against if cint(self.is_return) else self.name,
				"against_voucher_type": self.doctype
			}, self.party_account_currency)
		)