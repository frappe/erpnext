# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _

from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
	get_periodwise_distribution_data,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.utils import get_fiscal_year


def get_data_column(filters, partner_doctype):
	data = []
	period_list = get_period_list(filters.fiscal_year, filters.fiscal_year, '', '',
		'Fiscal Year', filters.period, company=filters.company)

	rows = get_data(filters, period_list, partner_doctype)
	columns = get_columns(filters, period_list, partner_doctype)

	if not rows:
		return columns, data

	for key, value in rows.items():
		value.update({
			frappe.scrub(partner_doctype): key[0],
			'item_group': key[1]
		})

		data.append(value)

	return columns, data

def get_data(filters, period_list, partner_doctype):
	sales_field = frappe.scrub(partner_doctype)
	sales_users_data = get_parents_data(filters, partner_doctype)

	if not sales_users_data: return
	sales_users, item_groups = [], []

	for d in sales_users_data:
		if d.parent not in sales_users:
			sales_users.append(d.parent)

		if d.item_group not in item_groups:
			item_groups.append(d.item_group)

	date_field = ("transaction_date"
		if filters.get('doctype') == "Sales Order" else "posting_date")

	actual_data = get_actual_data(filters, item_groups, sales_users, date_field, sales_field)

	return prepare_data(filters, sales_users_data,
		actual_data, date_field, period_list, sales_field)

def get_columns(filters, period_list, partner_doctype):
	fieldtype, options = "Currency", "currency"

	if filters.get("target_on") == 'Quantity':
		fieldtype, options = "Float", ""

	columns = [{
		"fieldname": frappe.scrub(partner_doctype),
		"label": _(partner_doctype),
		"fieldtype": "Link",
		"options": partner_doctype,
		"width": 150
	}, {
		"fieldname": "item_group",
		"label": _("Item Group"),
		"fieldtype": "Link",
		"options": "Item Group",
		"width": 150
	}]

	for period in period_list:
		target_key = 'target_{}'.format(period.key)
		variance_key = 'variance_{}'.format(period.key)

		columns.extend([{
			"fieldname": target_key,
			"label": _("Target ({})").format(period.label),
			"fieldtype": fieldtype,
			"options": options,
			"width": 150
		}, {
			"fieldname": period.key,
			"label": _("Achieved ({})").format(period.label),
			"fieldtype": fieldtype,
			"options": options,
			"width": 150
		}, {
			"fieldname": variance_key,
			"label": _("Variance ({})").format(period.label),
			"fieldtype": fieldtype,
			"options": options,
			"width": 150
		}])

	columns.extend([{
		"fieldname": "total_target",
		"label": _("Total Target"),
		"fieldtype": fieldtype,
		"options": options,
		"width": 150
	}, {
		"fieldname": "total_achieved",
		"label": _("Total Achieved"),
		"fieldtype": fieldtype,
		"options": options,
		"width": 150
	}, {
		"fieldname": "total_variance",
		"label": _("Total Variance"),
		"fieldtype": fieldtype,
		"options": options,
		"width": 150
	}])

	return columns

def prepare_data(filters, sales_users_data, actual_data, date_field, period_list, sales_field):
	rows = {}

	target_qty_amt_field = ("target_qty"
		if filters.get("target_on") == 'Quantity' else "target_amount")

	qty_or_amount_field = ("stock_qty"
		if filters.get("target_on") == 'Quantity' else "base_net_amount")

	for d in sales_users_data:
		key = (d.parent, d.item_group)
		dist_data = get_periodwise_distribution_data(d.distribution_id, period_list, filters.get("period"))

		if key not in rows:
			rows.setdefault(key,{
				'total_target': 0,
				'total_achieved': 0,
				'total_variance': 0
			})

		details = rows[key]
		for period in period_list:
			p_key = period.key
			if p_key not in details:
				details[p_key] = 0

			target_key = 'target_{}'.format(p_key)
			variance_key = 'variance_{}'.format(p_key)
			details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
			details[variance_key] = 0
			details["total_target"] += details[target_key]

			for r in actual_data:
				if (r.get(sales_field) == d.parent and r.item_group == d.item_group and
					period.from_date <= r.get(date_field) and r.get(date_field) <= period.to_date):
					details[p_key] += r.get(qty_or_amount_field, 0)
					details[variance_key] = details.get(p_key) - details.get(target_key)

			details["total_achieved"] += details.get(p_key)
			details["total_variance"] = details.get("total_achieved") - details.get("total_target")

	return rows

def get_actual_data(filters, item_groups, sales_users_or_territory_data, date_field, sales_field):
	fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)
	dates = [fiscal_year.year_start_date, fiscal_year.year_end_date]

	select_field = "`tab{0}`.{1}".format(filters.get("doctype"), sales_field)
	child_table = "`tab{0}`".format(filters.get("doctype") + ' Item')

	if sales_field == 'sales_person':
		select_field = "`tabSales Team`.sales_person"
		child_table = "`tab{0}`, `tabSales Team`".format(filters.get("doctype") + ' Item')
		cond = """`tabSales Team`.parent = `tab{0}`.name and
			`tabSales Team`.sales_person in ({1}) """.format(filters.get("doctype"),
			','.join(['%s'] * len(sales_users_or_territory_data)))
	else:
		cond = "`tab{0}`.{1} in ({2})".format(filters.get("doctype"), sales_field,
			','.join(['%s'] * len(sales_users_or_territory_data)))

	return frappe.db.sql(""" SELECT `tab{child_doc}`.item_group,
			`tab{child_doc}`.stock_qty, `tab{child_doc}`.base_net_amount,
			{select_field}, `tab{parent_doc}`.{date_field}
		FROM `tab{parent_doc}`, {child_table}
		WHERE
			`tab{child_doc}`.parent = `tab{parent_doc}`.name
			and `tab{parent_doc}`.docstatus = 1 and {cond}
			and `tab{child_doc}`.item_group in ({item_groups})
			and `tab{parent_doc}`.{date_field} between %s and %s"""
			.format(
				cond = cond,
				date_field = date_field,
				select_field = select_field,
				child_table = child_table,
				parent_doc = filters.get("doctype"),
				child_doc = filters.get("doctype") + ' Item',
				item_groups = ','.join(['%s'] * len(item_groups))
			), tuple(sales_users_or_territory_data + item_groups + dates), as_dict=1)

def get_parents_data(filters, partner_doctype):
	filters_dict = {'parenttype': partner_doctype}

	target_qty_amt_field = ("target_qty"
		if filters.get("target_on") == 'Quantity' else "target_amount")

	if filters.get("fiscal_year"):
		filters_dict["fiscal_year"] = filters.get("fiscal_year")

	return frappe.get_all('Target Detail',
		filters = filters_dict,
		fields = ["parent", "item_group", target_qty_amt_field, "fiscal_year", "distribution_id"])
