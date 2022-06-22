# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import erpnext
import frappe
from frappe import _, msgprint, throw
from frappe.utils import getdate, nowdate
from frappe.model.document import Document
from datetime import datetime, timedelta, date
from frappe.model.naming import parse_naming_series

class SupplierRetention(Document):
	def validate(self):
		self.calculate_percentage_and_references()
		if self.docstatus == 1:
			self.calculate_retention()
			self.update_accounts_status()
			self.apply_gl_entry()
			self.update_dashboard_supplier()
	
	def on_cancel(self):
		self.update_dashboard_supplier_cancel()
	
	def update_dashboard_supplier(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid -= self.total_withheld
			supplier.save()
		else:
			new_doc = frappe.new_doc("Dashboard Supplier")
			new_doc.supplier = self.supplier
			new_doc.company = self.company
			new_doc.billing_this_year = 0
			new_doc.total_unpaid = self.total_withheld * -1
			new_doc.insert()
	
	def update_dashboard_supplier_cancel(self):
		suppliers = frappe.get_all("Dashboard Supplier",["*"], filters = {"supplier": self.supplier, "company": self.company})

		if len(suppliers) > 0:
			supplier = frappe.get_doc("Dashboard Supplier", suppliers[0].name)
			supplier.total_unpaid += self.total_withheld
			supplier.save()

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

			if document.reference_doctype == "Purchase Invoice":
				sales_invoice = frappe.get_doc("Purchase Invoice", document.reference_name)
				outstanding_amount = sales_invoice.outstanding_amount
				outstanding_amount -= total
				sales_invoice.db_set('outstanding_amount', outstanding_amount, update_modified=False)
			
			if document.reference_doctype == "Sales Invoice":
				sales_invoice = frappe.get_doc("Sales Invoice", document.reference_name)
				outstanding_amount = sales_invoice.outstanding_amount
				outstanding_amount -= total
				sales_invoice.db_set('outstanding_amount', outstanding_amount, update_modified=False)

			if document.reference_doctype == "Supplier Documents":
				supllier_document = frappe.get_doc("Supplier Documents", document.reference_name)
				outstanding_amount = supllier_document.outstanding_amount
				outstanding_amount -= total
				supllier_document.db_set('outstanding_amount', outstanding_amount, update_modified=False)
	
	def update_accounts_status(self):
		supplier = frappe.get_doc("Supplier", self.supplier)
		if supplier:
			supplier.credit += self.total_withheld
			supplier.remaining_balance -= self.total_withheld
			supplier.save()

	def assign_cai(self):
		cai = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Active", "prefix": self.naming_series})
		if len(cai) == 0:
			frappe.throw(_("This secuence no assing cai"))
		current_value = self.get_current(cai[0].prefix)

		if current_value == None:
			current_value = 0

		now = datetime.now()

		date = now.date()

		if current_value + 1 <= int(cai[0].final_number) and str(date) <= str(cai[0].issue_deadline):
			self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, cai[0].prefix)

			amount = int(cai[0].final_number) - current_value

			self.alerts(cai[0].issue_deadline, amount)
		else:
			cai_secondary = frappe.get_all("CAI", ["initial_number", "final_number", "name_cai", "cai", "issue_deadline", "prefix"], filters = { "status": "Pending", "prefix": self.naming_series})
			
			if len(cai_secondary) > 0:
				final = int(cai[0].final_number) + 1
				initial = int(cai_secondary[0].initial_number)
				if final == initial:
					self.assing_data(cai_secondary[0].cai, cai_secondary[0].issue_deadline, cai_secondary[0].initial_number, cai_secondary[0].final_number, cai_secondary[0].prefix)
					doc = frappe.get_doc("CAI", cai[0].name_cai)
					doc.status = "Inactive"
					doc.save()

					doc_sec = frappe.get_doc("CAI", cai_secondary[0].name_cai)
					doc_sec.status = "Active"
					doc_sec.save()

					new_current = int(cai_secondary[0].initial_number) - 1
					name = self.parse_naming_series(cai_secondary[0].prefix)

					frappe.db.set_value("Series", name, "current", new_current, update_modified=False)
				else:
					self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, cai[0].prefix)
					frappe.throw("The CAI you are using is expired.")
			else:
				self.assing_data(cai[0].cai, cai[0].issue_deadline, cai[0].initial_number, cai[0].final_number, cai[0].prefix)
				frappe.throw("The CAI you are using is expired.")
	
	def get_current(self, prefix):
		pre = self.parse_naming_series(prefix)
		current_value = frappe.db.get_value("Series",
		pre, "current", order_by = "name")
		return current_value

	def parse_naming_series(self, prefix):
		parts = prefix.split('.')
		if parts[-1] == "#" * len(parts[-1]):
			del parts[-1]

		pre = parse_naming_series(parts)
		return pre
	
	def assing_data(self, cai, issue_deadline, initial_number, final_number, prefix):
		pre = self.parse_naming_series(prefix)

		self.cai = cai

		self.due_date_cai = issue_deadline

		self.authorized_range = "{}{} al {}{}".format(pre, self.serie_number(int(initial_number)), pre, self.serie_number(int(final_number)))

	
	def serie_number(self, number):

		if number >= 1 and number < 10:
			return("0000000" + str(number))
		elif number >= 10 and number < 100:
			return("000000" + str(number))
		elif number >= 100 and number < 1000:
			return("00000" + str(number))
		elif number >= 1000 and number < 10000:
			return("0000" + str(number))
		elif number >= 10000 and number < 100000:
			return("000" + str(number))
		elif number >= 100000 and number < 1000000:
			return("00" + str(number))
		elif number >= 1000000 and number < 10000000:
			return("0" + str(number))
		elif number >= 10000000:
			return(str(number))
	

	def before_naming(self):
		if self.docstatus == 0:
			self.assign_cai()
	
	def alerts(self, date, amount):
		gcai_setting = frappe.get_all("Cai Settings", ["expired_days", "expired_amount"])

		if len(gcai_setting) > 0:
			if amount <= gcai_setting[0].expired_amount:
				amount_rest = amount - 1
				frappe.msgprint(_("There are only {} numbers available for this CAI.".format(amount_rest)))
		
			now = date.today()
			days = timedelta(days=int(gcai_setting[0].expired_days))

			sum_dates = now+days

			if str(date) <= str(sum_dates):
				for i in range(int(gcai_setting[0].expired_days)):		
					now1 = date.today()
					days1 = timedelta(days=i)

					sum_dates1 = now1+days1
					if str(date) == str(sum_dates1):
						frappe.msgprint(_("This CAI expires in {} days.".format(i)))
						break
	
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

		account_to_debit = company.default_payable_account

		reason_porcentage = frappe.get_all("Reason And Percentage", ["reason"], filters = {"parent": self.name})

		reason_retention = frappe.get_doc("Reason For Retention", reason_porcentage[0].reason)

		account_to_credit = reason_retention.account

		doc = frappe.new_doc("GL Entry")
		doc.posting_date = self.posting_date
		doc.transaction_date = None
		doc.account = account_to_debit
		doc.party_type = "Supplier"
		doc.party = self.supplier
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
		doc.party_type = "Supplier"
		doc.party = self.supplier
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