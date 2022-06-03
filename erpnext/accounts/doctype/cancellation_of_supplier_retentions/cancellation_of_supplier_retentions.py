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
			self.update_accounts_status()
			self.update_dashboard_supplier()
	
	def on_cancel(self):
		self.update_dashboard_supplier_cancel()
	
	def update_dashboard_supplier(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid += self.total_withheld
			supplier.save()
		else:
			new_doc = frappe.new_doc("Dashboard Supplier")
			new_doc.supplier = self.supplier
			new_doc.company = self.company
			new_doc.billing_this_year = 0
			new_doc.total_unpaid = self.total_withheld
			new_doc.insert()
	
	def update_dashboard_supplier_cancel(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid -= self.total_withheld
			supplier.save()
	
	def update_accounts_status(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.debit += self.total_withheld
			supplier.remaining_balance += self.total_withheld
			supplier.save()

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
		retention.db_set('status', 'Annulled', update_modified=False)
		retention.db_set('total_references', 0, update_modified=False)
		retention.db_set('total_withheld', 0, update_modified=False)
		retention.db_set('percentage_total', 0, update_modified=False)

		references = references = frappe.get_all("Withholding Reference", ["*"], filters = {"parent": self.supplier_retention})

		for reference in references:
			ref = frappe.get_doc("Withholding Reference", reference.name)
			ref.db_set('net_total', 0, update_modified=False)