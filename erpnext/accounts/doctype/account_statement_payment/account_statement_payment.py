# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta, date

class AccountStatementPayment(Document):
	def validate(self):
		if self.docstatus == 1:
			self.create_new_sales_invoice()
	
	def on_cancel(self):
		self.delete_new_sales_invoice()
	
	def delete_new_sales_invoice(self):
		sale_invoice = frappe.get_all("Sales Invoice", ["name"], filters = {"patient_statement": self.patient_statement})
		
		for sale in sale_invoice:
			frappe.delete_doc("Sales Invoice", sale.name)
	
	def create_new_sales_invoice(self):
		if self.customer is None:
			frappe.throw(_("Mandatory customer field."))
		
		if self.due_date is None:
			frappe.throw(_("Mandatory Date field."))
		
		if self.type_document is None:
			frappe.throw(_("Mandatory Type Document field."))
		
		if self.reason_for_sale is None:
			frappe.throw(_("Mandatory Reason for sale field."))
		
		if self.patient_statement is None:
			frappe.throw(_("Mandatory Patient statement field."))
		
		if self.company is None:
			frappe.throw(_("Mandatory Company field."))

		doc = frappe.new_doc('Sales Invoice')
		doc.customer = self.customer
		doc.due_date = self.due_date
		doc.type_document = self.type_document
		doc.reason_for_sale = self.reason_for_sale
		doc.patient_statement = self.patient_statement
		doc.company = self.company
		
		items = frappe.get_all("Account Statement Payment Item", ["item", "item_name", "quantity", "price", "net_pay"], filters = {"parent": self.name})

		for item in items:
			row = doc.append("items", {})
			row.item_code = item.item
			row.qty = item.quantity
			row.rate = item.price
			row.amount = item.net_pay

		doc.insert()

