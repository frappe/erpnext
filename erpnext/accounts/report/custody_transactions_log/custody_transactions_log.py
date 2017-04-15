# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
	# frappe.msgprint(filters.get("fixed_asset"))
	columns = [
	_("Fixed Asset") + ":Data:100",
	_("Asset Category") + ":Data:100",
	_("Item Code") + ":Data:100",
	_("Employee Name") + ":Data:200",
	_("Employee Designation") + ":Data:200",	
	_("Employee Department") + ":Data:200",
	_("Status") + ":Data:200",	
	]
	
	data = frappe.get_list("Fixed Asset Custody", fields=["fixed_asset", "asset_category", "item_code", "employee_name", "employee_designation", "employee_department", "docstatus"], filters={"fixed_asset":filters.get("fixed_asset")}, as_list=1)
	datalist = list(map(list, data))
	for i, d in enumerate(datalist):
		if d[6]==0:
			datalist[i][6]="Draft"
		elif d[6]==1:
			datalist[i][6]="Submitted"
		elif d[6]==2:
			datalist[i][6]="Cancelled"

	return columns, datalist
