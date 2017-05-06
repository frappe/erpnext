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
		_("Lead Owner") + ":Data:130", 
		_("Lead Count") + ":Int:80",
		_("Opp Count") + ":Int:80",
		_("Quot Count") + ":Int:80", 
		_("Order Count") + ":Int:100",
		_("Order Value") + ":Float:100",
		_("Opp/Lead %") + ":Float:100",
		_("Quot/Lead %") + ":Float:100",
		_("Order/Quot %") + ":Float:100"
	]