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
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	salary_slips = frappe.get_all("Sales Invoice", ["posting_date", "authorized_range", "total_exempt", "isv15", "isv18", "grand_total"], filters = conditions)

	row = ["25-05-2021", "0246454", "100-1000", 25, 1, 1, 2, 2, 31]
	data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	if filters.get("from_date"): conditions += '"posting_date": [">=", "{}"], '.format(from_date)
	if filters.get("to_date"): conditions += '"posting_date": ["<=", "{}"]'.format(to_date)
	conditions += '}'

	return conditions