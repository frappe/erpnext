# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import date
from frappe.model.document import Document

class Proofofdailysales(Document):
	def validate(self):
		self.calculate_totals()
	
	def calculate_totals(self):
		sales_cash = frappe.get_all("Sales Invoice", ["total", "numeration", "total_taxes_and_charges"], filters = {"is_pos": 0, "company": self.company, "due_date": self.billing_date, "pos": self.pos, "type_document": self.document_type, "docstatus": 1})
		#sales_cards = frappe.get_all("Sales Invoice", ["total"], filters = {"is_pos": 1, "company": self.company, "due_date": self.billing_date, "pos": self.pos, "type_document": self.document_type, "docstatus": 1})
		
		#variables general data
		create_date = date.today()
		rtn = "0502199804256"
		billing_series = ""
		initial_document = ""
		final_document = ""

		#variables taxes
		taxed15 = 0
		taxed18 = 0
		exempt = 0
		exonerated = 0
		isv_taxed15 = 0
		isv_taxed18 = 0
		isv_exempt = 0
		isv_exonerated = 0

		#variables details total
		total_cash = 0
		total_cards = 0
		other_payments = 0
		credits = 0
		total_base_isv15 = 0
		total_base_isv18 = 0
		total_exempt = 0
		total_isv15 = 0
		total_isv18 = 0
		grand_total = 0

		if len(sales_cash) > 0:
			billing_series = sales_cash[0].numeration[0:10]
			initial_document = sales_cash[0].numeration[11:19]

			for cash in sales_cash:
				total_cash += cash.total
				final_document = cash.numeration[11:19]
				
				# if cash.total_taxes_and_charges > 0:
					#desarrollar la logica de los impuestos aplicado
		else:
			frappe.throw(_("No data to display."))
		
		self.create_date = create_date
		self.rtn = rtn
		self.billing_series = billing_series
		self.initial_document = initial_document
		self.final_document = final_document

		self.taxed15 = taxed15
		self.taxed18 = taxed18
		self.exempt = exempt
		self.exonerated = exonerated
		self.isv_taxed15 = isv_taxed15
		self.isv_taxed18 = isv_taxed18
		self.isv_exempt = isv_exempt
		self.isv_exonerated = isv_exonerated

		self.total_cash = total_cash
		self.total_cards = total_cards
		self.other_payments = other_payments
		self.credits = credits
		self.total_base_isv15 = total_base_isv15
		self.total_base_isv18 = total_base_isv18
		self.total_exempt = total_exempt
		self.total_isv15 = total_isv15
		self.total_isv18 = total_isv18
		self.grand_total = total_cash + total_cards + other_payments