# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
import frappe
from frappe import _
from frappe.utils import money_in_words
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from frappe.utils.csvutils import getlink
from erpnext.controllers.accounts_controller import AccountsController


class Fees(AccountsController):
	def validate(self):
		self.set_missing_values()
		self.calculate_total()
		# self.validate_debit_to_account()
		
	def set_missing_values(self):
		if not self.contact_email:
			self.contact_email = "manas@erpnext.com"
		if not self.against_income_account:
			self.against_income_account = "Academic Fees - S"
		if not self.cost_center:
			self.cost_center = "Main - S"

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

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True,
		"title": _("Fees"),
		"get_list": get_fee_list,
		"row_template": "templates/includes/fee/fee_row.html"
	}
