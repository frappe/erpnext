# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	# columns, data = [], []
	columns = [
	_("Fixed Asset") + ":Data:100",
	_("Asset Category") + ":Data:100",
	_("Item Code") + ":Data:100",
	_("Employee Name") + ":Data:200",
	_("Employee Designation") + ":Data:200",	
	_("Employee Department") + ":Data:200"	
	]
	# data= []	


	data = frappe.get_list("Fixed Asset Custody", fields=["fixed_asset", "asset_category", "item_code", "employee_name", "employee_designation", "employee_department"], filters={"docstatus":1}, as_list=1)
	return columns, data
