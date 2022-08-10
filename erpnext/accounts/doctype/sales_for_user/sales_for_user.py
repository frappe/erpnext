# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime
from erpnext.controllers.queries import get_match_cond

class SalesForUser(Document):
	def validate(self):
		if self.docstatus == 0:
			self.return_data()

	def return_data(self):
		outstanding_amount, cash, cards, adv_app, total_monetary, total_income, total_utility, total_exempt_sales, advances = 0,0,0,0,0,0,0,0,0
		dates = []
		condition = self.return_filters()
		operations = 0
		serie = self.prefix
		split_serie = serie.split("-")
		serie_final = ("{}-{}-{}").format(split_serie[0],split_serie[1],split_serie[2])

		salary_slips = frappe.get_all("Sales Invoice", ["*"], filters = condition,  order_by = "name asc")

		date_actual = self.start_date

		da_string = date_actual.split(" ")

		while da_string[0] <= self.final_date:
			register = da_string[0]
			dates.append(register)

			date_split = da_string[0].split("-")
			date_format = ("{}/{}/{}").format(date_split[2], date_split[1], date_split[0])

			cast_date = datetime.datetime.strptime(date_format, '%d/%m/%Y')
			tomorrow = cast_date + datetime.timedelta(days=1)
			da_string[0] = tomorrow.strftime('%Y-%m-%d')

		dates_reverse = sorted(dates, reverse=False)

		self.total_exempt_sales = 0

		modes = []

		values_modes = []

		modes_payments = frappe.get_all("Mode of Payment", ["*"])

		for mode_payment in modes_payments:
			modes.append(mode_payment.name)
			values_modes.append(0)
		
		conditions_arr = []

		values_conditions = []

		total_cont = 0

		conditions_terms = frappe.get_all("Terms and Conditions", ["*"])

		for condtions_term in conditions_terms:
			conditions_arr.append(condtions_term.name)
			values_conditions.append(0)

		for date in dates_reverse:
			split_date = str(date).split("T")[0].split("-")
			creation_date = "-".join(reversed(split_date))
			initial_range = ""
			final_range = ""
			total_exempt = 0
			total_exonerated = 0
			taxed_sales15 = 0
			isv15 = 0
			taxed_sales18 = 0
			isv18 = 0
			cont = 0
			discount = 0
			partial_discount = 0
			grand_total = 0
			gross = 0
			change_amount = 0

			for salary_slip in salary_slips:
				if salary_slip.status != "Cancelled":
					date_validate = salary_slip.creation.strftime('%Y-%m-%d %H:%M:%S')
					dates_validate = salary_slip.posting_date.strftime('%Y-%m-%d')
					if date == dates_validate and salary_slip.status != "Return" and date_validate >= self.start_date and date_validate <= self.final_date:
						operations += 1
						if cont == 0:
							split_initial_range = salary_slip.name.split("-")
							initial_range = split_initial_range[3]

						outstanding_amount += salary_slip.outstanding_amount
						adv_app += salary_slip.total_advance
						total_exempt += salary_slip.total_exempt
						gross += salary_slip.total
						total_exonerated += salary_slip.total_exonerated
						taxed_sales15 += salary_slip.taxed_sales15
						isv15 += salary_slip.isv15
						taxed_sales18 += salary_slip.taxed_sales18
						discount += salary_slip.discount_amount
						partial_discount += salary_slip.partial_discount
						grand_total += salary_slip.grand_total
						isv18 = salary_slip.isv18
						authorized_range = salary_slip.authorized_range
						change_amount += salary_slip.paid_amount - salary_slip.change_amount

						split_final_range = salary_slip.name.split("-")
						final_range = split_final_range[3]
						cont += 1

						payments = frappe.get_all("Sales Invoice Payment", ["*"], filters = {"parent": salary_slip.name})
				
						for payment in payments:
							if payment.mode_of_payment == "Efectivo":
								cash += payment.amount
							if payment.mode_of_payment == "Tarjetas de credito":
								cards += payment.amount

							conta = 0

							for mode in modes:
								if payment.mode_of_payment == mode:
									values_modes[conta] += payment.amount
								
								conta += 1

						conta = 0

						for cond in conditions_arr:
							if salary_slip.tc_name == cond:
								values_conditions[conta] += salary_slip.grand_total

								if cond == "Contado":
									total_cont += salary_slip.grand_total
							
							conta += 1

						advances += salary_slip.total_advance
					
			final_range = "{}-{}".format(initial_range, final_range)

			details = frappe.get_all("Sales For User Detail", ["name"], filters = {"parent": self.name})

			for detail in details:
				frappe.delete_doc("Sales For User Detail", detail.name)

			row = self.append("details", {})
			row.date = creation_date
			row.serie = serie_final
			row.range = final_range
			row.gross = gross
			row.exempts_sales = grand_total
			row.exonerated = total_exonerated
			row.taxed_sales_15 = taxed_sales15
			row.isv15 = isv15
			row.taxed_sales_18 = taxed_sales18
			row.isv18 = isv18
			row.total = grand_total
			row.discount = discount
			row.partial_discount = partial_discount

			self.total_exempt_sales += grand_total

		payment_details = frappe.get_all("Sales Invoice Payment Detail", ["name"], filters = {"parent": self.name})

		for pay_det in payment_details:
			frappe.delete_doc("Sales Invoice Payment Detail", pay_det.name)

		conta = 0

		for mode in modes:
			row = self.append("payments", {})
			row.mode_of_payment = mode
			row.amount = values_modes[conta]

			conta += 1
		
		conditions_details = frappe.get_all("Terms and Conditions Detail", ["name"], filters = {"parent": self.name})

		for condition_detail in conditions_details:
			frappe.delete_doc("Terms and Conditions Detail", condition_detail.name)

		conta = 0

		for con in conditions_arr:
			row = self.append("terms_and_conditions", {})
			row.terms_and_conditions = con
			row.amount = values_conditions[conta]

			conta += 1

		payment_entry = 0

		if self.user != None:
			con_entry = self.filters_entries()
			entries = frappe.get_all("Payment Entry", ["paid_amount"], filters = con_entry)

			for entry in entries:
				payment_entry += entry.paid_amount
		
		self.total_cash = cash
		self.actual_cash = change_amount
		self.total_cards = cards
		self.total_advances_applied = advances
		total_income = total_cont + payment_entry

		self.total_income = total_income
		self.total_credit = outstanding_amount

		self.total_invoice = operations
		self.total_operations = operations
		self.payment_entry = payment_entry
	
	def filters_entries(self):
		conditions = ''

		conditions += "{"
		conditions += '"creation": ["between", ["{}", "{}"]]'.format(self.start_date, self.final_date)
		conditions += ', "user": "{}"'.format(self.user)
		conditions += '}'

		return conditions

	def return_filters(self):
		conditions = ''

		conditions += "{"
		conditions += '"creation": ["between", ["{}", "{}"]]'.format(self.start_date, self.final_date)
		conditions += ', "naming_series": "{}"'.format(self.prefix)
		conditions += ', "company": "{}"'.format(self.company)
		conditions += ', "status": ["!=", "Canceled"]'
		if self.user != None:
			conditions += ', "cashier": "{}"'.format(self.user)
		conditions += '}'

		return conditions