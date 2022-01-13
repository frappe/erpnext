# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Serie") + "::240", _("Item Code") + "::240", _("Item Name") + "::240", _("Item Group") + "::240" ,_("Qty") + "::240"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	inventories = frappe.get_all("Inventory Download", ["*"], filters = conditions)

	for inventory in inventories:
		items = frappe.get_all("Inventory Download Detail", ["*"], filters = {"parent": inventory.name})

		for item in items:
			row = [inventory.creation_date, inventory.name, item.item_code, item.item_name, item.item_group, item.qty]
			data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"creation_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	if filters.get("company"):
		conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("reason_for_download"):
		conditions += ', "reason_for_download": "{}"'.format(filters.get("reason_for_download"))
	if filters.get("warehouse"):
		conditions += ', "warehouse": "{}"'.format(filters.get("warehouse"))
	if filters.get("download_area"):
		conditions += ', "download_area": "{}"'.format(filters.get("download_area"))
	conditions += '}'

	return conditions