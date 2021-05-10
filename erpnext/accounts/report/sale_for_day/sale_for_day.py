# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Range") + "::240", _("Exempts Sales") + ":Currency:120", _("Exonerated") + ":Currency:120", _("Taxed Sales 15%") + ":Currency:120", _("I.S.V 15%") + ":Currency:120", _("Taxed Sales 18%") + ":Currency:120", _("I.S.V 18%") + ":Currency:120", _("Total") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)
	serie = filters.get("prefix")
	split_serie = serie.split("-")
	serie_final = ("{}-{}-{}").format(split_serie[0],split_serie[1],split_serie[2])

	salary_slips = frappe.get_all("Sales Invoice", ["name", "naming_series", "creation_date", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total"], filters = conditions,  order_by = "name asc")

	date_actual = from_date

	while date_actual <= to_date:
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
			date_validate = salary_slip.creation_date.strftime('%Y-%m-%d')
			if date == date_validate:
				if cont == 0:
					split_initial_range = salary_slip.name.split("-")
					initial_range = split_initial_range[3]

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

		row = [creation_date, serie_final, final_range, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"creation_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "naming_series": "{}"'.format(filters.get("prefix"))
	conditions += '}'

	return conditions