# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.permissions import get_user_permissions
from frappe.utils import cint, cstr, formatdate, getdate


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
		for month in range(from_month if year == from_year else 1, (to_month + 1) if year == to_year else 13):
			key = f"{year}-{month:02d}"
			data = customers_in.get(key)
			new = data["new"] if data else [0, 0.0]
			repeat = data["repeat"] if data else [0, 0.0]
			out.append(
				{
					"year": cstr(year),
					"month": formatdate(f"{key}-01", "MMMM"),
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
			"label": _("Territory"),
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
			parent_data = next(x for x in data if x["territory"] == ld["parent_territory"])
			for key in parent_data.keys():
				if key not in ["indent", "territory", "parent_territory", "bold"]:
					parent_data[key] += ld[key]

	return columns, data, None, None, None, 1


def get_customer_stats(filters, tree_view=False):
	"""Count distinct new and repeat customers and their revenue per period."""
	si = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(si)
		.select(si.territory, si.posting_date, si.customer, si.base_grand_total, si.is_return)
		.where((si.docstatus == 1) & (si.posting_date <= filters.get("to_date")))
		# name tie-break makes the first-seen-per-customer classification deterministic across engines
		.orderby(si.posting_date)
		.orderby(si.name)
	)
	if filters.get("company"):
		query = query.where(si.company == filters.get("company"))

	# scope to the user's permitted customers; the report serves roles without Sales
	# Invoice read, so apply the Customer restriction directly instead of via get_list
	permitted_customers = get_permitted_customers()
	if permitted_customers is not None:
		query = query.where(si.customer.isin(permitted_customers))

	from_date = getdate(filters.get("from_date"))
	acquisition = {}  # customer -> (key, date) of their first invoice
	counted = {}  # key -> {"new": set of customers, "repeat": set of customers}
	customers_in = {}

	for row in query.run(as_dict=True):
		posting_date = getdate(row.posting_date)
		key = row.territory if tree_view else posting_date.strftime("%Y-%m")

		# a return never acquires a customer; it only nets revenue
		if not row.is_return and row.customer not in acquisition:
			acquisition[row.customer] = (key, posting_date)

		if posting_date < from_date:
			continue

		acq = acquisition.get(row.customer)
		# without an acquiring sale (e.g. a standalone credit note) the customer is never "new"
		new_or_repeat = "new" if acq and key == acq[0] and acq[1] >= from_date else "repeat"

		customers_in.setdefault(key, {"new": [0, 0.0], "repeat": [0, 0.0]})
		counted.setdefault(key, {"new": set(), "repeat": set()})

		# count each customer once per period; returns net revenue but not the headcount
		if not row.is_return and row.customer not in counted[key][new_or_repeat]:
			counted[key][new_or_repeat].add(row.customer)
			customers_in[key][new_or_repeat][0] += 1
		customers_in[key][new_or_repeat][1] += row.base_grand_total

	return customers_in


def get_permitted_customers():
	"""Customers the current user is restricted to, or None when unrestricted."""
	customer_perms = get_user_permissions(frappe.session.user).get("Customer") or []
	allowed = [
		perm.get("doc")
		for perm in customer_perms
		if not perm.get("applicable_for") or perm.get("applicable_for") == "Sales Invoice"
	]
	return allowed or None
