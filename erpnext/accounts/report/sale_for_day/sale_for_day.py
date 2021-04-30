# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Authorized Range") + "::240", _("Exempts Sales") + ":Currency:120", _("Taxed Sales 15%") + ":Currency:120", _("I.S.V 15%") + ":Currency:120", _("Taxed Sales 18%") + ":Currency:120", _("I.S.V 18%") + ":Currency:120", _("Total") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Sales Invoice", ["naming_series", "posting_date", "authorized_range", "total_exempt", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total"], filters = conditions)

	for salary_slip in salary_slips:
		if len(dates) == 0:
			register = salary_slip.posting_date
			dates.append(register)
		else:
			new_date = False
			if salary_slip.posting_date in dates:
				new_date = False
			else:
				register = salary_slip.posting_date
				dates.append(register)

	dates_reverse = sorted(dates, reverse=False)
	
	for date in dates_reverse:
		split_date = str(date).split("T")[0].split("-")
		posting_date = "-".join(reversed(split_date))
		serie = filters.get("prefix")
		authorized_range = ""
		total_exempt = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0

		for salary_slip in salary_slips:
			if date == salary_slip.posting_date:
				total_exempt += salary_slip.total_exempt
				taxed_sales15 += salary_slip.taxed_sales15
				isv15 += salary_slip.isv15
				taxed_sales18 += salary_slip.taxed_sales18
				isv18 = salary_slip.isv18
				authorized_range = salary_slip.authorized_range
		
		grand_total = taxed_sales15 + isv15 + taxed_sales18 + isv18 + total_exempt

		row = [posting_date, serie, authorized_range, total_exempt, taxed_sales15, isv15, taxed_sales18, isv18, grand_total]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "naming_series": "{}"'.format(filters.get("prefix"))
	conditions += '}'

	return conditions