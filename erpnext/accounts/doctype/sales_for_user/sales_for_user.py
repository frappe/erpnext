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

		salary_slips = frappe.get_all("Sales Invoice", ["name","outstanding_amount", "total_advance", "creation", "status","naming_series", "creation_date", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total", "partial_discount", "discount_amount", "total"], filters = condition,  order_by = "name asc")

		date_actual = self.start_date

		# for salary in salary_slips:
		# 	payments = frappe.get_all("Sales Invoice Payment", ["*"], filters = {"parent": salary.name})
			
		# 	for payment in payments:
		# 		if payment.mode_of_payment == "Efectivo":
		# 			cash += payment.amount
		# 		if payment.mode_of_payment == "Tarjetas de credito":
		# 			cards += payment.amount

		# 	advances += salary.total_advance

		sales_person_cols = ""
		sales_team_table = ""

		# si_list = frappe.db.sql("""
		# 	select
		# 		`tabSales Invoice Item`.parenttype, `tabSales Invoice Item`.parent,
		# 		`tabSales Invoice`.posting_date, `tabSales Invoice`.posting_time,
		# 		`tabSales Invoice`.project, `tabSales Invoice`.update_stock,
		# 		`tabSales Invoice`.customer, `tabSales Invoice`.customer_group,
		# 		`tabSales Invoice`.territory, `tabSales Invoice Item`.item_code,
		# 		`tabSales Invoice Item`.item_name, `tabSales Invoice Item`.description,
		# 		`tabSales Invoice Item`.warehouse, `tabSales Invoice Item`.item_group,
		# 		`tabSales Invoice Item`.brand, `tabSales Invoice Item`.dn_detail,
		# 		`tabSales Invoice Item`.delivery_note, `tabSales Invoice Item`.stock_qty as qty,
		# 		`tabSales Invoice Item`.base_net_rate, `tabSales Invoice Item`.base_net_amount,
		# 		`tabSales Invoice Item`.name as "item_row", `tabSales Invoice`.is_return
		# 		{sales_person_cols}
		# 	from
		# 		`tabSales Invoice` inner join `tabSales Invoice Item`
		# 			on `tabSales Invoice Item`.parent = `tabSales Invoice`.name
		# 		{sales_team_table}
		# 	where
		# 		`tabSales Invoice`.docstatus=1 and `tabSales Invoice`.is_opening!='Yes' {conditions} {match_cond}
		# 	order by
		# 		`tabSales Invoice`.posting_date desc, `tabSales Invoice`.posting_time desc"""
		# 	.format(conditions=conditions, sales_person_cols=sales_person_cols,
		# 		sales_team_table=sales_team_table, match_cond = get_match_cond('Sales Invoice')), as_dict=1)

		# for row1 in si_list:
		# 	hello = 125

		da_string = date_actual.split(" ")

		# da = datetime.datetime.strptime(da_string[0], '%d/%m/%Y')

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
			discount = 0
			partial_discount = 0
			grand_total = 0
			gross = 0

			for salary_slip in salary_slips:
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

					split_final_range = salary_slip.name.split("-")
					final_range = split_final_range[3]
					cont += 1

					payments = frappe.get_all("Sales Invoice Payment", ["*"], filters = {"parent": salary_slip.name})
			
					for payment in payments:
						if payment.mode_of_payment == "Efectivo":
							cash += payment.amount
						if payment.mode_of_payment == "Tarjetas de credito":
							cards += payment.amount

					advances += salary_slip.total_advance
			final_range = "{}-{}".format(initial_range, final_range)

			# row1 = [creation_date, serie_final, final_range, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]

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

		self.total_cash = cash
		self.total_cards = cards
		self.total_advances_applied = advances
		total_income = cash + cards + total_monetary

		self.total_income = total_income
		self.total_credit = outstanding_amount

		self.total_invoice = operations
		self.total_operations = operations

	def return_filters(self):
		conditions = ''

		conditions += "{"
		conditions += '"creation": ["between", ["{}", "{}"]]'.format(self.start_date, self.final_date)
		# conditions += '"creation": [">=", "{}"]'.format(self.start_date)
		# conditions += ', "creation": ["<=", "{}"]'.format(self.final_date)
		conditions += ', "naming_series": "{}"'.format(self.prefix)
		conditions += ', "company": "{}"'.format(self.company)
		# conditions += '"posting_time": ["between", ["{}", "{}"]]'.format(self.start_hour, self.final_hour)
		# conditions += ', "posting_time": [">=", "{}"]'.format(self.start_hour)
		# conditions += ', "posting_time": ["<=", "{}"]'.format(self.final_hour)
		if self.user != None:
			conditions += ', "cashier": "{}"'.format(self.user)
		# conditions += ', "is_pos": 1'.format(self.user)
		conditions += '}'

		return conditions

	def return_filters_sql(self):
		conditions = ''

		# conditions += "{"
		# conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(self.start_date, self.final_date)
		# conditions += ', "naming_series": "{}"'.format(self.prefix)
		# conditions += ', "company": "{}"'.format(self.company)
		# conditions += ', "posting_time": [">", "{}"]'.format(self.start_hour)
		# conditions += ', "posting_time": ["<", "{}"]'.format(self.final_hour)
		# conditions += ', "cashier": "{}"'.format(self.user)
		# conditions += '}'

		conditions += ' and company = {}'.format(self.company)
		conditions += ' and posting_date >= {}'.format(self.start_date)
		conditions += ' and posting_date <= {}'.format(self.final_date)
		conditions += ' and naming_series = {}'.format(self.prefix)
		conditions += ' and posting_time >= {}'.format(self.start_hour)
		conditions += ' and posting_time <= {}'.format(self.final_hour)
		if self.user != None:
			conditions += ' and cashier = {}'.format(self.user)

		return conditions
