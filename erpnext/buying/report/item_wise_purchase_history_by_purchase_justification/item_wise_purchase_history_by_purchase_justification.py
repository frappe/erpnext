# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Item Code") + "::240", _("Item Name") + "::240", _("Item Group") + "::240", _("Description") + "::240", _("Qty") + "::240", _("UOM") + "::240", _("Rate") + ":Currency:120", _("Amount") + ":Currency:120", _("Purchase Order") + "::240", _("Transaction Date") + "::240", _("Supplier") + "::240" ,_("Supplier Name") + "::240", _("Project") + "::240", _("Received Amount") + "::240", _("Company") + "::240"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	purchase_orders = frappe.get_all("Purchase Order", ["*"], filters = conditions)

	for order in purchase_orders:
		items = frappe.get_all("Purchase Order Item", ["*"], filters = {"parent": order.name})

		for item in items:
			row = [item.item_code, item.item_name, item.item_group, item.description, item.qty, item.uom, item.rate, item.amount, order.name, order.transaction_date, order.supplier, order.supplier, "", 0, order.company]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"transaction_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "justification_purchase": "{}"'.format(filters.get("purchase_justification"))
	conditions += ' ,"docstatus": 1'
	conditions += '}'

	return conditions