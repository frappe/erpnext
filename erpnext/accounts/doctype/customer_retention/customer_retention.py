# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw
from frappe.model.document import Document
from datetime import datetime, timedelta, date

class CustomerRetention(Document):
	def validate(self):
		self.calculate_percentage_and_references()
		if self.docstatus == 1:
			self.calculate_retention()
			self.update_accounts_status()
			self.apply_gl_entry()
			self.apply_changes_sales_invoice()
			self.apply_changes_customer_document()
			self.update_dashboard_customer()
	
	def on_cancel(self):
		self.update_dashboard_customer_cancel()
	
	def update_dashboard_customer(self):
		customers = frappe.get_all("Dashboard Customer",["*"], filters = {"customer": self.customer, "company": self.company})

		if len(customers) > 0:
			customer = frappe.get_doc("Dashboard Customer", customers[0].name)
			customer.total_unpaid -= self.total_withheld
			customer.save()
		else:
			new_doc = frappe.new_doc("Dashboard Customer")
			new_doc.customer = self.customer
			new_doc.company = self.company
			new_doc.billing_this_year = 0
			new_doc.total_unpaid = self.total_withheld * -1
			new_doc.insert()
	
	def update_dashboard_customer_cancel(self):
		customers = frappe.get_all("Dashboard Customer",["*"], filters = {"customer": self.customer, "company": self.company})

		if len(customers) > 0:
			customer = frappe.get_doc("Dashboard Customer", customers[0].name)
			customer.total_unpaid += self.total_withheld
			customer.save()

	def calculate_percentage_and_references(self):
		if self.get("reasons"):
			total_percentage = 0
			for item in self.get("reasons"):
				total_percentage += item.percentage
			self.percentage_total = total_percentage
		if self.get("references"):
			total_references = 0
			withheld = 0
			for item in self.get("references"):
				total_references += item.net_total
				withheld += item.net_total * (self.percentage_total/100)
			self.total_references = total_references
			self.total_withheld = withheld
	
	def calculate_retention(self):
		for document in self.get("references"):
			total = document.net_total * (self.percentage_total/100)
			if document.reference_name == "Sales Invoice":
				sales_invoice = frappe.get_doc("Sales Invoice", document.reference_name)
				# sales_invoice.outstanding_amount -= total
				sales_invoice.outstanding_amount = document.net_total - total
				sales_invoice.save()
	
	def update_accounts_status(self):
		customer = frappe.get_doc("Customer", self.customer)
		if customer:
			customer.credit += self.total_withheld
			customer.remaining_balance -= self.total_withheld
			customer.save()

	def create_daily_summary_series(self):
		split_serie = self.naming_series.split('-')
		serie =  "{}-{}".format(split_serie[0], split_serie[1])
		prefix = frappe.get_all("Daily summary series", ["name_serie"], filters = {"name_serie": serie})

		if len(prefix) == 0:
			doc = frappe.new_doc('Daily summary series')
			doc.name_serie = serie
			doc.insert()
	
	def before_naming(self):
		if self.docstatus == 0:
			self.create_daily_summary_series()
	
	def apply_gl_entry(self):
		currentDateTime = datetime.now()
		date = currentDateTime.date()
		year = date.strftime("%Y")

		fecha_inicial = '01-01-{}'.format(year)
		fecha_final = '31-12-{}'.format(year)
		fecha_i = datetime.strptime(fecha_inicial, '%d-%m-%Y')
		fecha_f = datetime.strptime(fecha_final, '%d-%m-%Y')

		fiscal_year = frappe.get_all("Fiscal Year", ["*"], filters = {"year_start_date": [">=", fecha_i], "year_end_date": ["<=", fecha_f]})

		company = frappe.get_doc("Company", self.company)

		account_to_debit = company.default_receivable_account

		reason_porcentage = frappe.get_all("Customer Reason And Percentage", ["reason"], filters = {"parent": self.name})

		reason_retention = frappe.get_doc("Customer Reason For Retention", reason_porcentage[0].reason)

		account_to_credit = reason_retention.account

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = account_to_debit
		doc.party_type = "Customer"
		doc.party = self.customer
		doc.cost_center = company.cost_center
		doc.debit = self.total_withheld
		doc.credit = 0
		doc.account_currency = self.currency
		doc.debit_in_account_currency = self.total_withheld
		doc.credit_in_account_currency = None
		doc.against = account_to_credit
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
		doc.account = account_to_credit
		doc.party_type = "Customer"
		doc.party = self.customer
		doc.cost_center = company.cost_center
		doc.debit = 0
		doc.credit = self.total_withheld
		doc.account_currency = self.currency
		doc.debit_in_account_currency = 0
		doc.credit_in_account_currency = self.total_withheld
		doc.against = account_to_debit
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
	
	def apply_changes_sales_invoice(self):
		references = frappe.get_all("Reference Customer Retention", ["*"], filters = {"parent": self.name})

		for reference in references:
			if reference.reference_doctype == "Sales Invoice":
				doc = frappe.get_doc("Sales Invoice", reference.reference_name)
				outstanding = doc.outstanding_amount
				doc.db_set('outstanding_amount', outstanding, update_modified=False)
	
	def apply_changes_customer_document(self):
		references = frappe.get_all("Reference Customer Retention", ["*"], filters = {"parent": self.name})

		for reference in references:
			if reference.reference_doctype == "Customer Documents":
				doc = frappe.get_doc("Customer Documents", reference.reference_name)
				outstanding = doc.outstanding_amount - self.total_withheld
				doc.db_set('outstanding_amount', outstanding, update_modified=False)