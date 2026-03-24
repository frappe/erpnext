# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from itertools import groupby

import frappe
from frappe import _
from frappe.query_builder.functions import Count
from frappe.utils import flt

from erpnext.accounts.report.utils import convert


def validate_filters(from_date, to_date, company):
	if from_date and to_date and (from_date >= to_date):
		frappe.throw(_("To Date must be greater than From Date"))

	if not company:
		frappe.throw(_("Please Select a Company"))


@frappe.whitelist()
def get_funnel_data(from_date: str, to_date: str, company: str):
	validate_filters(from_date, to_date, company)

	lead = frappe.qb.DocType("Lead")
	quotation = frappe.qb.DocType("Quotation")
	customer = frappe.qb.DocType("Customer")
	from_datetime = f"{from_date} 00:00:00"
	to_datetime = f"{to_date} 23:59:59.999999"

	active_leads = (
		frappe.get_all(
			"Lead",
			filters={
				"creation": ["between", [from_datetime, to_datetime]],
				"company": company,
			},
			fields=[{"COUNT": "*", "as": "count"}],
		)[0].count
		or 0
	)

	opportunities = (
		frappe.get_all(
			"Opportunity",
			filters={
				"creation": ["between", [from_datetime, to_datetime]],
				"opportunity_from": "Lead",
				"company": company,
			},
			fields=[{"COUNT": "*", "as": "count"}],
		)[0].count
		or 0
	)

	quotations = (
		frappe.qb.from_(quotation)
		.select(Count("*").as_("count"))
		.where(
			(quotation.docstatus == 1)
			& quotation.creation.between(from_datetime, to_datetime)
			& ((quotation.opportunity != "") | (quotation.quotation_to == "Lead"))
			& (quotation.company == company)
		)
	).run()[0][0] or 0

	converted = (
		frappe.qb.from_(customer)
		.join(lead)
		.on(lead.name == customer.lead_name)
		.select(Count("*").as_("count"))
		.where(customer.creation.between(from_datetime, to_datetime) & (lead.company == company))
	).run()[0][0] or 0

	return [
		{"title": _("Active Leads"), "value": active_leads, "color": "#B03B46"},
		{"title": _("Opportunities"), "value": opportunities, "color": "#F09C00"},
		{"title": _("Quotations"), "value": quotations, "color": "#006685"},
		{"title": _("Converted"), "value": converted, "color": "#00AD65"},
	]


@frappe.whitelist()
def get_opp_by_utm_source(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_source", from_date, to_date, company)


@frappe.whitelist()
def get_opp_by_utm_campaign(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_campaign", from_date, to_date, company)


@frappe.whitelist()
def get_opp_by_utm_medium(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_medium", from_date, to_date, company)


def get_opp_by(by_field, from_date, to_date, company):
	validate_filters(from_date, to_date, company)

	opportunities = frappe.get_all(
		"Opportunity",
		filters=[
			["status", "in", ["Open", "Quotation", "Replied"]],
			["company", "=", company],
			["transaction_date", "Between", [from_date, to_date]],
		],
		fields=["currency", "sales_stage", "opportunity_amount", "probability", by_field],
	)

	if opportunities:
		default_currency = frappe.get_cached_value("Global Defaults", "None", "default_currency")

		cp_opportunities = [
			dict(
				x,
				**{
					"compound_amount": (
						convert(x["opportunity_amount"], x["currency"], default_currency, to_date)
						* x["probability"]
						/ 100
					)
				},
			)
			for x in opportunities
		]

		summary = {}
		sales_stages = set()
		group_key = lambda o: (o[by_field], o["sales_stage"])  # noqa
		for (by_field_group, sales_stage), rows in groupby(
			sorted(cp_opportunities, key=group_key), group_key
		):
			summary.setdefault(by_field_group, {})[sales_stage] = sum(r["compound_amount"] for r in rows)
			sales_stages.add(sales_stage)

		pivot_table = []
		for sales_stage in sales_stages:
			row = []
			for sales_stage_values in summary.values():
				row.append(flt(sales_stage_values.get(sales_stage)))
			pivot_table.append({"chartType": "bar", "name": sales_stage, "values": row})

		result = {"datasets": pivot_table, "labels": list(summary.keys())}
		return result

	else:
		return "empty"


@frappe.whitelist()
def get_pipeline_data(from_date: str, to_date: str, company: str):
	validate_filters(from_date, to_date, company)

	opportunities = frappe.get_all(
		"Opportunity",
		filters=[
			["status", "in", ["Open", "Quotation", "Replied"]],
			["company", "=", company],
			["transaction_date", "Between", [from_date, to_date]],
		],
		fields=["currency", "sales_stage", "opportunity_amount", "probability"],
	)

	if opportunities:
		default_currency = frappe.get_cached_value("Global Defaults", "None", "default_currency")

		cp_opportunities = [
			dict(
				x,
				**{
					"compound_amount": (
						convert(x["opportunity_amount"], x["currency"], default_currency, to_date)
						* x["probability"]
						/ 100
					)
				},
			)
			for x in opportunities
		]

		summary = {}
		for sales_stage, rows in groupby(cp_opportunities, lambda o: o["sales_stage"]):
			summary[sales_stage] = sum(flt(r["compound_amount"]) for r in rows)

		result = {
			"labels": list(summary.keys()),
			"datasets": [{"name": _("Total Amount"), "values": list(summary.values()), "chartType": "bar"}],
		}
		return result

	else:
		return "empty"
