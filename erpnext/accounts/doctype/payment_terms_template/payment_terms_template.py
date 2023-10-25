# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PaymentTermsTemplate(Document):
	def validate(self):
		self.validate_invoice_portion()
		self.validate_terms()

	def validate_invoice_portion(self):
		total_portion = 0
		for term in self.terms:
			total_portion += flt(term.get("invoice_portion", 0))

		if flt(total_portion, 2) != 100.00:
			frappe.msgprint(
				_("Combined invoice portion must equal 100%"), raise_exception=1, indicator="red"
			)

	def validate_terms(self):
		terms = []
		for term in self.terms:
			if self.allocate_payment_based_on_payment_terms and not term.payment_term:
				frappe.throw(_("Row {0}: Payment Term is mandatory").format(term.idx))

			term_info = (term.payment_term, term.credit_days, term.credit_months, term.due_date_based_on)
			if term_info in terms:
				frappe.msgprint(
					_("The Payment Term at row {0} is possibly a duplicate.").format(term.idx),
					raise_exception=1,
					indicator="red",
				)
			else:
				terms.append(term_info)
