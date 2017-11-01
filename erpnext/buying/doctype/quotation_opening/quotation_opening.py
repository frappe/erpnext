# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class QuotationOpening(Document):
	def validate(self):
		self.validate_supplier_quotation()
		self.validate_sq_duplicate()
		self.get_sqs_for_rfq()
		# sqs = get_sqs_for_rfq(self.request_for_quotation)
		# if sqs: 
		material = frappe.get_doc('Supplier Quotation', self.supplier_quotation)
		if material.material_request:
			self.material_request = material.material_request

			proj = frappe.get_doc('Material Request', self.material_request)
			if proj.project:
				self.project = proj.project

	def validate_sq_duplicate(self):
		sq = frappe.db.sql("select name from `tabQuotation Opening` where docstatus = 1 and request_for_quotation = '{0}'".format(self.request_for_quotation), as_dict = True)
		if sq:
			frappe.throw(_("The request for quotation you have selected is already linked with submitted quotation opening here <a href='#Form/Quotation Opening/{0}'>{0}</a>".format(sq[0].name)))	

	def validate_supplier_quotation(self):
		sqs = []
		if self.get("quotations"):

			for qt in self.get("quotations"):
				sqs.append(qt.supplier_quotation)
			if not self.supplier_quotation in sqs:
				frappe.throw(_("The quotation you have selected is not included in the selected request for quotation"))

	def get_sqs_for_rfq(self):
		sqs = self.get_sqs()

		if sqs:
			csq = []
			for sq in sqs:
				csq.append({
					"supplier_quotation": sq.name,
					"supplier": sq.supplier,
					"grand_total": sq.grand_total,
					"transaction_date": sq.transaction_date
					})
			self.set("quotations", csq)
		else: 
			self.set("quotations", [])

	def get_sqs(self, flt = 0):

		sqs = frappe.db.sql("""select name, supplier, grand_total, transaction_date
		 from `tabSupplier Quotation` where docstatus = 1 and name in (select DISTINCT parent
		 from `tabSupplier Quotation Item` where request_for_quotation = '{0}')
		 """.format(self.request_for_quotation), as_dict = True)
		if flt == 0:
			return sqs
		else:
			sqs_str = ""
			for sq in sqs:
				sqs_str += sq.name + ", "

			if sqs_str != "":
				return sqs_str.rstrip(", ")
			else:
				return None