# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from frappe import _


class PaymentTermsTemplate(Document):
	def validate(self):
		self.validate_invoice_portion()
		self.validate_credit_days()
		self.check_duplicate_terms()

	def validate_invoice_portion(self):
		payment_amount_types = list(set([d.payment_amount_type for d in self.terms]))

		if len(payment_amount_types) == 1 and payment_amount_types[0] == "Percentage":
			total_portion = 0
			for term in self.terms:
				total_portion += flt(term.get('invoice_portion', 0))

			if flt(total_portion, 2) != 100.00:
				frappe.msgprint(_('Combined invoice portion must equal 100%'), raise_exception=1, indicator='red')

		if 'Amount' in payment_amount_types:
			if 'Percentage' in payment_amount_types:
				frappe.throw(_("Payment Amount Type 'Percentage' cannot be selected if 'Amount' is selected"))

			for i, term in enumerate(self.terms):
				last_row = i == len(self.terms) - 1
				if term.payment_amount_type == "Remaining Amount" and not last_row:
					frappe.throw(_("Row {0}: Payment Amount Type 'Remaining Amount' can only be set for the last row"))


	def validate_credit_days(self):
		for term in self.terms:
			if cint(term.credit_days) < 0:
				frappe.msgprint(_('Credit Days cannot be a negative number'), raise_exception=1, indicator='red')

	def check_duplicate_terms(self):
		terms = []
		for term in self.terms:
			term_info = (term.credit_days, term.credit_months, term.due_date_based_on)
			if term_info in terms:
				frappe.msgprint(
					_('The Payment Term at row {0} is possibly a duplicate.').format(term.idx),
					raise_exception=1, indicator='red'
				)
			else:
				terms.append(term_info)
