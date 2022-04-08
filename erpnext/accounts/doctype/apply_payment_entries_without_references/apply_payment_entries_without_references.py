# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ApplyPaymentEntriesWithoutReferences(Document):
	def validate(self):
		if self.current_unallocated_amount <= 0:
			frappe.throw(_("This payment entry {} is not valid.".format(self.payment_entry)))

		if self.docstatus == 1:
			self.update_sales_invoice()
			self.update_payment_entry()
		# self.create_payment_entry_reference()

	def onload(self):
		self.unallocated_amount = 0
		self.total_amount = 0
		self.total_allocated_amount = 0
		for reference in self.get("references"):
			self.total_amount += reference.allocated
		
		self.unallocated_amount = self.current_unallocated_amount - self.total_amount
		self.total_allocated_amount = self.current_total_allocated_amount + self.total_amount

		if self.unallocated_amount < 0:
			frappe.throw(_("Total amount cannot be greater than current unallocated amount."))
	
	def on_cancel(self):
		self.cancel_changes_sales_invoice()
		self.cancel_changes_payment_entry()
	
	def update_payment_entry(self):
		doc = frappe.get_doc("Payment Entry", self.payment_entry)

		doc.db_set('total_allocated_amount', self.total_allocated_amount, update_modified=False)
		doc.db_set('unallocated_amount', self.unallocated_amount, update_modified=False)
	
	def cancel_changes_payment_entry(self):
		doc = frappe.get_doc("Payment Entry", self.payment_entry)

		total_allocated_amount = doc.total_allocated_amount - self.total_amount
		unallocated_amount = doc.unallocated_amount + self.total_amount

		doc.db_set('total_allocated_amount', total_allocated_amount, update_modified=False)
		doc.db_set('unallocated_amount', unallocated_amount, update_modified=False)
	
	def create_payment_entry_reference(self):
		for reference in self.get("references"):
			doc = frappe.get_doc("Payment Entry", self.payment_entry)
			doc.db_set('docstatus', 0, update_modified=False)
			doc.db_set('status', "Draft", update_modified=False)
			row = doc.append("references", {
				'reference_doctype': "Sales Invoice",
				'reference_name': reference.reference_name,
				'due_date': reference.due_date,
				'total_amount': reference.total_amount,
				'outstanding_amount': reference.outstanding_amount,
				'allocated_amount': reference.allocated
			})
			doc.save()
			doc.db_set('docstatus', 1, update_modified=False)
			doc.db_set('status', "Submitted", update_modified=False)
			# doc = frappe.new_doc("Payment Entry Reference")
			# doc.reference_doctype = "Sales Invoice"
			# doc.reference_name = reference.reference_name
			# doc.due_date = reference.due_date
			# doc.total_amount = reference.total_amount
			# doc.outstanding_amount = reference.outstanding_amount
			# doc.allocated_amount = reference.allocated
			# doc.insert()

	def update_sales_invoice(self):
		for reference in self.get("references"):
			doc = frappe.get_doc("Sales Invoice", reference.reference_name)

			outstanding_amount = doc.outstanding_amount - reference.allocated
			total_advance = doc.total_advance + reference.allocated

			if outstanding_amount < 0:
				frappe.throw(_("Allocated cannot be greater than outsanding amount of the invoice {}.".format(reference.reference_name)))
			
			doc.db_set('total_advance', total_advance, update_modified=False)
			doc.db_set('outstanding_amount', outstanding_amount, update_modified=False)

			if outstanding_amount == 0:
				doc.db_set('docstatus', 4, update_modified=False)
				doc.db_set('status', "Paid", update_modified=False)
	
	def cancel_changes_sales_invoice(self):
		for reference in self.get("references"):
			doc = frappe.get_doc("Sales Invoice", reference.reference_name)

			outstanding_amount = doc.outstanding_amount + reference.allocated
			total_advance = doc.total_advance - reference.allocated

			if doc.outstanding_amount > 0:
				doc.db_set('docstatus', 5, update_modified=False)
				doc.db_set('status', "Unpaid", update_modified=False)
			
			doc.db_set('total_advance', total_advance, update_modified=False)
			doc.db_set('outstanding_amount', outstanding_amount, update_modified=False)