# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class PaymentTermsTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.payment_terms_template_detail.payment_terms_template_detail import (
			PaymentTermsTemplateDetail,
		)

		allocate_payment_based_on_payment_terms: DF.Check
		template_name: DF.Data | None
		terms: DF.Table[PaymentTermsTemplateDetail]
	# end: auto-generated types

	def validate(self):
		self.validate_invoice_portion()
		self.validate_terms()

	def validate_invoice_portion(self):
		total_portion = 0
		for term in self.terms:
			if flt(term.invoice_portion) <= 0:
				frappe.throw(
					_("Row {0}: Invoice Portion must be more than 0.").format(term.idx),
					title=_("Invalid Invoice Portion"),
				)
			total_portion += flt(term.invoice_portion)

		if flt(total_portion, 2) != 100.00:
			frappe.msgprint(_("Combined invoice portion must equal 100%"), raise_exception=1, indicator="red")

	def validate_terms(self):
		terms = []
		payment_terms = set()
		for term in self.terms:
			if self.allocate_payment_based_on_payment_terms:
				if not term.payment_term:
					frappe.throw(_("Row {0}: Payment Term is mandatory").format(term.idx))

				# payments are allocated by payment term, so each term must be used once
				if term.payment_term in payment_terms:
					frappe.throw(
						_(
							"Row {0}: Payment Term {1} is used more than once. Each Payment Term must be used only once when payments are allocated based on payment terms."
						).format(term.idx, frappe.bold(term.payment_term)),
						title=_("Duplicate Payment Term"),
					)
				payment_terms.add(term.payment_term)

			term_info = (term.payment_term, term.credit_days, term.credit_months, term.due_date_based_on)
			if term_info in terms:
				frappe.msgprint(
					_("The Payment Term at row {0} is possibly a duplicate.").format(term.idx),
					raise_exception=1,
					indicator="red",
				)
			else:
				terms.append(term_info)
