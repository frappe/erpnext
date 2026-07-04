# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt


def execute(filters=None):
	columns, data = [], []
	columns = get_columns("utm_campaign")
	data = get_lead_data(filters or {}, "utm_campaign")
	return columns, data


def get_columns(based_on):
	return [
		{"fieldname": frappe.scrub(based_on), "label": _(based_on), "fieldtype": "Data", "width": 150},
		{"fieldname": "lead_count", "label": _("Lead Count"), "fieldtype": "Int", "width": 80},
		{"fieldname": "opp_count", "label": _("Opp Count"), "fieldtype": "Int", "width": 80},
		{"fieldname": "quot_count", "label": _("Quot Count"), "fieldtype": "Int", "width": 80},
		{"fieldname": "order_count", "label": _("Order Count"), "fieldtype": "Int", "width": 100},
		{"fieldname": "order_value", "label": _("Order Value"), "fieldtype": "Float", "width": 100},
		{"fieldname": "opp_lead", "label": _("Opp/Lead %"), "fieldtype": "Float", "width": 100},
		{"fieldname": "quot_lead", "label": _("Quot/Lead %"), "fieldtype": "Float", "width": 100},
		{"fieldname": "order_quot", "label": _("Order/Quot %"), "fieldtype": "Float", "width": 100},
	]


def get_lead_data(filters, based_on):
	based_on_field = frappe.scrub(based_on)

	lead_filters = [[based_on_field, "is", "set"]]
	if filters.from_date:
		lead_filters.append(["creation", ">=", filters.from_date])
	if filters.to_date:
		# date(creation) <= to_date, i.e. anything created before the next day
		lead_filters.append(["creation", "<", add_days(filters.to_date, 1)])

	lead_details = frappe.get_all("Lead", filters=lead_filters, fields=[based_on_field, "name"])

	lead_map = frappe._dict()
	for d in lead_details:
		lead_map.setdefault(d.get(based_on_field), []).append(d.name)

	data = []
	for based_on_value, leads in lead_map.items():
		row = {based_on_field: based_on_value, "lead_count": len(leads)}
		row["quot_count"] = get_lead_quotation_count(leads)
		row["opp_count"] = get_lead_opp_count(leads)
		row["order_count"] = get_quotation_ordered_count(leads)
		row["order_value"] = get_order_amount(leads) or 0

		row["opp_lead"] = flt(row["opp_count"]) / flt(row["lead_count"] or 1.0) * 100.0
		row["quot_lead"] = flt(row["quot_count"]) / flt(row["lead_count"] or 1.0) * 100.0

		row["order_quot"] = flt(row["order_count"]) / flt(row["quot_count"] or 1.0) * 100.0

		data.append(row)

	return data


def get_lead_quotation_count(leads):
	return frappe.db.count("Quotation", {"quotation_to": "Lead", "party_name": ["in", leads]})


def get_lead_opp_count(leads):
	return frappe.db.count("Opportunity", {"opportunity_from": "Lead", "party_name": ["in", leads]})


def get_quotation_ordered_count(leads):
	return frappe.db.count(
		"Quotation", {"status": "Ordered", "quotation_to": "Lead", "party_name": ["in", leads]}
	)


def get_order_amount(leads):
	so_item = frappe.qb.DocType("Sales Order Item")
	quotation = frappe.qb.DocType("Quotation")
	return (
		frappe.qb.from_(so_item)
		.select(Sum(so_item.base_net_amount))
		.where(
			so_item.prevdoc_docname.isin(
				frappe.qb.from_(quotation)
				.select(quotation.name)
				.where(
					(quotation.status == "Ordered")
					& (quotation.quotation_to == "Lead")
					& quotation.party_name.isin(leads)
				)
			)
		)
		.run()
	)[0][0]
