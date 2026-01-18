# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_months, flt, formatdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.controllers.trends import get_period_date_ranges


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	if filters.get("budget_against_filter"):
		dimensions = filters.get("budget_against_filter")
	else:
		dimensions = get_budget_dimensions(filters)

	budget_records = get_budget_records(filters, dimensions)
	budget_map = build_budget_map(budget_records, filters)

	data = build_report_data(budget_map, filters)

	chart_data = build_comparison_chart_data(filters, columns, data)

	return columns, data, None, chart_data


def get_budget_records(filters, dimensions):
	budget_against_field = frappe.scrub(filters["budget_against"])

	return frappe.db.sql(
		f"""
		SELECT
			b.name,
			b.account,
			b.{budget_against_field} AS dimension,
			b.budget_amount,
			b.from_fiscal_year,
			b.to_fiscal_year,
			b.budget_start_date,
			b.budget_end_date
		FROM
			`tabBudget` b
		WHERE
			b.company = %s
			AND b.docstatus = 1
			AND b.budget_against = %s
			AND b.{budget_against_field} IN ({', '.join(['%s'] * len(dimensions))})
			AND (
				b.from_fiscal_year <= %s
				AND b.to_fiscal_year >= %s
			)
		""",
		(
			filters.company,
			filters.budget_against,
			*dimensions,
			filters.to_fiscal_year,
			filters.from_fiscal_year,
		),
		as_dict=True,
	)


def build_budget_map(budget_records, filters):
	"""
	Builds a nested dictionary structure aggregating budget and actual amounts.

	Structure: {dimension_name: {account_name: {fiscal_year: {month_name: {"budget": amount, "actual": amount}}}}}
	"""
	budget_map = {}

	for budget in budget_records:
		actual_amt = get_actual_transactions(budget.dimension, filters)
		budget_map.setdefault(budget.dimension, {})
		budget_map[budget.dimension].setdefault(budget.account, {})

		budget_distributions = get_budget_distributions(budget)

		for row in budget_distributions:
			months = get_months_in_range(row.start_date, row.end_date)
			monthly_budget = flt(row.amount) / len(months)

			for month_date in months:
				fiscal_year = get_fiscal_year(month_date)[0]
				month = month_date.strftime("%B")

				budget_map[budget.dimension][budget.account].setdefault(fiscal_year, {})
				budget_map[budget.dimension][budget.account][fiscal_year].setdefault(
					month,
					{
						"budget": 0,
						"actual": 0,
					},
				)

				budget_map[budget.dimension][budget.account][fiscal_year][month]["budget"] += monthly_budget

				for ad in actual_amt.get(budget.account, []):
					if ad.month_name == month and ad.fiscal_year == fiscal_year:
						budget_map[budget.dimension][budget.account][fiscal_year][month]["actual"] += flt(
							ad.debit
						) - flt(ad.credit)

	return budget_map


def get_actual_transactions(dimension_name, filters):
	budget_against = frappe.scrub(filters.get("budget_against"))
	cost_center_filter = ""

	if filters.get("budget_against") == "Cost Center" and dimension_name:
		cc_lft, cc_rgt = frappe.db.get_value("Cost Center", dimension_name, ["lft", "rgt"])
		cost_center_filter = f"""
			and lft >= "{cc_lft}"
			and rgt <= "{cc_rgt}"
		"""

	actual_transactions = frappe.db.sql(
		f"""
			select
				gl.account,
				gl.debit,
				gl.credit,
				gl.fiscal_year,
				MONTHNAME(gl.posting_date) as month_name,
				b.{budget_against} as budget_against
			from
				`tabGL Entry` gl,
				`tabBudget` b
			where
				b.docstatus = 1
				and b.account=gl.account
				and b.{budget_against} = gl.{budget_against}
				and gl.fiscal_year between %s and %s
				and gl.is_cancelled = 0
				and b.{budget_against} = %s
				and exists(
					select
						name
					from
						`tab{filters.budget_against}`
					where
						name = gl.{budget_against}
						{cost_center_filter}
				)
				group by
					gl.name
				order by gl.fiscal_year
		""",
		(filters.from_fiscal_year, filters.to_fiscal_year, dimension_name),
		as_dict=1,
	)

	actual_transactions_map = {}
	for transaction in actual_transactions:
		actual_transactions_map.setdefault(transaction.account, []).append(transaction)

	return actual_transactions_map


def get_budget_distributions(budget):
	return frappe.db.sql(
		"""
			SELECT start_date, end_date, amount, percent
			FROM `tabBudget Distribution`
			WHERE parent = %s
			ORDER BY start_date ASC
		  """,
		(budget.name,),
		as_dict=True,
	)


def get_months_in_range(start_date, end_date):
	months = []
	current = start_date

	while current <= end_date:
		months.append(current)
		current = add_months(current, 1)

	return months


def build_report_data(budget_map, filters):
	data = []

	show_cumulative = filters.get("show_cumulative") and filters.get("period") != "Yearly"
	periods = get_periods(filters)

	for dimension, accounts in budget_map.items():
		for account, fiscal_year_map in accounts.items():
			row = {
				"budget_against": dimension,
				"account": account,
			}

			running_budget = 0
			running_actual = 0
			total_budget = 0
			total_actual = 0

			for period in periods:
				fiscal_year = period["fiscal_year"]
				months = get_months_between(period["from_date"], period["to_date"])

				period_budget = 0
				period_actual = 0

				month_map = fiscal_year_map.get(fiscal_year, {})

				for month in months:
					values = month_map.get(month)
					if values:
						period_budget += values.get("budget", 0)
						period_actual += values.get("actual", 0)

				if show_cumulative:
					running_budget += period_budget
					running_actual += period_actual
					display_budget = running_budget
					display_actual = running_actual
				else:
					display_budget = period_budget
					display_actual = period_actual

				total_budget += period_budget
				total_actual += period_actual

				if filters["period"] == "Yearly":
					budget_label = _("Budget") + " " + fiscal_year
					actual_label = _("Actual") + " " + fiscal_year
					variance_label = _("Variance") + " " + fiscal_year
				else:
					budget_label = _("Budget") + f" ({period['label_suffix']}) {fiscal_year}"
					actual_label = _("Actual") + f" ({period['label_suffix']}) {fiscal_year}"
					variance_label = _("Variance") + f" ({period['label_suffix']}) {fiscal_year}"

				row[frappe.scrub(budget_label)] = display_budget
				row[frappe.scrub(actual_label)] = display_actual
				row[frappe.scrub(variance_label)] = display_budget - display_actual

			if filters["period"] != "Yearly":
				row["total_budget"] = total_budget
				row["total_actual"] = total_actual
				row["total_variance"] = total_budget - total_actual

			data.append(row)

	return data


def get_periods(filters):
	periods = []

	group_months = filters["period"] != "Monthly"

	for (fiscal_year,) in get_fiscal_years(filters):
		for from_date, to_date in get_period_date_ranges(filters["period"], fiscal_year):
			if filters["period"] == "Yearly":
				label_suffix = fiscal_year
			else:
				if group_months:
					label_suffix = formatdate(from_date, "MMM") + "-" + formatdate(to_date, "MMM")
				else:
					label_suffix = formatdate(from_date, "MMM")

			periods.append(
				{
					"fiscal_year": fiscal_year,
					"from_date": from_date,
					"to_date": to_date,
					"label_suffix": label_suffix,
				}
			)

	return periods


def get_months_between(from_date, to_date):
	months = []
	current = from_date

	while current <= to_date:
		months.append(formatdate(current, "MMMM"))
		current = add_months(current, 1)

	return months


def get_columns(filters):
	columns = [
		{
			"label": _(filters.get("budget_against")),
			"fieldtype": "Link",
			"fieldname": "budget_against",
			"options": filters.get("budget_against"),
			"width": 150,
		},
		{
			"label": _("Account"),
			"fieldname": "account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 150,
		},
	]

	group_months = False if filters["period"] == "Monthly" else True

	fiscal_year = get_fiscal_years(filters)

	for year in fiscal_year:
		for from_date, to_date in get_period_date_ranges(filters["period"], year[0]):
			if filters["period"] == "Yearly":
				labels = [
					_("Budget") + " " + str(year[0]),
					_("Actual") + " " + str(year[0]),
					_("Variance") + " " + str(year[0]),
				]
				for label in labels:
					columns.append(
						{"label": label, "fieldtype": "Float", "fieldname": frappe.scrub(label), "width": 150}
					)
			else:
				for label in [
					_("Budget") + " (%s)" + " " + str(year[0]),
					_("Actual") + " (%s)" + " " + str(year[0]),
					_("Variance") + " (%s)" + " " + str(year[0]),
				]:
					if group_months:
						label = label % (
							formatdate(from_date, format_string="MMM")
							+ "-"
							+ formatdate(to_date, format_string="MMM")
						)
					else:
						label = label % formatdate(from_date, format_string="MMM")

					columns.append(
						{"label": label, "fieldtype": "Float", "fieldname": frappe.scrub(label), "width": 150}
					)

	if filters["period"] != "Yearly":
		for label in [_("Total Budget"), _("Total Actual"), _("Total Variance")]:
			columns.append(
				{"label": label, "fieldtype": "Float", "fieldname": frappe.scrub(label), "width": 150}
			)

		return columns
	else:
		return columns


def get_fiscal_years(filters):
	fiscal_year = frappe.db.sql(
		"""
			select
				name
			from
				`tabFiscal Year`
			where
				name between %(from_fiscal_year)s and %(to_fiscal_year)s
		""",
		{"from_fiscal_year": filters["from_fiscal_year"], "to_fiscal_year": filters["to_fiscal_year"]},
	)

	return fiscal_year


def get_budget_dimensions(filters):
	order_by = ""
	if filters.get("budget_against") == "Cost Center":
		order_by = "order by lft"

	if filters.get("budget_against") in ["Cost Center", "Project"]:
		return frappe.db.sql_list(
			"""
				select
					name
				from
					`tab{tab}`
				where
					company = %s
				{order_by}
			""".format(tab=filters.get("budget_against"), order_by=order_by),
			filters.get("company"),
		)
	else:
		return frappe.db.sql_list(
			"""
				select
					name
				from
					`tab{tab}`
			""".format(tab=filters.get("budget_against"))
		)  # nosec


def build_comparison_chart_data(filters, columns, data):
	if not data:
		return None

	budget_fields = []
	actual_fields = []

	for col in columns:
		fieldname = col.get("fieldname")
		if not fieldname:
			continue

		if fieldname.startswith("budget_"):
			budget_fields.append(fieldname)
		elif fieldname.startswith("actual_"):
			actual_fields.append(fieldname)

	if not budget_fields or not actual_fields:
		return None

	labels = [
		col["label"].replace("Budget", "").strip()
		for col in columns
		if col.get("fieldname", "").startswith("budget_")
	]

	budget_values = [0] * len(budget_fields)
	actual_values = [0] * len(actual_fields)

	for row in data:
		for i, field in enumerate(budget_fields):
			budget_values[i] += flt(row.get(field))

		for i, field in enumerate(actual_fields):
			actual_values[i] += flt(row.get(field))

	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Budget"),
					"chartType": "bar",
					"values": budget_values,
				},
				{
					"name": _("Actual Expense"),
					"chartType": "bar",
					"values": actual_values,
				},
			],
		},
		"type": "bar",
	}
