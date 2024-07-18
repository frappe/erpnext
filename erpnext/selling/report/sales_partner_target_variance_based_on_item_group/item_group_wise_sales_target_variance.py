# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _

from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import (
	get_periodwise_distribution_data,
)
from erpnext.accounts.report.financial_statements import get_period_list
from erpnext.accounts.utils import get_fiscal_year


def get_data_column(filters, partner_doctype):
	data = []
	period_list = get_period_list(
		filters.fiscal_year,
		filters.fiscal_year,
		"",
		"",
		"Fiscal Year",
		filters.period,
		company=filters.company,
	)

	rows = get_data(filters, period_list, partner_doctype)
	columns = get_columns(filters, period_list, partner_doctype)

	if not rows:
		return columns, data

	for key, value in rows.items():
		value.update({frappe.scrub(partner_doctype): key[0], "item_group": key[1]})

		data.append(value)

	return columns, data


def get_data(filters, period_list, partner_doctype):
	sales_field = frappe.scrub(partner_doctype)
	sales_users_data = get_parents_data(filters, partner_doctype)

	if not sales_users_data:
		return
	sales_users = []
	sales_user_wise_item_groups = {}

	for d in sales_users_data:
		if d.parent not in sales_users:
			sales_users.append(d.parent)

		sales_user_wise_item_groups.setdefault(d.parent, [])
		if d.item_group:
			sales_user_wise_item_groups[d.parent].append(d.item_group)

	date_field = "transaction_date" if filters.get("doctype") == "Sales Order" else "posting_date"

	actual_data = get_actual_data(filters, sales_users, date_field, sales_field)

	return prepare_data(
		filters,
		sales_users_data,
		sales_user_wise_item_groups,
		actual_data,
		date_field,
		period_list,
		sales_field,
	)


def get_columns(filters, period_list, partner_doctype):
	fieldtype, options = "Currency", "currency"

	if filters.get("target_on") == "Quantity":
		fieldtype, options = "Float", ""

	columns = [
		{
			"fieldname": frappe.scrub(partner_doctype),
			"label": _(partner_doctype),
			"fieldtype": "Link",
			"options": partner_doctype,
			"width": 150,
		},
		{
			"fieldname": "item_group",
			"label": _("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 150,
		},
	]

	for period in period_list:
		target_key = f"target_{period.key}"
		variance_key = f"variance_{period.key}"

		columns.extend(
			[
				{
					"fieldname": target_key,
					"label": _("Target ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
				{
					"fieldname": period.key,
					"label": _("Achieved ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
				{
					"fieldname": variance_key,
					"label": _("Variance ({})").format(period.label),
					"fieldtype": fieldtype,
					"options": options,
					"width": 150,
				},
			]
		)

	columns.extend(
		[
			{
				"fieldname": "total_target",
				"label": _("Total Target"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
			{
				"fieldname": "total_achieved",
				"label": _("Total Achieved"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
			{
				"fieldname": "total_variance",
				"label": _("Total Variance"),
				"fieldtype": fieldtype,
				"options": options,
				"width": 150,
			},
		]
	)

	return columns


def prepare_data(
	filters,
	sales_users_data,
	sales_user_wise_item_groups,
	actual_data,
	date_field,
	period_list,
	sales_field,
):
	rows = {}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"
	qty_or_amount_field = "stock_qty" if filters.get("target_on") == "Quantity" else "base_net_amount"

	item_group_parent_child_map = get_item_group_parent_child_map()

	for d in sales_users_data:
		key = (d.parent, d.item_group)
		dist_data = get_periodwise_distribution_data(d.distribution_id, period_list, filters.get("period"))

		if key not in rows:
			rows.setdefault(key, {"total_target": 0, "total_achieved": 0, "total_variance": 0})

		details = rows[key]
		for period in period_list:
			p_key = period.key
			if p_key not in details:
				details[p_key] = 0

			target_key = f"target_{p_key}"
			variance_key = f"variance_{p_key}"
			details[target_key] = (d.get(target_qty_amt_field) * dist_data.get(p_key)) / 100
			details[variance_key] = 0
			details["total_target"] += details[target_key]

			for r in actual_data:
				if (
					r.get(sales_field) == d.parent
					and period.from_date <= r.get(date_field)
					and r.get(date_field) <= period.to_date
					and (
						not sales_user_wise_item_groups.get(d.parent)
						or r.item_group == d.item_group
						or r.item_group in item_group_parent_child_map.get(d.item_group, [])
					)
				):
					details[p_key] += r.get(qty_or_amount_field, 0)
					details[variance_key] = details.get(p_key) - details.get(target_key)
				else:
					details[variance_key] = details.get(p_key) - details.get(target_key)

			details["total_achieved"] += details.get(p_key)
			details["total_variance"] = details.get("total_achieved") - details.get("total_target")

	return rows


def get_item_group_parent_child_map():
	"""
	Returns a dict of all item group parents and leaf children associated with them.
	"""

	item_groups = frappe.get_all(
		"Item Group", fields=["name", "parent_item_group"], order_by="lft desc, rgt desc"
	)
	item_group_parent_child_map = {}

	for item_group in item_groups:
		children = item_group_parent_child_map.get(item_group.name, [])
		if not children:
			children = [item_group.name]
		item_group_parent_child_map.setdefault(item_group.parent_item_group, []).extend(children)

	return item_group_parent_child_map


def get_actual_data(filters, sales_users_or_territory_data, date_field, sales_field):
	fiscal_year = get_fiscal_year(fiscal_year=filters.get("fiscal_year"), as_dict=1)

	parent_doc = frappe.qb.DocType(filters.get("doctype"))
	child_doc = frappe.qb.DocType(filters.get("doctype") + " Item")

	query = frappe.qb.from_(parent_doc).inner_join(child_doc).on(child_doc.parent == parent_doc.name)

	if sales_field == "sales_person":
		sales_team = frappe.qb.DocType("Sales Team")
		stock_qty = child_doc.stock_qty * sales_team.allocated_percentage / 100
		net_amount = child_doc.base_net_amount * sales_team.allocated_percentage / 100
		sales_field_col = sales_team[sales_field]

		query = query.inner_join(sales_team).on(sales_team.parent == parent_doc.name)
	else:
		stock_qty = child_doc.stock_qty
		net_amount = child_doc.base_net_amount
		sales_field_col = parent_doc[sales_field]

	query = query.select(
		child_doc.item_group,
		parent_doc[date_field],
		(stock_qty).as_("stock_qty"),
		(net_amount).as_("base_net_amount"),
		sales_field_col,
	).where(
		(parent_doc.docstatus == 1)
		& (parent_doc[date_field].between(fiscal_year.year_start_date, fiscal_year.year_end_date))
		& (sales_field_col.isin(sales_users_or_territory_data))
	)

	return query.run(as_dict=True)


def get_parents_data(filters, partner_doctype):
	filters_dict = {"parenttype": partner_doctype}

	target_qty_amt_field = "target_qty" if filters.get("target_on") == "Quantity" else "target_amount"

	if filters.get("fiscal_year"):
		filters_dict["fiscal_year"] = filters.get("fiscal_year")

	return frappe.get_all(
		"Target Detail",
		filters=filters_dict,
		fields=["parent", "item_group", target_qty_amt_field, "fiscal_year", "distribution_id"],
	)
