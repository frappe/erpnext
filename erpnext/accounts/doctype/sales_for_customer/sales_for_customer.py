# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
import datetime

class SalesForCustomer(Document):
	def on_update(self):
		self.return_data()

	def return_data(self):
		outstanding_amount, cash, cards, adv_app, total_monetary, total_income, total_utility, total_exempt_sales = 0,0,0,0,0,0,0,0
		dates = []
		conditions = self.return_filters()
		serie = self.prefix
		split_serie = serie.split("-")
		serie_final = ("{}-{}-{}").format(split_serie[0],split_serie[1],split_serie[2])

		salary_slips = frappe.get_all("Sales Invoice", ["name", "outstanding_amount", "total_advance", "status","naming_series", "creation_date", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total"], filters = conditions,  order_by = "name asc")

		self.total_invoice = len(salary_slips)
		self.total_operations = len(salary_slips)
		date_actual = self.start_date

		while date_actual <= self.final_date:
			register = date_actual
			dates.append(register)

			date_split = date_actual.split("-")
			date_format = ("{}/{}/{}").format(date_split[2], date_split[1], date_split[0])

			cast_date = datetime.datetime.strptime(date_format, '%d/%m/%Y')
			tomorrow = cast_date + datetime.timedelta(days=1)
			date_actual = tomorrow.strftime('%Y-%m-%d')

		dates_reverse = sorted(dates, reverse=False)
	
		for date in dates_reverse:
			split_date = str(date).split("T")[0].split("-")
			creation_date = "-".join(reversed(split_date))		
			initial_range = ""
			final_range = ""
			authorized_range = ""
			total_exempt = 0
			total_exonerated = 0
			taxed_sales15 = 0
			isv15 = 0
			taxed_sales18 = 0
			isv18 = 0
			cont = 0

			for salary_slip in salary_slips: 
				date_validate = salary_slip.posting_date.strftime('%Y-%m-%d')
				if date == date_validate and salary_slip.status != "Return":
					if cont == 0:
						split_initial_range = salary_slip.name.split("-")
						initial_range = split_initial_range[3]

					outstanding_amount += salary_slip.outstanding_amount
					adv_app += salary_slip.total_advance
					total_exempt += salary_slip.total_exempt
					total_exonerated += salary_slip.total_exonerated
					taxed_sales15 += salary_slip.taxed_sales15
					isv15 += salary_slip.isv15
					taxed_sales18 += salary_slip.taxed_sales18
					isv18 = salary_slip.isv18
					authorized_range = salary_slip.authorized_range

					split_final_range = salary_slip.name.split("-")
					final_range = split_final_range[3]
					cont += 1
		
			grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt
			final_range = "{}-{}".format(initial_range, final_range)

			# row1 = [creation_date, serie_final, final_range, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]

			details = frappe.get_all("Sales For Customer Detail", ["name"], filters = {"parent": self.name})

			for detail in details:
				frappe.delete_doc("Sales For Customer Detail", detail.name)

			row = self.append("details", {})
			row.date = creation_date
			row.serie = serie_final
			row.range = final_range
			row.exempts_sales = total_exempt
			row.exonerated = total_exonerated
			row.taxed_sales_15 = taxed_sales15
			row.isv15 = isv15
			row.taxed_sales_18 = taxed_sales18
			row.isv18 = isv18
			row.total = grand_total

			self.total_exempt_sales = 0
			self.total_exempt_sales += total_exempt
		
		total_income = cash + cards + total_monetary

		self.total_income = total_income
		self.total_credit = outstanding_amount

	def return_filters(self):
		conditions = ''	

		conditions += "{"
		conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(self.start_date, self.final_date)
		conditions += ', "naming_series": "{}"'.format(self.prefix)
		conditions += ', "company": "{}"'.format(self.company)
		conditions += ', "posting_time": [">", "{}"]'.format(self.start_hour)
		conditions += ', "posting_time": ["<", "{}"]'.format(self.final_hour)
		conditions += ', "cashier": "{}"'.format(self.user)
		conditions += '}'

		return conditions
