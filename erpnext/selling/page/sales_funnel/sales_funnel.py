# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _
from erpnext.accounting.report.utils import convert
import pandas as pd

@frappe.whitelist()
def get_funnel_data(from_date, to_date, company):
	active_leads = frappe.db.sql("""select count(*) from `tabLead`
		where (date(`modified`) between %s and %s)
		and status != "Do Not Contact" and company=%s""", (from_date, to_date, company))[0][0]

	active_leads += frappe.db.sql("""select count(distinct contact.name) from `tabContact` contact
		left join `tabDynamic Link` dl on (dl.parent=contact.name) where dl.link_doctype='Customer'
		and (date(contact.modified) between %s and %s) and status != "Passive" """, (from_date, to_date))[0][0]

	opportunities = frappe.db.sql("""select count(*) from `tabOpportunity`
		where (date(`creation`) between %s and %s)
		and status != "Lost" and company=%s""", (from_date, to_date, company))[0][0]

	quotations = frappe.db.sql("""select count(*) from `tabQuotation`
		where docstatus = 1 and (date(`creation`) between %s and %s)
		and status != "Lost" and company=%s""", (from_date, to_date, company))[0][0]

	sales_orders = frappe.db.sql("""select count(*) from `tabSales Order`
		where docstatus = 1 and (date(`creation`) between %s and %s) and company=%s""", (from_date, to_date, company))[0][0]

	return [
		{ "title": _("Active Leads / Customers"), "value": active_leads, "color": "#B03B46" },
		{ "title": _("Opportunities"), "value": opportunities, "color": "#F09C00" },
		{ "title": _("Quotations"), "value": quotations, "color": "#006685" },
		{ "title": _("Sales Orders"), "value": sales_orders, "color": "#00AD65" }
	]

@frappe.whitelist()
def get_opp_by_lead_source(from_date, to_date, company):
	opportunities = frappe.get_all("Opportunity", filters=[['status', 'in', ['Open', 'Quotation', 'Replied']], ['company', '=', company], ['transaction_date', 'Between', [from_date, to_date]]], fields=['currency', 'sales_stage', 'opportunity_amount', 'probability', 'source'])

	if opportunities:
		default_currency = frappe.get_cached_value('Global Defaults', 'None',  'default_currency')

		cp_opportunities = [dict(x, **{'compound_amount': (convert(x['opportunity_amount'], x['currency'], default_currency, to_date) * x['probability']/100)}) for x in opportunities]

		df = pd.DataFrame(cp_opportunities).groupby(['source', 'sales_stage'], as_index=False).agg({'compound_amount': 'sum'})

		result = {}
		result['labels'] = list(set(df.source.values))
		result['datasets'] = []

		for s in set(df.sales_stage.values):
			result['datasets'].append({'name': s, 'values': [0]*len(result['labels']), 'chartType': 'bar'})

		for row in df.itertuples():
			source_index = result['labels'].index(row.source)

			for dataset in result['datasets']:
				if dataset['name'] == row.sales_stage:
					dataset['values'][source_index] = row.compound_amount

		return result

	else:
		return 'empty'

@frappe.whitelist()
def get_pipeline_data(from_date, to_date, company):
	opportunities = frappe.get_all("Opportunity", filters=[['status', 'in', ['Open', 'Quotation', 'Replied']], ['company', '=', company], ['transaction_date', 'Between', [from_date, to_date]]], fields=['currency', 'sales_stage', 'opportunity_amount', 'probability'])

	if opportunities:
		default_currency = frappe.get_cached_value('Global Defaults', 'None',  'default_currency')

		cp_opportunities = [dict(x, **{'compound_amount': (convert(x['opportunity_amount'], x['currency'], default_currency, to_date) * x['probability']/100)}) for x in opportunities]

		df = pd.DataFrame(cp_opportunities).groupby(['sales_stage'], as_index=True).agg({'compound_amount': 'sum'}).to_dict()

		result = {}
		result['labels'] = df['compound_amount'].keys()
		result['datasets'] = []
		result['datasets'].append({'name': _("Total Amount"), 'values': df['compound_amount'].values(), 'chartType': 'bar'})

		return result

	else:
		return 'empty'