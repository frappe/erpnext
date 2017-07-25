# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import money_in_words, nowdate
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from frappe.utils.csvutils import getlink
from erpnext.accounts.utils import get_account_currency
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

class Fees(AccountsController):
	def set_indicator(self):
		"""Set indicator for portal"""
		if self.outstanding_amount > 0:
			self.indicator_color = "orange"
			self.indicator_title = _("Unpaid")
		else:
			self.indicator_color = "green"
			self.indicator_title = _("Paid")

	def validate(self):
		self.calculate_total()
		'''
		set missing field here and validate the accounts
		'''

	def calculate_total(self):
		"""Calculates total amount."""
		self.grand_total = 0
		for d in self.components:
			self.grand_total += d.amount
		self.outstanding_amount = self.grand_total
		self.grand_total_in_words = money_in_words(self.grand_total)

	def on_submit(self):

		self.make_gl_entries()

		if self.send_payment_request:
			pr = make_payment_request(dt="Fees", dn=self.name, recipient_id=self.contact_email,
					submit_doc=True, use_dummy_message=True)
			frappe.msgprint(_("Payment request {0} created").format(getlink("Payment Request", pr.name)))


	def make_gl_entries(self):
		if not self.grand_total:
			return
		student_gl_entries =  self.get_gl_dict({
							"account": self.debit_to,
							"party_type": "Student",
							"party": self.student,
							"against": self.against_income_account,
							"debit": self.grand_total,
							"debit_in_account_currency": self.grand_total,
							"against_voucher": self.name,
							"against_voucher_type": self.doctype
						})
		fee_gl_entry = self.get_gl_dict({
							"account": self.against_income_account,
							"against": self.student,
							"credit": self.grand_total,
							"credit_in_account_currency": self.grand_total,
							"cost_center": self.cost_center
						})
		from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries([student_gl_entries, fee_gl_entry], cancel=(self.docstatus == 2),
			update_outstanding="Yes", merge_entries=False)

def get_fee_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified"):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		return frappe. db.sql('''select name, program, due_date, paid_amount, outstanding_amount, total_amount from `tabFees`
			where student= %s and docstatus=1
			order by due_date asc limit {0} , {1}'''
			.format(limit_start, limit_page_length), student, as_dict = True)


@frappe.whitelist()
def get_payment_entry(dt, dn, bank_account=None):
	doc = frappe.get_doc(dt, dn)

	party_type = "Student"
	party_account = doc.debit_to
	party_account_currency = doc.get("currency") or get_account_currency(party_account)

	# payment type
	if (doc.outstanding_amount > 0):
			payment_type = "Receive"

	# amounts
	grand_total = outstanding_amount = 0
	grand_total = doc.grand_total
	outstanding_amount = doc.outstanding_amount

	# bank or cash
	bank = get_default_bank_cash_account(doc.company, "Bank")

	paid_amount = received_amount = 0
	if party_account_currency == bank.account_currency:
		paid_amount = received_amount = abs(outstanding_amount)
	elif payment_type == "Receive":
		paid_amount = abs(outstanding_amount)
	else:
		received_amount = abs(outstanding_amount)

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = payment_type
	pe.company = doc.company
	pe.posting_date = nowdate()
	pe.mode_of_payment = doc.get("mode_of_payment")
	pe.party_type = party_type
	pe.party = doc.student
	pe.party_name = doc.student_name
	pe.paid_from = party_account if payment_type=="Receive" else bank.account
	pe.paid_to = party_account if payment_type=="Pay" else bank.account
	pe.paid_from_account_currency = party_account_currency if payment_type=="Receive" else bank.account_currency
	pe.paid_to_account_currency = party_account_currency if payment_type=="Pay" else bank.account_currency
	pe.paid_amount = paid_amount
	pe.received_amount = received_amount
	pe.allocate_payment_amount = 1
	pe.letter_head = doc.get("letter_head")

	pe.append("references", {
		"reference_doctype": dt,
		"reference_name": dn,
		"due_date": doc.get("due_date"),
		"total_amount": grand_total,
		"outstanding_amount": outstanding_amount,
		"allocated_amount": outstanding_amount
	})

	pe.setup_party_account_field()
	pe.set_missing_values()
	return pe


def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Fees"),
		"get_list": get_fee_list,
		"row_template": "templates/includes/fee/fee_row.html"
	}
