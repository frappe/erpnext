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

	def compose(self):
		doc = self.doc
		gl_map = []

		company_currency = erpnext.get_company_currency(doc.company)
		doc.transaction_currency = company_currency
		doc.transaction_exchange_rate = 1
		if doc.multi_currency:
			for row in doc.get("accounts"):
				if row.account_currency != company_currency:
					# Journal assumes the first foreign currency as transaction currency
					doc.transaction_currency = row.account_currency
					doc.transaction_exchange_rate = row.exchange_rate
					break

		advance_doctypes = get_advance_payment_doctypes()

		for d in doc.get("accounts"):
			if d.debit or d.credit or (doc.voucher_type == "Exchange Gain Or Loss"):
				r = [d.user_remark, doc.remark]
				r = [x for x in r if x]
				remarks = "\n".join(r)

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

				gl_map.append(
					self.get_gl_dict(
						row,
						item=d,
					)
				)
		return gl_map
