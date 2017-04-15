# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data
	
def get_columns():
	return [
		_("Lead") + ":Link/Lead:100",
		_("Reference Document") + "::150",
		_("Reference Name") + ":Dynamic Link/"+_("Reference Document")+":120",
		_("Message") + ":Data:200",
		_("Last Communication Date") + ":Date:180"
	]

def get_data(filters):
	lead_details = []
	lead_filters = get_lead_filters(filters)
	
	for lead in frappe.get_all('Lead', fields = ['name'], filters=lead_filters):
		data = frappe.db.sql("""
			select 
				foo.lead,`tabCommunication`.reference_doctype, `tabCommunication`.reference_name, 
				`tabCommunication`.content, `tabCommunication`.communication_date
			from 
				(
					(select name, lead from `tabOpportunity` where lead = %(lead)s) 
				union 
					(select name, lead from `tabQuotation` where lead = %(lead)s)
				union
					(select name, lead from `tabIssue` where lead = %(lead)s and status!='Closed')
				union
					(select %(lead)s, %(lead)s)
				) 
				as foo, `tabCommunication` 
			where 
				`tabCommunication`.reference_name = foo.name and
				`tabCommunication`.communication_medium in ('Email', 'SMS', 'Phone')
			order by 
				foo.lead, `tabCommunication`.creation desc limit %(limit)s""", 
			{'lead': lead.name, 'limit': filters.get('no_of_interaction')})

		for lead_info in data:
			lead_details.append(list(lead_info))

	return lead_details
	
def get_lead_filters(filters):
	lead_filters = [["status", "!=", "Converted"]]
	if filters.get('lead'):
		lead_filters.append(["name", "=", filters.get('lead')])
	return lead_filters