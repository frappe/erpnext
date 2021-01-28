# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.controllers.status_updater import StatusUpdater
from frappe.utils import flt
from six.moves import reduce
from frappe import _
from frappe.model.mapper import get_mapped_doc

class BankTransaction(StatusUpdater):
	def after_insert(self):
		self.unallocated_amount = abs(flt(self.credit) - flt(self.debit))

	def on_submit(self):
		self.clear_linked_payment_entries()
		self.set_status()

	def on_update_after_submit(self):
		self.update_allocations()
		self.clear_linked_payment_entries()
		self.set_status(update=True)

	def update_allocations(self):
		if self.payment_entries:
			allocated_amount = reduce(lambda x, y: flt(x) + flt(y), [x.allocated_amount for x in self.payment_entries])
		else:
			allocated_amount = 0

		if allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", flt(allocated_amount))
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)) - flt(allocated_amount))

		else:
			frappe.db.set_value(self.doctype, self.name, "allocated_amount", 0)
			frappe.db.set_value(self.doctype, self.name, "unallocated_amount", abs(flt(self.credit) - flt(self.debit)))

		amount = self.debit or self.credit
		if amount == self.allocated_amount:
			frappe.db.set_value(self.doctype, self.name, "status", "Reconciled")

		self.reload()

	def clear_linked_payment_entries(self):
		for payment_entry in self.payment_entries:
			allocated_amount = get_total_allocated_amount(payment_entry)
			paid_amount = get_paid_amount(payment_entry, self.currency)

			if paid_amount and allocated_amount:
				if  flt(allocated_amount[0]["allocated_amount"]) > flt(paid_amount):
					frappe.throw(_("The total allocated amount ({0}) is greated than the paid amount ({1}).").format(flt(allocated_amount[0]["allocated_amount"]), flt(paid_amount)))
				else:
					if payment_entry.payment_document in ["Payment Entry", "Journal Entry", "Purchase Invoice", "Expense Claim"]:
						self.clear_simple_entry(payment_entry)

					elif payment_entry.payment_document == "Sales Invoice":
						self.clear_sales_invoice(payment_entry)

	def clear_simple_entry(self, payment_entry):
		frappe.db.set_value(payment_entry.payment_document, payment_entry.payment_entry, "clearance_date", self.date)

	def clear_sales_invoice(self, payment_entry):
		frappe.db.set_value("Sales Invoice Payment", dict(parenttype=payment_entry.payment_document,
			parent=payment_entry.payment_entry), "clearance_date", self.date)

def get_total_allocated_amount(payment_entry):
	return frappe.db.sql("""
		SELECT
			SUM(btp.allocated_amount) as allocated_amount,
			bt.name
		FROM
			`tabBank Transaction Payments` as btp
		LEFT JOIN
			`tabBank Transaction` bt ON bt.name=btp.parent
		WHERE
			btp.payment_document = %s
		AND
			btp.payment_entry = %s
		AND
			bt.docstatus = 1""", (payment_entry.payment_document, payment_entry.payment_entry), as_dict=True)

def get_paid_amount(payment_entry, currency):
	if payment_entry.payment_document in ["Payment Entry", "Sales Invoice", "Purchase Invoice"]:

		paid_amount_field = "paid_amount"
		if payment_entry.payment_document == 'Payment Entry':
			doc = frappe.get_doc("Payment Entry", payment_entry.payment_entry)
			paid_amount_field = ("base_paid_amount"
				if doc.paid_to_account_currency == currency else "paid_amount")

		return frappe.db.get_value(payment_entry.payment_document,
			payment_entry.payment_entry, paid_amount_field)

	elif payment_entry.payment_document == "Journal Entry":
		return frappe.db.get_value(payment_entry.payment_document, payment_entry.payment_entry, "total_credit")

	elif payment_entry.payment_document == "Expense Claim":
		return frappe.db.get_value(payment_entry.payment_document, payment_entry.payment_entry, "total_amount_reimbursed")

	else:
		frappe.throw("Please reconcile {0}: {1} manually".format(payment_entry.payment_document, payment_entry.payment_entry))

@frappe.whitelist()
def unclear_reference_payment(doctype, docname):
	if frappe.db.exists(doctype, docname):
		doc = frappe.get_doc(doctype, docname)
		if doctype == "Sales Invoice":
			frappe.db.set_value("Sales Invoice Payment", dict(parenttype=doc.payment_document,
				parent=doc.payment_entry), "clearance_date", None)
		else:
			frappe.db.set_value(doc.payment_document, doc.payment_entry, "clearance_date", None)

		return doc.payment_entry

@frappe.whitelist()
def make_journal_entry(source_name, target_doc=None,
	opposite_account=None, party={'type': None, 'name': None}, reference={'type': None, 'name': None}):

	doc = get_mapped_doc('Bank Transaction', source_name, {
		'Bank Transaction': {
			'doctype': 'Journal Entry',
			# From Bank Transaction -> Journal Entry
			'field_map': {
				"company": "company",
				"date": "cheque_date",
				"transaction_id": "cheque_no",
				"description": "user_remark"
			},
			'field_no_map': ['accounts'],
			'validation': {
				'docstatus': ['=', 1]
			}
		}
	}, target_doc)
	doc.voucher_type = 'Bank Entry'

	bank_trans = frappe.get_cached_doc('Bank Transaction', source_name)
	bank_ac = frappe.get_value('Bank Account', bank_trans.bank_account, 'account')

	credit_row = frappe.new_doc('Journal Entry Account', doc, 'accounts')
	doc.append('accounts', credit_row)
	debit_row = frappe.new_doc('Journal Entry Account', doc, 'accounts')
	doc.append('accounts', debit_row)

	if bank_trans.credit > 0:
		# They paid us
		amount = bank_trans.credit
		opp_row = credit_row
		bank_row = debit_row
	else:
		# We paid them
		amount = bank_trans.debit
		opp_row = debit_row
		bank_row = credit_row

	bank_row.account = bank_ac
	bank_row.bank_account = bank_trans.bank_account

	opp_row.account = opposite_account
	opp_row.party_type = party['type']
	opp_row.party = party['name']
	opp_row.reference_type = reference['type']
	opp_row.reference_name = reference['name']

	credit_row.credit_in_account_currency = amount
	debit_row.debit_in_account_currency = amount

	return doc
