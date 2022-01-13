# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CancellationOfSupplierRetentions(Document):
	def validate(self):
		if self.docstatus == 1:
			self.calculate_retention()
			self.delete_gl_entries()
			self.change_status_retention()
	
	def calculate_retention(self):
		retention = frappe.get_doc("Supplier Retention", self.supplier_retention)

		for document in retention.get("references"):
			total = document.net_total * (self.percentage_total/100)			

			if document.reference_doctype == "Purchase Invoice":
				sales_invoice = frappe.get_doc("Purchase Invoice", document.reference_name)
				outstanding_amount = sales_invoice.outstanding_amount
				outstanding_amount += total
				sales_invoice.db_set('outstanding_amount', outstanding_amount, update_modified=False)

			if document.reference_doctype == "Supplier Documents":
				supllier_document = frappe.get_doc("Supplier Documents", document.reference_name)
				outstanding_amount = supllier_document.outstanding_amount
				outstanding_amount += total
				supllier_document.db_set('outstanding_amount', outstanding_amount, update_modified=False)
	
	def delete_gl_entries(self):
		entries = frappe.get_all("GL Entry", ["*"], filters = {"voucher_no": self.supplier_retention})

		for entry in entries:
			doc = frappe.get_doc("GL Entry", entry.name)
			doc.db_set('docstatus', 0, update_modified=False)

			frappe.delete_doc("GL Entry", entry.name)
	
	def change_status_retention(self):
		retention = frappe.get_doc("Supplier Retention", self.supplier_retention)
		retention.db_set('docstatus', 2, update_modified=False)