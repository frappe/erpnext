# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import nowdate
from erpnext.accounts.party import get_party_account
from frappe.model.document import Document

class PaymentOrder(Document):
	def on_submit(self):
		self.update_payment_status()

	def on_cancel(self):
		self.update_payment_status(cancel=True)

	def update_payment_status(self, cancel=False):
		status = 'Payment Ordered'
		if cancel:
			status = 'Initiated'

		ref_field = "status" if self.payment_order_type == "Payment Request" else "payment_order_status"

		for d in self.references:
			frappe.db.set_value(self.payment_order_type, d.get(frappe.scrub(self.payment_order_type)), ref_field, status)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_mop_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" select mode_of_payment from `tabPayment Order Reference`
		where parent = %(parent)s and mode_of_payment like %(txt)s
		limit %(start)s, %(page_len)s""", {
			'parent': filters.get("parent"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		})

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier_query(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" select supplier from `tabPayment Order Reference`
		where parent = %(parent)s and supplier like %(txt)s and
		(payment_reference is null or payment_reference='')
		limit %(start)s, %(page_len)s""", {
			'parent': filters.get("parent"),
			'start': start,
			'page_len': page_len,
			'txt': "%%%s%%" % txt
		})

@frappe.whitelist()
def make_payment_records(name, supplier, mode_of_payment=None):
	doc = frappe.get_doc('Payment Order', name)
	make_journal_entry(doc, supplier, mode_of_payment)

def make_journal_entry(doc, supplier, mode_of_payment=None):
	# je = frappe.new_doc('Journal Entry')
	je = frappe.new_doc('Payment Entry')
	je.payment_order = doc.name
	je.posting_date = nowdate()
	je.party = supplier
	je.party_type = 'Supplier'
	je.company = doc.company
	je.payment_type = 'Pay'

	je.reference_date = nowdate()
	# bank or cash
	from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
	bank = get_default_bank_cash_account(doc.company, "Bank", mode_of_payment=None,account=None)

	if not bank:
		bank = get_default_bank_cash_account(doc.company, "Cash", mode_of_payment=None,account=None)
	party_account = get_party_account('Supplier', supplier, doc.company)
	je.paid_from = party_account if je.payment_type=="Receive" else doc.references[0].account
	je.paid_to = party_account if je.payment_type=="Pay" else bank.account
	# je.paid_to = doc.references[0].account
	# je.paid_to = party_account if payment_type=="Pay" else bank.account

	# Cheque Book Changes
	if doc.references[0].mode_of_payment == 'BANK' or doc.references[0].mode_of_payment == 'Cheque':
		cheque_no = frappe.db.sql("""
		SELECT
			name
			From
			`tabCheque Book Series`
			WHERE
		parent = (
			SELECT
			name
			FROM
			`tabCheque Book Enrollment`
			WHERE
			account_name = '{0}'
			and docstatus = 1
			and is_active = 1
			)
		and status = 'Not Used'
		ORDER BY cast(cheque_number as UNSIGNED) asc 
		LIMIT 1 
		FOR UPDATE
	""".format(doc.company_bank_account))
		if cheque_no:
			je.reference_no = cheque_no[0][0]

	mode_of_payment_type = frappe._dict(frappe.get_all('Mode of Payment',
		fields = ["name", "type"], as_list=1))

	je.voucher_type = 'Bank Entry'
	if mode_of_payment and mode_of_payment_type.get(mode_of_payment) == 'Cash':
		je.voucher_type = "Cash Entry"

	paid_amt = 0
	
	for d in doc.references:
		if (d.supplier == supplier
			and (not mode_of_payment or mode_of_payment == d.mode_of_payment)):
			je.append('references', {
				# 'account': party_account,
				'total_amount': d.amount,
				# 'debit_in_account_currency': d.amount,
				# 'party_type': 'Supplier',
				# 'party': supplier,
				'reference_doctype': d.reference_doctype,
				'reference_name': d.reference_name,
				'outstanding_amount': d.amount,
				'allocated_amount': d.amount
			})

			paid_amt += d.amount

	# je.append('references', {
	# 	'total_amount': paid_amt,
	# 	'outstanding_amount': paid_amt,
	# 	'allocated_amount': d.a
	# 	# 'account': doc.account,
	# 	# 'credit_in_account_currency': paid_amt
	# })
	je.paid_amount = paid_amt
	je.received_amount = paid_amt
	je.flags.ignore_mandatory = True
	je.save()
	if doc.references[0].mode_of_payment == 'BANK' or doc.references[0].mode_of_payment == 'Cheque':
		if cheque_no:
			frappe.db.sql("""update `tabCheque Book Series` set status='Used',refrence='{0}' WHERE parent = (
					SELECT
					name
					FROM
					`tabCheque Book Enrollment`
					WHERE
					account_name = '{1}'
					and docstatus = 1
					and is_active = 1
					)
				and name = '{2}'""".format(je.name,doc.company_bank_account,cheque_no[0][0]),debug=True)
	frappe.msgprint(_("{0} {1} created").format(je.doctype, je.name))
