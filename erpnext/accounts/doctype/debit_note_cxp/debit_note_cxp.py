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
		self.calculate_totals()

		if self.docstatus == 1:
			self.update_dashboard_supplier()
			self.update_accounts_status()
			self.apply_gl_entry()
	
	def on_cancel(self):
		self.update_dashboard_supplier_cancel()
		self.update_accounts_status_cancel()
		self.delete_gl_entry()
	
	def calculate_totals(self):		
		self.total_taxed = 0
		tax15 = 0
		tax18 = 0

		for tax in self.get("taxes"):
			self.total_taxed += tax.base_isv

			tax_rate = frappe.get_all("Item Tax Template Detail", ["*"], filters = {"parent": tax.isv_template})

			if tax_rate[0].tax_rate == 15:
				tax15 += (tax.base_isv / 1.15)*0.15
			
			if tax_rate[0].tax_rate == 18:
				tax18 += (tax.base_isv / 1.18)*0.18
		
		if self.total_taxed > self.amount_total:
			frappe.throw(_("Total taxed can't be greater than Amount Total."))
		
		self.isv_18 = tax18
		self.isv_15 = tax15
		self.outstanding_amount = self.amount_total
	
	def update_dashboard_supplier(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.billing_this_year += self.amount_total
			supplier.total_unpaid += self.outstanding_amount
			supplier.save()
		else:
			new_doc = frappe.new_doc("Dashboard Supplier")
			new_doc.supplier = self.supplier
			new_doc.company = self.company
			new_doc.billing_this_year = self.amount_total
			new_doc.total_unpaid = self.outstanding_amount
			new_doc.insert()
	
	def update_dashboard_supplier_cancel(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.billing_this_year -= self.amount_total
			supplier.total_unpaid -= self.outstanding_amount
			supplier.save()
	
	def update_accounts_status(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.debit += self.amount_total
			supplier.remaining_balance += self.amount_total
			supplier.save()
	
	def update_accounts_status_cancel(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.debit -= self.amount_total
			supplier.remaining_balance -= self.amount_total
			supplier.save()
	
	def delete_gl_entry(self):
		entries = frappe.get_all("GL Entry", ["name"], filters = {"voucher_no": self.name})

		for entry in entries:
			frappe.delete_doc("GL Entry", entry.name)
	
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