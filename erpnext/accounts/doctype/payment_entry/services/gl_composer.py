# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.services.base_gl_composer import BaseGLComposer
from erpnext.accounts.utils import get_account_currency, get_advance_payment_doctypes


class PaymentEntryGLComposer(BaseGLComposer):
	"""Assembles the GL entries for a Payment Entry.

	The voucher-specific row builders live here and operate on ``self.doc``.
	Shared helpers (get_gl_dict, calculate_base_allocated_amount_for_reference,
	get_exchange_rate, get_party_account_for_taxes) remain on the document for
	now and are invoked via ``self.doc``. The advance-posting builders stay on
	the document; they post separately from this compose pass and move with the
	advances service in a later phase.
	"""

	def compose(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import add_regional_gl_entries

		doc = self.doc
		if doc.payment_type in ("Receive", "Pay") and not doc.get("party_account_field"):
			doc.setup_party_account_field()
		doc.set_transaction_currency_and_rate()

		gl_entries = []
		self.add_party_gl_entries(gl_entries)
		self.add_bank_gl_entries(gl_entries)
		self.add_deductions_gl_entries(gl_entries)
		self.add_tax_gl_entries(gl_entries)
		add_regional_gl_entries(gl_entries, doc)
		return gl_entries

	def add_party_gl_entries(self, gl_entries):
		doc = self.doc
		if not doc.party_account:
			return

		advance_payment_doctypes = get_advance_payment_doctypes()
		if doc.payment_type == "Receive":
			against_account = doc.paid_to
		else:
			against_account = doc.paid_from

		party_account_type = frappe.db.get_value("Party Type", doc.party_type, "account_type")

		party_gl_dict = self.get_gl_dict(
			{
				"account": doc.party_account,
				"party_type": doc.party_type,
				"party": doc.party,
				"against": against_account,
				"account_currency": doc.party_account_currency,
				"cost_center": doc.cost_center,
			},
			item=doc,
		)

		for d in doc.get("references"):
			# re-defining dr_or_cr for every reference in order to avoid the last value affecting calculation of reverse
			dr_or_cr = "credit" if doc.payment_type == "Receive" else "debit"
			cost_center = doc.cost_center
			if d.reference_doctype == "Sales Invoice" and not cost_center:
				cost_center = frappe.db.get_value(d.reference_doctype, d.reference_name, "cost_center")

			gle = party_gl_dict.copy()

			allocated_amount_in_company_currency = doc.calculate_base_allocated_amount_for_reference(d)

			if (
				d.reference_doctype in ["Sales Invoice", "Purchase Invoice"]
				and d.allocated_amount < 0
				and (
					(party_account_type == "Receivable" and doc.payment_type == "Pay")
					or (party_account_type == "Payable" and doc.payment_type == "Receive")
				)
			):
				# reversing dr_cr because because it will get reversed in gl processing due to negative amount
				dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

			gle.update(
				self.get_gl_dict(
					{
						"account": doc.party_account,
						"party_type": doc.party_type,
						"party": doc.party,
						"against": against_account,
						"account_currency": doc.party_account_currency,
						"cost_center": cost_center,
						dr_or_cr + "_in_account_currency": d.allocated_amount,
						dr_or_cr: allocated_amount_in_company_currency,
						dr_or_cr + "_in_transaction_currency": d.allocated_amount
						if doc.transaction_currency == doc.party_account_currency
						else allocated_amount_in_company_currency / doc.transaction_exchange_rate,
						"advance_voucher_type": d.advance_voucher_type,
						"advance_voucher_no": d.advance_voucher_no,
						"transaction_exchange_rate": doc.target_exchange_rate,
					},
					item=doc,
				)
			)

			if d.reference_doctype in advance_payment_doctypes:
				# advance reference
				gle.update(
					{
						"against_voucher_type": doc.doctype,
						"against_voucher": doc.name,
						"advance_voucher_type": d.reference_doctype,
						"advance_voucher_no": d.reference_name,
					}
				)

			elif doc.book_advance_payments_in_separate_party_account:
				# Do not reference Invoices while Advance is in separate party account
				gle.update({"against_voucher_type": doc.doctype, "against_voucher": doc.name})
			else:
				gle.update(
					{
						"against_voucher_type": d.reference_doctype,
						"against_voucher": d.reference_name,
					}
				)

			gl_entries.append(gle)

		if doc.unallocated_amount:
			dr_or_cr = "credit" if doc.payment_type == "Receive" else "debit"
			exchange_rate = doc.get_exchange_rate()
			base_unallocated_amount = doc.unallocated_amount * exchange_rate

			gle = party_gl_dict.copy()

			gle.update(
				self.get_gl_dict(
					{
						"account": doc.party_account,
						"party_type": doc.party_type,
						"party": doc.party,
						"against": against_account,
						"account_currency": doc.party_account_currency,
						"cost_center": doc.cost_center,
						dr_or_cr + "_in_account_currency": doc.unallocated_amount,
						dr_or_cr + "_in_transaction_currency": doc.unallocated_amount
						if doc.party_account_currency == doc.transaction_currency
						else base_unallocated_amount / doc.transaction_exchange_rate,
						dr_or_cr: base_unallocated_amount,
					},
					item=doc,
				)
			)
			if doc.book_advance_payments_in_separate_party_account:
				gle.update(
					{
						"against_voucher_type": "Payment Entry",
						"against_voucher": doc.name,
					}
				)
			gl_entries.append(gle)

	def add_bank_gl_entries(self, gl_entries):
		doc = self.doc
		if doc.payment_type in ("Pay", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.paid_from,
						"account_currency": doc.paid_from_account_currency,
						"against": doc.party if doc.payment_type == "Pay" else doc.paid_to,
						"credit_in_account_currency": doc.paid_amount,
						"credit_in_transaction_currency": doc.paid_amount
						if doc.paid_from_account_currency == doc.transaction_currency
						else doc.base_paid_amount / doc.transaction_exchange_rate,
						"credit": doc.base_paid_amount,
						"cost_center": doc.cost_center,
						"post_net_value": True,
					},
					item=doc,
				)
			)
		if doc.payment_type in ("Receive", "Internal Transfer"):
			gl_entries.append(
				self.get_gl_dict(
					{
						"account": doc.paid_to,
						"account_currency": doc.paid_to_account_currency,
						"against": doc.party if doc.payment_type == "Receive" else doc.paid_from,
						"debit_in_account_currency": doc.received_amount,
						"debit_in_transaction_currency": doc.received_amount
						if doc.paid_to_account_currency == doc.transaction_currency
						else doc.base_received_amount / doc.transaction_exchange_rate,
						"debit": doc.base_received_amount,
						"cost_center": doc.cost_center,
					},
					item=doc,
				)
			)

	def add_tax_gl_entries(self, gl_entries):
		doc = self.doc
		for d in doc.get("taxes"):
			account_currency = get_account_currency(d.account_head)
			if account_currency != doc.company_currency:
				frappe.throw(_("Currency for {0} must be {1}").format(d.account_head, doc.company_currency))

			if doc.payment_type in ("Pay", "Internal Transfer"):
				dr_or_cr = "debit" if d.add_deduct_tax == "Add" else "credit"
				rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
				against = doc.party or doc.paid_from
			elif doc.payment_type == "Receive":
				dr_or_cr = "credit" if d.add_deduct_tax == "Add" else "debit"
				rev_dr_or_cr = "credit" if dr_or_cr == "debit" else "debit"
				against = doc.party or doc.paid_to

			payment_account = doc.get_party_account_for_taxes()
			tax_amount = d.tax_amount
			base_tax_amount = d.base_tax_amount

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": d.account_head,
						"against": against,
						dr_or_cr: tax_amount,
						dr_or_cr + "_in_account_currency": base_tax_amount
						if account_currency == doc.company_currency
						else d.tax_amount,
						dr_or_cr + "_in_transaction_currency": base_tax_amount
						/ doc.transaction_exchange_rate,
						"cost_center": d.cost_center,
						"post_net_value": True,
					},
					account_currency,
					item=d,
				)
			)

			if not d.included_in_paid_amount:
				if get_account_currency(payment_account) != doc.company_currency:
					if doc.payment_type == "Receive":
						exchange_rate = doc.target_exchange_rate
					elif doc.payment_type in ["Pay", "Internal Transfer"]:
						exchange_rate = doc.source_exchange_rate
					base_tax_amount = flt((tax_amount / exchange_rate), doc.precision("paid_amount"))

				gl_entries.append(
					self.get_gl_dict(
						{
							"account": payment_account,
							"against": against,
							rev_dr_or_cr: tax_amount,
							rev_dr_or_cr + "_in_account_currency": base_tax_amount
							if account_currency == doc.company_currency
							else d.tax_amount,
							rev_dr_or_cr + "_in_transaction_currency": base_tax_amount
							/ doc.transaction_exchange_rate,
							"cost_center": doc.cost_center,
							"post_net_value": True,
						},
						account_currency,
						item=d,
					)
				)

	def add_deductions_gl_entries(self, gl_entries):
		doc = self.doc
		for d in doc.get("deductions"):
			if not d.amount:
				continue

			account_currency = get_account_currency(d.account)
			if account_currency != doc.company_currency:
				frappe.throw(_("Currency for {0} must be {1}").format(d.account, doc.company_currency))

			gl_entries.append(
				self.get_gl_dict(
					{
						"account": d.account,
						"account_currency": account_currency,
						"against": doc.party or doc.paid_from,
						"debit_in_account_currency": d.amount,
						"debit_in_transaction_currency": d.amount / doc.transaction_exchange_rate,
						"debit": d.amount,
						"cost_center": d.cost_center,
					},
					item=d,
				)
			)
