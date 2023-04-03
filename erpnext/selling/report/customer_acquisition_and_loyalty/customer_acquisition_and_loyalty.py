# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import calendar

import frappe
from frappe import _
from frappe.utils import cint, cstr, getdate


def execute(filters=None):
	common_columns = [
		{
			"label": _("New Customers"),
			"fieldname": "new_customers",
			"fieldtype": "Int",
			"default": 0,
			"width": 125,
		},
		{
			"label": _("Repeat Customers"),
			"fieldname": "repeat_customers",
			"fieldtype": "Int",
			"default": 0,
			"width": 125,
		},
		{"label": _("Total"), "fieldname": "total", "fieldtype": "Int", "default": 0, "width": 100},
		{
			"label": _("New Customer Revenue"),
			"fieldname": "new_customer_revenue",
			"fieldtype": "Currency",
			"default": 0.0,
			"width": 175,
		},
		{
			"label": _("Repeat Customer Revenue"),
			"fieldname": "repeat_customer_revenue",
			"fieldtype": "Currency",
			"default": 0.0,
			"width": 175,
		},
		{
			"label": _("Total Revenue"),
			"fieldname": "total_revenue",
			"fieldtype": "Currency",
			"default": 0.0,
			"width": 175,
		},
	]
	if filters.get("view_type") == "Monthly":
		return get_data_by_time(filters, common_columns)
	else:
		return get_data_by_territory(filters, common_columns)


def get_data_by_time(filters, common_columns):
	# key yyyy-mm
	columns = [
		{"label": _("Year"), "fieldname": "year", "fieldtype": "Data", "width": 100},
		{"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 100},
	]
	columns += common_columns

	customers_in = get_customer_stats(filters)

	# time series
	from_year, from_month, temp = filters.get("from_date").split("-")
	to_year, to_month, temp = filters.get("to_date").split("-")

	from_year, from_month, to_year, to_month = (
		cint(from_year),
		cint(from_month),
		cint(to_year),
		cint(to_month),
	)

	out = []
	for year in range(from_year, to_year + 1):
		for month in range(
			from_month if year == from_year else 1, (to_month + 1) if year == to_year else 13
		):
			key = "{year}-{month:02d}".format(year=year, month=month)
			data = customers_in.get(key)
			new = data["new"] if data else [0, 0.0]
			repeat = data["repeat"] if data else [0, 0.0]
			out.append(
				{
					"year": cstr(year),
					"month": calendar.month_name[month],
					"new_customers": new[0],
					"repeat_customers": repeat[0],
					"total": new[0] + repeat[0],
					"new_customer_revenue": new[1],
					"repeat_customer_revenue": repeat[1],
					"total_revenue": new[1] + repeat[1],
				}
			)
	return columns, out


def get_data_by_territory(filters, common_columns):
	columns = [
		{
			"label": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		}
	]
	columns += common_columns

	customers_in = get_customer_stats(filters, tree_view=True)

	territory_dict = {}
	for t in frappe.db.sql(
		"""SELECT name, lft, parent_territory, is_group FROM `tabTerritory` ORDER BY lft""", as_dict=1
	):
		territory_dict.update({t.name: {"parent": t.parent_territory, "is_group": t.is_group}})

	depth_map = frappe._dict()
	for name, info in territory_dict.items():
		default = depth_map.get(info["parent"]) + 1 if info["parent"] else 0
		depth_map.setdefault(name, default)

	data = []
	for name, indent in depth_map.items():
		condition = customers_in.get(name)
		new = customers_in[name]["new"] if condition else [0, 0.0]
		repeat = customers_in[name]["repeat"] if condition else [0, 0.0]
		temp = {
			"territory": name,
			"parent_territory": territory_dict[name]["parent"],
			"indent": indent,
			"new_customers": new[0],
			"repeat_customers": repeat[0],
			"total": new[0] + repeat[0],
			"new_customer_revenue": new[1],
			"repeat_customer_revenue": repeat[1],
			"total_revenue": new[1] + repeat[1],
			"bold": 0 if indent else 1,
		}
		data.append(temp)

	loop_data = sorted(data, key=lambda k: k["indent"], reverse=True)

	for ld in loop_data:
		if ld["parent_territory"]:
			parent_data = [x for x in data if x["territory"] == ld["parent_territory"]][0]
			for key in parent_data.keys():
				if key not in ["indent", "territory", "parent_territory", "bold"]:
					parent_data[key] += ld[key]

	return columns, data, None, None, None, 1


def get_customer_stats(filters, tree_view=False):
	"""Calculates number of new and repeated customers and revenue."""
	company_condition = ""
	if filters.get("company"):
		company_condition = " and company=%(company)s"

	customers = []
	customers_in = {}

	for si in frappe.db.sql(
		"""select territory, posting_date, customer, base_grand_total from `tabSales Invoice`
		where docstatus=1 and posting_date <= %(to_date)s
		{company_condition} order by posting_date""".format(
			company_condition=company_condition
		),
		filters,
		as_dict=1,
	):

		key = si.territory if tree_view else si.posting_date.strftime("%Y-%m")
		new_or_repeat = "new" if si.customer not in customers else "repeat"
		customers_in.setdefault(key, {"new": [0, 0.0], "repeat": [0, 0.0]})

		# if filters.from_date <= si.posting_date.strftime('%Y-%m-%d'):
		if getdate(filters.from_date) <= getdate(si.posting_date):
			customers_in[key][new_or_repeat][0] += 1
			customers_in[key][new_or_repeat][1] += si.base_grand_total
		if new_or_repeat == "new":
			customers.append(si.customer)

	return customers_in
