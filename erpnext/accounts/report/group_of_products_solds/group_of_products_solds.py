# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Item Group") + ":Link/Item Group:100", _("Qty") + ":Int:120", _("Rate") + ":Currency/currency:120",_("Amount") + ":Currency/currency:120"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	dates = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	invoices = frappe.get_all("Sales Invoice", ["*"], filters = conditions)
	products = []
	categories = []

	for invoice in invoices:
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": invoice.name})

		for item in items:
			products.append(item)
			if item.item_group in categories:
				exist = True
			else:
				categories.append(item.item_group)

	for item_group in categories:
		group = item_group
		qty = 0
		base_net_rate = 0
		base_net_amount = 0
		for product in products:
			if item_group == product.item_group:
				qty += product.qty
				base_net_rate += product.base_net_rate
				base_net_amount += product.base_net_amount
		
		row = [group, qty, base_net_rate, base_net_amount]
		data.append(row)
			

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	if filters.get("serie"): conditions += ', "name": "{}"'.format(filters.get("serie"))
	conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions