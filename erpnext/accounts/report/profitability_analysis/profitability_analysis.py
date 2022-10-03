# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cstr, flt

from erpnext.accounts.report.financial_statements import (
	filter_accounts,
	filter_out_zero_value_rows,
)
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters

value_fields = ("income", "expense", "gross_profit_loss")


def execute(filters=None):
	if not filters.get("based_on"):
		filters["based_on"] = "Cost Center"

	based_on = filters.based_on.replace(" ", "_").lower()
	validate_filters(filters)
	accounts = get_accounts_data(based_on, filters.get("company"))
	data = get_data(accounts, filters, based_on)
	columns = get_columns(filters)
	return columns, data


def get_accounts_data(based_on, company):
	if based_on == "cost_center":
		return frappe.db.sql(
			"""select name, parent_cost_center as parent_account, cost_center_name as account_name, lft, rgt
			from `tabCost Center` where company=%s order by name""",
			company,
			as_dict=True,
		)
	elif based_on == "project":
		return frappe.get_all("Project", fields=["name"], filters={"company": company}, order_by="name")
	else:
		filters = {}
		doctype = frappe.unscrub(based_on)
		has_company = frappe.db.has_column(doctype, "company")

		if has_company:
			filters.update({"company": company})

		return frappe.get_all(doctype, fields=["name"], filters=filters, order_by="name")


def get_data(accounts, filters, based_on):
	if not accounts:
		return []

	accounts, accounts_by_name, parent_children_map = filter_accounts(accounts)

	gl_entries_by_account = {}

	set_gl_entries_by_account(
		filters.get("company"),
		filters.get("from_date"),
		filters.get("to_date"),
		based_on,
		gl_entries_by_account,
		ignore_closing_entries=not flt(filters.get("with_period_closing_entry")),
	)

	total_row = calculate_values(accounts, gl_entries_by_account, filters)
	accumulate_values_into_parents(accounts, accounts_by_name)

	data = prepare_data(accounts, filters, total_row, parent_children_map, based_on)
	data = filter_out_zero_value_rows(
		data, parent_children_map, show_zero_values=filters.get("show_zero_values")
	)

	return data


def calculate_values(accounts, gl_entries_by_account, filters):
	init = {"income": 0.0, "expense": 0.0, "gross_profit_loss": 0.0}

	total_row = {
		"cost_center": None,
		"account_name": "'" + _("Total") + "'",
		"warn_if_negative": True,
		"income": 0.0,
		"expense": 0.0,
		"gross_profit_loss": 0.0,
		"account": "'" + _("Total") + "'",
		"parent_account": None,
		"indent": 0,
		"has_value": True,
	}

	for d in accounts:
		d.update(init.copy())

		# add opening

		for entry in gl_entries_by_account.get(d.name, []):
			if cstr(entry.is_opening) != "Yes":
				if entry.type == "Income":
					d["income"] += flt(entry.credit) - flt(entry.debit)
				if entry.type == "Expense":
					d["expense"] += flt(entry.debit) - flt(entry.credit)

				d["gross_profit_loss"] = d.get("income") - d.get("expense")

		total_row["income"] += d["income"]
		total_row["expense"] += d["expense"]

	total_row["gross_profit_loss"] = total_row.get("income") - total_row.get("expense")

	return total_row


def accumulate_values_into_parents(accounts, accounts_by_name):
	for d in reversed(accounts):
		if d.parent_account:
			for key in value_fields:
				accounts_by_name[d.parent_account][key] += d[key]


def prepare_data(accounts, filters, total_row, parent_children_map, based_on):
	data = []
	company_currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")

	for d in accounts:
		has_value = False
		row = {
			"account_name": d.account_name or d.name,
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"fiscal_year": filters.get("fiscal_year"),
			"currency": company_currency,
			"based_on": based_on,
		}

		for key in value_fields:
			row[key] = flt(d.get(key, 0.0), 3)

			if abs(row[key]) >= 0.005:
				# ignore zero values
				has_value = True

		row["has_value"] = has_value
		data.append(row)

	data.extend([{}, total_row])

	return data


def get_columns(filters):
	return [
		{
			"fieldname": "account",
			"label": _(filters.get("based_on")),
			"fieldtype": "Link",
			"options": filters.get("based_on"),
			"width": 300,
		},
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{
			"fieldname": "income",
			"label": _("Income"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 305,
		},
		{
			"fieldname": "expense",
			"label": _("Expense"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 305,
		},
		{
			"fieldname": "gross_profit_loss",
			"label": _("Gross Profit / Loss"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 307,
		},
	]


def set_gl_entries_by_account(
	company, from_date, to_date, based_on, gl_entries_by_account, ignore_closing_entries=False
):
	"""Returns a dict like { "account": [gl entries], ... }"""
	additional_conditions = []

	if ignore_closing_entries:
		additional_conditions.append("and ifnull(voucher_type, '')!='Period Closing Voucher'")

	if from_date:
		additional_conditions.append("and posting_date >= %(from_date)s")

	gl_entries = frappe.db.sql(
		"""select posting_date, {based_on} as based_on, debit, credit,
		is_opening, (select root_type from `tabAccount` where name = account) as type
		from `tabGL Entry` where company=%(company)s
		{additional_conditions}
		and posting_date <= %(to_date)s
		and {based_on} is not null
		and is_cancelled = 0
		order by {based_on}, posting_date""".format(
			additional_conditions="\n".join(additional_conditions), based_on=based_on
		),
		{"company": company, "from_date": from_date, "to_date": to_date},
		as_dict=True,
	)

	for entry in gl_entries:
		gl_entries_by_account.setdefault(entry.based_on, []).append(entry)

	return gl_entries_by_account
