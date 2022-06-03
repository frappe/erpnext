# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.model.document import Document
from datetime import datetime, timedelta, date

class DebitNoteCXP(Document):
	def validate(self):
		self.verificate_references_and_amount()
		self.calculate_total()
		if self.docstatus == 1:
			self.verificate_amount()
			self.update_accounts_status()
			self.apply_gl_entry()
			self.update_dashboard_supplier()
	
	def on_cancel(self):
		self.update_dashboard_supplier_cancel()
	
	def update_dashboard_supplier(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid -= self.amount_total
			supplier.save()
		else:
			new_doc = frappe.new_doc("Dashboard Supplier")
			new_doc.supplier = self.supplier
			new_doc.company = self.company
			new_doc.billing_this_year = 0
			new_doc.total_unpaid -= self.amount_total
			new_doc.insert()
	
	def update_dashboard_supplier_cancel(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid += self.amount_total
			supplier.save()

	def calculate_total(self):
		if not self.get("references"):
			frappe.throw(_(" Required references"))
		total_reference = 0
		for d in self.get("references"):
			total_reference += d.total_amount
			self.total_references = total_reference
		
		if self.total_exempt > self.total_references:
			frappe.throw(_("Amount cannot be greater than the total references"))

		self.calculate_isv()
		total_base = 0
		if len(self.get("references")) > 0:
			if self.total_exempt != None:
				if not self.get("taxes"):
					self.amount_total = self.total_exempt
				else:
					for taxes_list in self.get("taxes"):
						total_base += taxes_list.base_isv
						if self.total_exempt != None:
							self.amount_total = total_base + self.total_exempt
						else:
							self.amount_total = total_base
						if self.isv_15 != None:
							self.amount_total = total_base + self.total_exempt + self.isv_15
						elif self.isv_18 != None:
							self.amount_total = total_base + self.total_exempt + self.isv_18
	
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

	def verificate_references_and_amount(self):
		if len(self.get("references")) > 1:
			order_by = sorted(self.references, key=lambda item: item.total_amount)
			remaining_amount = self.amount
			for d in order_by:
				if remaining_amount <= d.total_amount:
					result = d.total_amount - remaining_amount
					if result <= 0:
						frappe.throw(_("The amount can not be accepted to pay the bills, the amount must pay the bills or pay one and advance another."))

	def verificate_amount(self):
		remaining = 0
		amount_total = self.amount_total
		if len(self.get("references")) > 1:
			for d in sorted(self.references, key=lambda item: item.total_amount):
				purchase_invoice = frappe.get_doc("Purchase Invoice", d.reference_name)
				if amount_total > d.total_amount:
					amount_total -= d.total_amount
					purchase_invoice.outstanding_amount -= d.total_amount
				else:
					if amount_total <= d.total_amount:
						purchase_invoice.outstanding_amount -= amount_total
				purchase_invoice.save()
		else: 
			for x in self.get("references"):
				if amount_total <= x.total_amount:
					purchase_invoice = frappe.get_doc("Purchase Invoice", x.reference_name)
					purchase_invoice.outstanding_amount -= self.amount_total
				purchase_invoice.save()
	
	def update_accounts_status(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.credit += self.amount_total
			supplier.remaining_balance -= self.amount_total
			supplier.save()
	
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
		doc.debit = self.amount_total
		doc.credit = 0
		doc.account_currency = self.currency
		doc.debit_in_account_currency = self.amount_total
		doc.credit_in_account_currency = 0
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
		doc.credit = self.amount_total
		doc.account_currency = self.currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = self.amount_total
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