# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.utils import getdate, nowdate, flt
from frappe.model.document import Document
from datetime import datetime, timedelta, date
from frappe.model.naming import parse_naming_series

class SupplierDocuments(Document):
	def validate(self):
		self.calculate_total()
		self.validate_status()
		self.set_status()
		if self.docstatus == 1:
			self.update_accounts_status()
			self.update_dashboard_supplier()
			self.grand_total = self.outstanding_amount
			self.db_set('grand_total', self.outstanding_amount, update_modified=False)
			# self.apply_gl_entry()
		
	def on_load(self):
		self.validate_status()
	
	def on_cancel(self):
		self.update_dashboard_supplier_cancel()
	
	def update_dashboard_supplier(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.billing_this_year += self.total
			supplier.total_unpaid += self.outstanding_amount
			supplier.save()
		else:
			new_doc = frappe.new_doc("Dashboard Supplier")
			new_doc.supplier = self.supplier
			new_doc.company = self.company
			new_doc.billing_this_year = self.total
			new_doc.total_unpaid = self.outstanding_amount
			new_doc.insert()
	
	def update_dashboard_supplier_cancel(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.billing_this_year -= self.total
			supplier.total_unpaid -= self.outstanding_amount
			supplier.save()

	def calculate_total(self):
		self.calculate_isv()
		total_base = 0
		if self.total_exempt != None:
			if not self.get("taxes"):
				self.total = self.total_exempt
				self.outstanding_amount = self.total_exempt
			else:
				for taxes_list in self.get("taxes"):
					total_base += taxes_list.base_isv
				if self.total_exempt != None:
					self.total = total_base + self.total_exempt
					self.outstanding_amount = total_base + self.total_exempt
				else:
					self.total = total_base
					self.outstanding_amount = total_base 
				if self.isv_15 != None:
					self.total = total_base + self.total_exempt + self.isv_15
					self.outstanding_amount = total_base + self.total_exempt + self.isv_15
				elif self.isv_18 != None:
					self.total = total_base + self.total_exempt + self.isv_15
					self.outstanding_amount = total_base + self.total_exempt + self.isv_15
			
	def calculate_isv(self):
		self.isv_15 = 0
		self.isv_18 = 0
		for taxes_list in self.get("taxes"):
			item_tax_template = frappe.get_all("Item Tax Template", ["name"], filters = {"name": taxes_list.isv_template})
			for tax_template in item_tax_template:
				tax_details = frappe.get_all("Item Tax Template Detail", ["name", "tax_rate"], filters = {"parent": tax_template.name})
				for tax in tax_details:
					if tax.tax_rate == 15:
						tx_base = taxes_list.base_isv * (tax.tax_rate/100)
						self.isv_15 = tx_base
					elif tax.tax_rate == 18:
						tx_base = taxes_list.base_isv * (tax.tax_rate/100)
						self.isv_18 = tx_base

	def update_accounts_status(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.debit += self.total
			supplier.remaining_balance += self.total
			supplier.save()
	
	def validate_status(self):
		if self.outstanding_amount > 0:
			self.status = "Unpaid"
		elif  getdate(self.due_date) >= getdate(nowdate()):
			self.status = "Overdue"
		elif self.outstanding_amount <= 0:
			self.status = "Paid"
	
	def set_status(self, update=False, status=None, update_modified=True):
		if self.is_new():
			if self.get('amended_from'):
				self.status = 'Draft'
			return

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if flt(self.outstanding_amount) > 0 and getdate(self.due_date) < getdate(nowdate()):
					self.status = "Overdue"
				elif flt(self.outstanding_amount) > 0 and getdate(self.due_date) >= getdate(nowdate()):
					self.status = "Unpaid"
				elif flt(self.outstanding_amount)<=0:
					self.status = "Paid"
				else:
					self.status = "Submitted"
			else:
				self.status = "Draft"

		if update:
			self.db_set('status', self.status, update_modified = update_modified)

	def apply_gl_entry(self):
		currentDateTime = datetime.now()
		date = currentDateTime.date()
		year = date.strftime("%Y")

		fecha_inicial = '01-01-{}'.format(year)
		fecha_final = '31-12-{}'.format(year)
		fecha_i = datetime.strptime(fecha_inicial, '%d-%m-%Y')
		fecha_f = datetime.strptime(fecha_final, '%d-%m-%Y')

		fiscal_year = frappe.get_all("Fiscal Year", ["*"], filters = {"year_start_date": [">=", fecha_i], "year_end_date": ["<=", fecha_f]})

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = self.account_to_debit
		doc.party_type = "Supplier"
		doc.party = self.supplier
		doc.cost_center = self.cost_center
		doc.debit = self.total
		doc.credit = 0
		doc.account_currency = self.currency
		doc.debit_in_account_currency = self.total
		doc.credit_in_account_currency = None
		doc.against = self.account_to_credit
		doc.against_voucher_type = self.doctype
		doc.against_voucher = self.name
		doc.voucher_type =  self.doctype
		doc.voucher_no = self.name
		doc.voucher_detail_no = None
		doc.project = None
		doc.remarks = 'No Remarks'
		doc.is_opening = "No"
		doc.is_advance = "No"
		doc.fiscal_year = fiscal_year[0].name
		doc.company = self.company
		doc.finance_book = None
		doc.to_rename = 1
		doc.due_date = None
		# doc.docstatus = 1
		doc.insert()

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = self.account_to_credit
		doc.party_type = "Supplier"
		doc.party = self.supplier
		doc.cost_center = self.cost_center
		doc.debit = 0
		doc.credit = self.total
		doc.account_currency = self.currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = self.total
		doc.against = self.account_to_debit
		doc.against_voucher_type = self.doctype
		doc.against_voucher = self.name
		doc.voucher_type =  self.doctype
		doc.voucher_no = self.name
		doc.voucher_detail_no = None
		doc.project = None
		doc.remarks = 'No Remarks'
		doc.is_opening = "No"
		doc.is_advance = "No"
		doc.fiscal_year = fiscal_year[0].name
		doc.company = self.company
		doc.finance_book = None
		doc.to_rename = 1
		doc.due_date = None
		# doc.docstatus = 1
		doc.insert()
