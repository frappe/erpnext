# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from itertools import groupby

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Date
from frappe.utils import flt


def validate_filters(from_date, to_date, company):
	if from_date and to_date and (from_date > to_date):
		frappe.throw(_("To Date must be greater than From Date"))

	if not company:
		frappe.throw(_("Please select a Company"))


def base_amount(opportunity):
	# company-currency value: convert via the live rate, falling back to the stored base
	return flt(opportunity["opportunity_amount"]) * flt(opportunity["conversion_rate"]) or flt(
		opportunity["base_opportunity_amount"]
	)


@frappe.whitelist()
def get_funnel_data(from_date: str, to_date: str, company: str):
	frappe.has_permission("Company", doc=company, throw=True)

	validate_filters(from_date, to_date, company)

	lead = frappe.qb.DocType("Lead")
	active_leads = (
		frappe.qb.from_(lead)
		.select(Count("*"))
		.where(Date(lead.creation).between(from_date, to_date) & (lead.company == company))
		.run()
	)[0][0]

	opportunity = frappe.qb.DocType("Opportunity")
	opportunities = (
		frappe.qb.from_(opportunity)
		.select(Count("*"))
		.where(
			Date(opportunity.creation).between(from_date, to_date)
			& (opportunity.opportunity_from == "Lead")
			& (opportunity.company == company)
		)
		.run()
	)[0][0]

	quotation = frappe.qb.DocType("Quotation")
	quotations = (
		frappe.qb.from_(quotation)
		.select(Count("*"))
		.where(
			(quotation.docstatus == 1)
			& Date(quotation.creation).between(from_date, to_date)
			& ((quotation.opportunity != "") | (quotation.quotation_to == "Lead"))
			& (quotation.company == company)
		)
		.run()
	)[0][0]

	customer = frappe.qb.DocType("Customer")
	converted = (
		frappe.qb.from_(customer)
		.inner_join(lead)
		.on(lead.name == customer.lead_name)
		.select(Count("*"))
		.where(Date(customer.creation).between(from_date, to_date) & (lead.company == company))
		.run()
	)[0][0]

	return [
		{"title": _("Active Leads"), "value": active_leads, "color": "#B03B46"},
		{"title": _("Opportunities"), "value": opportunities, "color": "#F09C00"},
		{"title": _("Quotations"), "value": quotations, "color": "#006685"},
		{"title": _("Converted"), "value": converted, "color": "#00AD65"},
	]


@frappe.whitelist()
def get_opp_by_utm_source(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_source", from_date, to_date, company, ignore_permissions=False)


@frappe.whitelist()
def get_opp_by_utm_campaign(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_campaign", from_date, to_date, company, ignore_permissions=False)


@frappe.whitelist()
def get_opp_by_utm_medium(from_date: str, to_date: str, company: str):
	return get_opp_by("utm_medium", from_date, to_date, company, ignore_permissions=False)


def get_opp_by(by_field, from_date, to_date, company, ignore_permissions=False):
	validate_filters(from_date, to_date, company)

	get_opportunities = frappe.get_all if ignore_permissions else frappe.get_list
	opportunities = get_opportunities(
		"Opportunity",
		filters=[
			["status", "in", ["Open", "Quotation", "Replied"]],
			["company", "=", company],
			["transaction_date", "Between", [from_date, to_date]],
		],
		fields=[
			"sales_stage",
			"base_opportunity_amount",
			"opportunity_amount",
			"conversion_rate",
			"probability",
			by_field,
		],
	)

	if opportunities:
		cp_opportunities = [
			dict(
				x,
				**{"compound_amount": (base_amount(x) * x["probability"] / 100)},
			)
			for x in opportunities
			if x.get(by_field)
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

	opportunities = frappe.get_list(
		"Opportunity",
		filters=[
			["status", "in", ["Open", "Quotation", "Replied"]],
			["company", "=", company],
			["transaction_date", "Between", [from_date, to_date]],
		],
		fields=[
			"sales_stage",
			"base_opportunity_amount",
			"opportunity_amount",
			"conversion_rate",
			"probability",
		],
	)

	if opportunities:
		cp_opportunities = [
			dict(
				x,
				**{"compound_amount": (base_amount(x) * x["probability"] / 100)},
			)
			for x in opportunities
		]

		summary = {}
		for opportunity in cp_opportunities:
			sales_stage = opportunity["sales_stage"]
			summary[sales_stage] = summary.get(sales_stage, 0) + flt(opportunity["compound_amount"])

		result = {
			"labels": list(summary.keys()),
			"datasets": [{"name": _("Total Amount"), "values": list(summary.values()), "chartType": "bar"}],
		}
		return result

	else:
		return "empty"
