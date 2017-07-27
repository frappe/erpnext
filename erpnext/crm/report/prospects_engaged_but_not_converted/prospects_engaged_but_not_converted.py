# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import add_days, now

def execute(filters=None):
	columns, data = [], []
	set_defaut_value_for_filters(filters)
	columns = get_columns()
	data = get_data(filters)

	return columns, data

def set_defaut_value_for_filters(filters):
	if not filters.get('no_of_interaction'): filters["no_of_interaction"] = 1
	if not filters.get('lead_age'): filters["lead_age"] = 60

def get_columns():
	return [
		_("Lead") + ":Link/Lead:100",
		_("Name") + "::100",
		_("Organization") + "::100",
		_("Reference Document") + "::150",
		_("Reference Name") + ":Dynamic Link/"+_("Reference Document")+":120",
		_("Last Communication") + ":Data:200",
		_("Last Communication Date") + ":Date:180"
	]

def get_data(filters):
	lead_details = []
	lead_filters = get_lead_filters(filters)

	for lead in frappe.get_all('Lead', fields = ['name', 'lead_name', 'company_name'], filters=lead_filters):
		data = frappe.db.sql("""
			select 
				`tabCommunication`.reference_doctype, `tabCommunication`.reference_name, 
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
				as ref_document, `tabCommunication`
			where
				`tabCommunication`.reference_name = ref_document.name and
				`tabCommunication`.sent_or_received = 'Received'
			order by
				ref_document.lead, `tabCommunication`.creation desc limit %(limit)s""",
			{'lead': lead.name, 'limit': filters.get('no_of_interaction')})

		for lead_info in data:
			lead_data = [lead.name, lead.lead_name, lead.company_name] + list(lead_info)
			lead_details.append(lead_data)

	return lead_details

def get_lead_filters(filters):
	lead_creation_date = get_creation_date_based_on_lead_age(filters)
	lead_filters = [["status", "!=", "Converted"], ["creation", ">", lead_creation_date]]

	if filters.get('lead'):
		lead_filters.append(["name", "=", filters.get('lead')])
	return lead_filters

def get_creation_date_based_on_lead_age(filters):
	return add_days(now(), (filters.get('lead_age') * -1))