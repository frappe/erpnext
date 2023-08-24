# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from itertools import groupby

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.utils import convert


def validate_filters(from_date, to_date, company):
	if from_date and to_date and (from_date >= to_date):
		frappe.throw(_("To Date must be greater than From Date"))

	if not company:
		frappe.throw(_("Please Select a Company"))


@frappe.whitelist()
def get_funnel_data(from_date, to_date, company):
	validate_filters(from_date, to_date, company)

	active_leads = frappe.db.sql(
		"""select count(*) from `tabLead`
		where (date(`creation`) between %s and %s)
		and company=%s""",
		(from_date, to_date, company),
	)[0][0]

	opportunities = frappe.db.sql(
		"""select count(*) from `tabOpportunity`
		where (date(`creation`) between %s and %s)
		and opportunity_from='Lead' and company=%s""",
		(from_date, to_date, company),
	)[0][0]

	quotations = frappe.db.sql(
		"""select count(*) from `tabQuotation`
		where docstatus = 1 and (date(`creation`) between %s and %s)
		and (opportunity!="" or quotation_to="Lead") and company=%s""",
		(from_date, to_date, company),
	)[0][0]

	converted = frappe.db.sql(
		"""select count(*) from `tabCustomer`
		JOIN `tabLead` ON `tabLead`.name = `tabCustomer`.lead_name
		WHERE (date(`tabCustomer`.creation) between %s and %s)
		and `tabLead`.company=%s""",
		(from_date, to_date, company),
	)[0][0]

	return [
		{"title": _("Active Leads"), "value": active_leads, "color": "#B03B46"},
		{"title": _("Opportunities"), "value": opportunities, "color": "#F09C00"},
		{"title": _("Quotations"), "value": quotations, "color": "#006685"},
		{"title": _("Converted"), "value": converted, "color": "#00AD65"},
	]


@frappe.whitelist()
def get_opp_by_lead_source(from_date, to_date, company):
	validate_filters(from_date, to_date, company)

	opportunities = frappe.get_all(
		"Opportunity",
		filters=[
			["status", "in", ["Open", "Quotation", "Replied"]],
			["company", "=", company],
			["transaction_date", "Between", [from_date, to_date]],
		],
		fields=["currency", "sales_stage", "opportunity_amount", "probability", "source"],
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
				}
			)
			for x in opportunities
		]

		summary = {}
		sales_stages = set()
		group_key = lambda o: (o["source"], o["sales_stage"])  # noqa
		for (source, sales_stage), rows in groupby(cp_opportunities, group_key):
			summary.setdefault(source, {})[sales_stage] = sum(r["compound_amount"] for r in rows)
			sales_stages.add(sales_stage)

		pivot_table = []
		for sales_stage in sales_stages:
			row = []
			for source, sales_stage_values in summary.items():
				row.append(flt(sales_stage_values.get(sales_stage)))
			pivot_table.append({"chartType": "bar", "name": sales_stage, "values": row})

		result = {"datasets": pivot_table, "labels": list(summary.keys())}
		return result

	else:
		return "empty"


@frappe.whitelist()
def get_pipeline_data(from_date, to_date, company):
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
				}
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
