# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Disount Reason") + "::240", _("Gross Amount") + ":Currency:120", _("Exempts Sales") + ":Currency:120", _("Exonerated") + ":Currency:120", _("Taxed Sales 15%") + ":Currency:120", _("I.S.V 15%") + ":Currency:120", _("Taxed Sales 18%") + ":Currency:120", _("I.S.V 18%") + ":Currency:120", _("Partial Discount") + ":Currency:120" ,_("Discount Amount") + ":Currency:120", _("Total") + ":Currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	groups = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Sales Invoice", ["name", "status","naming_series", "creation_date", "posting_date", "authorized_range", "total_exempt", "total_exonerated", "taxed_sales15", "isv15", "taxed_sales18", "isv18", "grand_total", "discount_amount", "partial_discount", "discount_reason", "total"], filters = conditions,  order_by = "name asc")
	
	for salary in salary_slips:
		if salary.discount_reason in groups:
			exist = True
		else:
			groups.append(salary.discount_reason)

	for group in groups:
		total_exempt = 0
		gross = 0
		total_exonerated = 0
		taxed_sales15 = 0
		isv15 = 0
		taxed_sales18 = 0
		isv18 = 0
		partial_discount = 0
		discount_amount = 0
		grand_total = 0

		for salary_slip in salary_slips:
			if group == salary_slip.discount_reason:			
				total_exempt += salary_slip.total_exempt
				gross += salary_slip.total
				total_exonerated += salary_slip.total_exonerated
				taxed_sales15 += salary_slip.taxed_sales15
				isv15 += salary_slip.isv15
				taxed_sales18 += salary_slip.taxed_sales18
				isv18 += salary_slip.isv18
				partial_discount += salary_slip.partial_discount
				discount_amount += salary_slip.discount_amount
				
				grand_total += salary_slip.grand_total

		row = [group, gross, total_exempt, total_exonerated, taxed_sales15, isv15, taxed_sales18, isv18, partial_discount, discount_amount, grand_total]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "naming_series": "{}"'.format(filters.get("prefix"))
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("discount_reason"):
		conditions += ', "discount_reason": "{}"'.format(filters.get("discount_reason"))
	conditions += ', "discount_amount": [">", 0]'
	conditions += '}'

	return conditions