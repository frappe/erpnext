# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
	columns, data = [], []
	columns=get_columns("Campaign Name")
	data=get_lead_data(filters or {}, "Campaign Name")
	return columns, data

def get_columns(based_on):
	return [
		{
			"fieldname": frappe.scrub(based_on),
			"label": _(based_on),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "lead_count",
			"label": _("Lead Count"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "opp_count",
			"label": _("Opp Count"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "quot_count",
			"label": _("Quot Count"),
			"fieldtype": "Int",
			"width": 80
		},
		{
			"fieldname": "order_count",
			"label": _("Order Count"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "order_value",
			"label": _("Order Value"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "opp_lead",
			"label": _("Opp/Lead %"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "quot_lead",
			"label": _("Quot/Lead %"),
			"fieldtype": "Float",
			"width": 100
		},
		{
			"fieldname": "order_quot",
			"label": _("Order/Quot %"),
			"fieldtype": "Float",
			"width": 100
		}
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
			based_on_field: based_on_value,
			"lead_count": len(leads)
		}
		row["quot_count"]= get_lead_quotation_count(leads)
		row["opp_count"] = get_lead_opp_count(leads)
		row["order_count"] = get_quotation_ordered_count(leads)
		row["order_value"] = get_order_amount(leads) or 0

		row["opp_lead"] = flt(row["opp_count"]) / flt(row["lead_count"] or 1.0) * 100.0
		row["quot_lead"] = flt(row["quot_count"]) / flt(row["lead_count"] or 1.0) * 100.0

		row["order_quot"] = flt(row["order_count"]) / flt(row["quot_count"] or 1.0) * 100.0

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
		where quotation_to = 'Lead' and party_name in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0] #nosec

def get_lead_opp_count(leads):
	return frappe.db.sql("""select count(name) from `tabOpportunity`
	where opportunity_from = 'Lead' and party_name in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]

def get_quotation_ordered_count(leads):
	return frappe.db.sql("""select count(name)
		from `tabQuotation` where status = 'Ordered' and quotation_to = 'Lead'
		and party_name in (%s)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]

def get_order_amount(leads):
	return frappe.db.sql("""select sum(base_net_amount)
		from `tabSales Order Item`
		where prevdoc_docname in (
			select name from `tabQuotation` where status = 'Ordered'
			and quotation_to = 'Lead' and party_name in (%s)
		)""" % ', '.join(["%s"]*len(leads)), tuple(leads))[0][0]