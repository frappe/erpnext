# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt

import erpnext
from erpnext.accounts.services.base_gl_composer import BaseGLComposer
from erpnext.accounts.utils import get_advance_payment_doctypes


class JournalEntryGLComposer(BaseGLComposer):
	"""Assembles the GL entries for a Journal Entry.

	A Journal Entry already carries its ledger rows in the ``accounts`` child
	table, so composing is a straight projection of those rows into GL dicts
	via ``self.get_gl_dict``. The transaction currency/rate are resolved
	from the first foreign-currency row (mirroring the former build_gl_map).
	"""

	def compose(self) -> list:
		"""Project the Journal Entry's non-zero account rows into GL dicts."""
		self._set_transaction_currency()
		advance_doctypes = get_advance_payment_doctypes()

		gl_map = []
		for d in self.doc.get("accounts"):
			if d.debit or d.credit or self.doc.voucher_type == "Exchange Gain Or Loss":
				gl_map.append(self.get_gl_dict(self._gl_row(d, advance_doctypes), item=d))
		return gl_map

	def _set_transaction_currency(self) -> None:
		"""Company currency, or the first foreign-currency row, becomes the transaction currency."""
		doc = self.doc
		doc.transaction_currency = erpnext.get_company_currency(doc.company)
		doc.transaction_exchange_rate = 1
		if not doc.multi_currency:
			return

		for row in doc.get("accounts"):
			if row.account_currency != doc.transaction_currency:
				# Journal assumes the first foreign currency as transaction currency
				doc.transaction_currency = row.account_currency
				doc.transaction_exchange_rate = row.exchange_rate
				break

	def _gl_row(self, d, advance_doctypes: list) -> dict:
		"""Build the GL dict for a single account row."""
		doc = self.doc
		remarks = "\n".join(x for x in [d.user_remark, doc.remark] if x)

		row = {
			"account": d.account,
			"party_type": d.party_type,
			"due_date": doc.due_date,
			"party": d.party,
			"against": d.against_account,
			"debit": flt(d.debit, d.precision("debit")),
			"credit": flt(d.credit, d.precision("credit")),
			"account_currency": d.account_currency,
			"debit_in_account_currency": flt(
				d.debit_in_account_currency, d.precision("debit_in_account_currency")
			),
			"credit_in_account_currency": flt(
				d.credit_in_account_currency, d.precision("credit_in_account_currency")
			),
			"transaction_currency": doc.transaction_currency,
			"transaction_exchange_rate": doc.transaction_exchange_rate,
			"debit_in_transaction_currency": flt(
				d.debit_in_account_currency, d.precision("debit_in_account_currency")
			)
			if doc.transaction_currency == d.account_currency
			else flt(d.debit, d.precision("debit")) / doc.transaction_exchange_rate,
			"credit_in_transaction_currency": flt(
				d.credit_in_account_currency, d.precision("credit_in_account_currency")
			)
			if doc.transaction_currency == d.account_currency
			else flt(d.credit, d.precision("credit")) / doc.transaction_exchange_rate,
			"against_voucher_type": d.reference_type,
			"against_voucher": d.reference_name,
			"remarks": remarks,
			"voucher_detail_no": d.reference_detail_no,
			"cost_center": d.cost_center,
			"project": d.project,
			"finance_book": doc.finance_book,
			"advance_voucher_type": d.advance_voucher_type,
			"advance_voucher_no": d.advance_voucher_no,
		}

		if d.reference_type in advance_doctypes:
			row.update(
				{
					"against_voucher_type": doc.doctype,
					"against_voucher": doc.name,
					"advance_voucher_type": d.reference_type,
					"advance_voucher_no": d.reference_name,
				}
			)

		# set flag to skip party validation
		account_type = frappe.get_cached_value("Account", d.account, "account_type")
		if account_type in ["Receivable", "Payable"] and doc.party_not_required:
			frappe.flags.party_not_required = True

		return row
