# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import date
from frappe.model.document import Document

class Proofofdailysales(Document):
	def on_update(self):
		self.calculate_totals()
	
	def calculate_totals(self):
		sales_invoice = frappe.get_all("Sales Invoice", ["total", "numeration", "total_taxes_and_charges", "name"], filters = {"is_pos": 0, "company": self.company, "due_date": self.billing_date, "pos": self.pos, "type_document": self.document_type, "docstatus": 1})
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
		total_base_isv15 = 0
		total_base_isv18 = 0
		total_exempt = 0
		total_isv15 = 0
		total_isv18 = 0
		grand_total = 0

		mode_pay = frappe.get_all("Mode of Payment", ["name"])

		# for mode in mode_pay:
		# 	total_payment = 0
		# 	payments_entry = frappe.get_all("Payment Entry", ["paid_amount"], filters = {"posting_date": self.billing_date, "mode_of_payment": mode.name, "docstatus": 1})

		# 	for payment in payments_entry:
		# 		total_payment += payment.paid_amount
			
		# 	grand_total += total_payment
		# 	exempt += total_payment
		# 	total_exempt += total_payment

		# 	registers_totals = frappe.get_all("Details totals proof of daily sales", ["name"], filters = {"mode_of_payment": mode.name, "parent": self.name})

		# 	if len(registers_totals) > 0:
		# 		doc = frappe.get_doc("Details totals proof of daily sales", registers_totals[0].name)
		# 		doc.total = total_payment
		# 		doc.save()
		# 	else:
		# 		row = self.append("totals_table", {})
		# 		row.mode_of_payment = mode.name
		# 		row.total = total_payment

		payments_entry = frappe.get_all("Payment Entry", ["paid_amount"], filters = {"posting_date": self.billing_date, "docstatus": 1})
		
		if len(sales_invoice) > 0 or  len(payments_entry) > 0:
			billing_series = sales_invoice[0].numeration[0:10]
			final_document = sales_invoice[0].numeration[11:19]
			total_credit = 0

			for sales in sales_invoice:
				initial_document = sales.numeration[11:19]
				sale_total = 0
				for mode in mode_pay:
					total_payment = 0
					payments_entry = frappe.get_all("Payment Entry", ["name", "paid_amount"], filters = {"posting_date": self.billing_date, "mode_of_payment": mode.name, "docstatus": 1})
					
					for payment in payments_entry:
						references = frappe.get_all("Payment Entry Reference", filters = {"reference_name": sales.name, "parent": payment.name})

						if len(references) > 0:
							total_payment += payment.paid_amount							
						
					grand_total += total_payment
					exempt += total_payment
					total_exempt += total_payment			
					
							
					registers_totals = frappe.get_all("Details totals proof of daily sales", ["name"], filters = {"mode_of_payment": mode.name, "parent": self.name})

					if len(registers_totals) > 0:
						frappe.msgprint("total:{}".format(total_payment))
						doc = frappe.get_doc("Details totals proof of daily sales", registers_totals[0].name)
						doc.total = total_payment
						doc.save()						
					else:
						frappe.msgprint("total:{} modo de pago: {}".format(total_payment, mode.name))
						row = self.append("totals_table", {})
						row.mode_of_payment = mode.name
						row.total = total_payment

					sale_total += total_payment
				
				if sale_total < sales.total:
					frappe.msgprint("{} {}".format(total_credit, sale_total))
					total_credit += sales.total - sale_total

			grand_total += total_credit
			exempt += total_credit
			total_exempt += total_credit	

			credit_register = frappe.get_all("Details totals proof of daily sales", ["name"], filters = {"mode_of_payment": "Credit", "parent": self.name})

			if len(credit_register) > 0:
				doccredit = frappe.get_doc("Details totals proof of daily sales", credit_register[0].name)
				doc.total = total_credit
				doc.save()
			else:
				rowcredit = self.append("totals_table", {})
				rowcredit.mode_of_payment = "Credit"
				rowcredit.total = total_credit
				
			frappe.msgprint("total_credit:{} ".format(total_credit))
		
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

		self.total_base_isv15 = total_base_isv15
		self.total_base_isv18 = total_base_isv18
		self.total_exempt = total_exempt
		self.total_isv15 = total_isv15
		self.total_isv18 = total_isv18
		self.grand_total = grand_total