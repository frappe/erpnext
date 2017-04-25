# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_lead_data(filters, "Campaign Name")
	return columns, data
	
def get_columns():
	return [
		_("Campaign Name") + ":data:130", 
		_("Lead Count") + ":Int:80",
		_("Opp Count") + ":Int:80",
		_("Quot Count") + ":Int:80", 
		_("Order Count") + ":Int:100",
		_("Order Value") + ":Float:100",
		_("Opp/Lead %") + ":Float:100",
		_("Quot/Lead %") + ":Float:100",
		_("Order/Quot %") + ":Float:100"
	]
	
def get_lead_data(filters, based_on):
	based_on_field = frappe.scrub(based_on)
	conditions = get_filter_conditions(filters)
	
	lead_details = frappe.db.sql("""
		select {based_on_field}, name
		from `tabLead` 
		where {based_on_field} is not null and {based_on_field} != '' {conditions} 
	""".format(based_on_field=based_on_field, conditions=conditions), filters, as_dict=1)
	
	lead_map = frappe._dict()
	for d in lead_details:
		lead_map.setdefault(d.get(based_on_field), []).append(d.name)
	
	data = []
	for based_on_value, leads in lead_map.items():
		row = {
			based_on: based_on_value,
			"Lead Count": len(leads)
		}
		row["Quot Count"]= get_lead_quotation_count(leads)
		row["Opp Count"] = get_lead_opp_count(leads)
		row["Order Count"] = get_quotation_ordered_count(leads)
		row["Order Value"] = get_order_amount(leads)
		
		row["Opp/Lead %"] = row["Opp Count"] / row["Lead Count"] * 100
		row["Quot/Lead %"] = row["Quot Count"] / row["Lead Count"] * 100
		
		row["Order/Quot %"] = row["Order Count"] / (row["Quot Count"] or 1) * 100
			
		data.append(row)
		
	return data
	
def get_filter_conditions(filters):
	conditions=""
	if filters.from_date:
		conditions += " and date(creation) >= %(from_date)s"
	if filters.to_date:
		conditions += " and date(creation) <= %(to_date)s"
	
	return conditions
	
def get_lead_quotation_count(leads):
	return frappe.db.sql("""select count(name) from `tabQuotation` 
		where lead in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]
	
def get_lead_opp_count(leads):
	return frappe.db.sql("""select count(name) from `tabOpportunity` 
	where lead in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]
	
def get_quotation_ordered_count(leads):
	return frappe.db.sql("""select count(name) 
		from `tabQuotation` where status = 'Ordered'
		and lead in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]
	
def get_order_amount(leads):
	return frappe.db.sql("""select sum(base_net_amount) 
		from `tabSales Order Item`
		where prevdoc_docname in (
			select name from `tabQuotation` where status = 'Ordered' 
			and lead in (%s)
		)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]