# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import datetime, timedelta, date
import pandas as pd
from pandas import ExcelWriter

class AccountStatementPayment(Document):
	def validate(self):
		if self.update_table:
			self.add_products_detail()

		if self.docstatus == 0 and self.discount_check:
			self.calculate_discount()
	
	def delete_new_sales_invoice(self):
		sale_invoice = frappe.get_all("Sales Invoice", ["name"], filters = {"patient_statement": self.patient_statement})
		
		for sale in sale_invoice:
			frappe.delete_doc("Sales Invoice", sale.name)
	
	def create_new_sales_invoice(self):
		if self.customer is None:
			frappe.throw(_("Mandatory customer field."))
		
		if self.due_date is None:
			frappe.throw(_("Mandatory Date field."))
		
		if self.reason_for_sale is None:
			frappe.throw(_("Mandatory Reason for sale field."))
		
		if self.patient_statement is None:
			frappe.throw(_("Mandatory Patient statement field."))
		
		if self.company is None:
			frappe.throw(_("Mandatory Company field."))

		doc = frappe.new_doc('Sales Invoice')
		doc.customer = self.customer
		doc.due_date = self.due_date
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

	def calculate_discount(self):
		total_sale = 0
		items = frappe.get_all("Account Statement Payment Item", ["item", "item_name", "quantity", "price", "net_pay", "sale_amount"], filters = {"parent": self.name})

		for item in items:
			if item.net_pay != item.sale_amount:
				total_sale += item.sale_amount
			else:
				total_sale += item.net_pay

		self.total_sale = total_sale

		self.total_discount = self.total_sale - self.discount_amount

		# return {
		# 	"total_sale": total_sale,
		# 	"total_discount": total_discount
		# }
	
	def add_products_detail(self):
		if self.products_detail != None:
			self.delete_products_detail()

		if self.products_table != None:
			for x in range(1,5):
				for product in self.get("products_table"):
					if product.no_order != None:
						if int(product.no_order) == x:
							row = self.append("products_detail", {})
							row.item = product.item
							row.item_name = product.item_name
							row.quantity = product.quantity
							row.price = product.price
							row.net_pay = product.net_pay
							row.sale_amount = product.sale_amount
							row.reference = product.reference
							if x == 1: row.history = _("Hospital Outgoings")
							if x == 2: row.history = _("Inventory Requisition")
							if x == 3: row.history = _("Laboratory and image")
							if x == 4: row.history = _("Medical Honorarium")
							row.no_order = x
			
			for product in self.get("products_table"):
				if product.no_order == None:
					row = self.append("products_detail", {})
					row.item = product.item
					row.item_name = product.item_name
					row.quantity = product.quantity
					row.price = product.price
					row.net_pay = product.net_pay
					row.sale_amount = product.sale_amount
					row.reference = product.reference

	def delete_products_detail(self):
		for product in self.get("products_detail"):
			frappe.delete_doc("Account Statement Payment Item Detail", product.name)
	
	def export_to_excel(self):
		name_list = [self.name]
		patient_statement_list = [self.patient_statement]
		customer_list = [self.customer]
		patient_name_list = [self.patient_name]
		company_list = [self.company]
		reason_for_sale_list = [self.reason_for_sale]

		data = pd.DataFrame({"Nombre": name_list,"Cuenta del paciente": patient_statement_list, "Cliente": customer_list, "Nombre del paciente": patient_name_list, "Compañia": company_list, "Razon de venta": reason_for_sale_list})

		# data = data[["Nombre", "Cuenta del paciente", "Cliente", "Nombre del paciente", "Compañia", "Razon de venta"]]
		writer = ExcelWriter('estado_euenta.xlsx')
		data.to_excel(writer, 'Hoja de datos', index=False)
		writer.save()
