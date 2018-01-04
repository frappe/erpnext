# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.accounts.report.non_billed_report import get_ordered_to_be_billed_data

def execute(filters=None):
	columns = get_column()
	args = get_args()
	data = get_ordered_to_be_billed_data(args)
	return columns, data

def get_column():
	return [
		_("Sales Order") + ":Link/Sales Order:120", _("Date") + ":Date:100",
		_("Suplier") + ":Link/Customer:120", _("Customer Name") + "::120",
		_("Project") + ":Link/Project:120", _("Item Code") + ":Link/Item:120", 
		_("Amount") + ":Currency:100", _("Billed Amount") + ":Currency:100", _("Pending Amount") + ":Currency:100",
		_("Item Name") + "::120", _("Description") + "::120", _("Company") + ":Link/Company:120",
	]

def get_args():
	return {'doctype': 'Sales Order', 'party': 'customer', 
		'date': 'transaction_date', 'order': 'transaction_date', 'order_by': 'asc'}