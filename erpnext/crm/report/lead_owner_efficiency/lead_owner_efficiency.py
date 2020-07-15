# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.crm.report.campaign_efficiency.campaign_efficiency import get_lead_data

def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_lead_data(filters, "Lead Owner")
	return columns, data

def get_columns():
	return [
		{
			"fieldname": "lead_owner",
			"label": _("Lead Owner"),
			"fieldtype": "Link",
			"options": "User",
			"width": "130"
		},
		{
			"fieldname": "lead_count",
			"label": _("Lead Count"),
			"fieldtype": "Int",
			"width": "80"
		},
		{
			"fieldname": "opp_count",
			"label": _("Opp Count"),
			"fieldtype": "Int",
			"width": "80"
		},
		{
			"fieldname": "quot_count",
			"label": _("Quot Count"),
			"fieldtype": "Int",
			"width": "80"
		},
		{
			"fieldname": "order_count",
			"label": _("Order Count"),
			"fieldtype": "Int",
			"width": "100"
		},
		{
			"fieldname": "order_value",
			"label": _("Order Value"),
			"fieldtype": "Float",
			"width": "100"
		},
		{
			"fieldname": "opp_lead",
			"label": _("Opp/Lead %"),
			"fieldtype": "Float",
			"width": "100"
		},
		{
			"fieldname": "quot_lead",
			"label": _("Quot/Lead %"),
			"fieldtype": "Float",
			"width": "100"
		},
		{
			"fieldname": "order_quot",
			"label": _("Order/Quot %"),
			"fieldtype": "Float",
			"width": "100"
		}
	]
