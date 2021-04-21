# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import (flt, cstr)

from erpnext.accounts.report.financial_statements import filter_accounts, filter_out_zero_value_rows
from erpnext.accounts.report.trial_balance.trial_balance import validate_filters

from six import itervalues

def execute(filters=None):
	validate_filters(filters)
	dimension_items_list = get_dimension_items_list(filters.dimension, filters.company)

	if not dimension_items_list:
		return [], []

	dimension_items_list = [''.join(d) for d in dimension_items_list]
	columns = get_columns(dimension_items_list)
	data = get_data(filters, dimension_items_list)

	return columns, data

def get_data(filters, dimension_items_list):
	company_currency = erpnext.get_company_currency(filters.company)
	acc = frappe.db.sql("""
		select
			name, account_number, parent_account, lft, rgt, root_type,
			report_type, account_name, include_in_gross, account_type, is_group
		from
			`tabAccount`
		where
			company=%s
			order by lft""", (filters.company), as_dict=True)

	if not acc:
		return None

	accounts, accounts_by_name, parent_children_map = filter_accounts(acc)

	min_lft, max_rgt = frappe.db.sql("""select min(lft), max(rgt) from `tabAccount`
		where company=%s""", (filters.company))[0]

	account = frappe.db.sql_list("""select name from `tabAccount`
		where lft >= %s and rgt <= %s and company = %s""", (min_lft, max_rgt, filters.company))

	gl_entries_by_account = {}
	set_gl_entries_by_account(dimension_items_list, filters, account, gl_entries_by_account)
	format_gl_entries(gl_entries_by_account, accounts_by_name, dimension_items_list)
	accumulate_values_into_parents(accounts, accounts_by_name, dimension_items_list)
	out = prepare_data(accounts, filters, parent_children_map, company_currency, dimension_items_list)
	out = filter_out_zero_value_rows(out, parent_children_map)

	return out

def set_gl_entries_by_account(dimension_items_list, filters, account, gl_entries_by_account):
	for item in dimension_items_list:
		condition = get_condition(filters.from_date, item, filters.dimension)
		if account:
			condition += " and account in ({})"\
				.format(", ".join([frappe.db.escape(d) for d in account]))

		gl_filters = {
			"company": filters.get("company"),
			"from_date": filters.get("from_date"),
			"to_date": filters.get("to_date"),
			"finance_book": cstr(filters.get("finance_book"))
		}

		gl_filters['item'] = ''.join(item)

		if filters.get("include_default_book_entries"):
			gl_filters["company_fb"] = frappe.db.get_value("Company",
				filters.company, 'default_finance_book')

		for key, value in filters.items():
			if value:
				gl_filters.update({
					key: value
				})

		gl_entries = frappe.db.sql("""
		select
			posting_date, account, debit, credit, is_opening, fiscal_year,
			debit_in_account_currency, credit_in_account_currency, account_currency
		from
			`tabGL Entry`
		where
			company=%(company)s
		{condition}
		and posting_date <= %(to_date)s
		and is_cancelled = 0
		order by account, posting_date""".format(
			condition=condition),
			gl_filters, as_dict=True) #nosec

		for entry in gl_entries:
			entry['dimension_item'] = ''.join(item)
			gl_entries_by_account.setdefault(entry.account, []).append(entry)

def format_gl_entries(gl_entries_by_account, accounts_by_name, dimension_items_list):

	for entries in itervalues(gl_entries_by_account):
		for entry in entries:
			d = accounts_by_name.get(entry.account)
			if not d:
				frappe.msgprint(
					_("Could not retrieve information for {0}.").format(entry.account), title="Error",
					raise_exception=1
				)
			for item in dimension_items_list:
				if item == entry.dimension_item:
					d[frappe.scrub(item)] = d.get(frappe.scrub(item), 0.0) + flt(entry.debit) - flt(entry.credit)

def prepare_data(accounts, filters, parent_children_map, company_currency, dimension_items_list):
	data = []

	for d in accounts:
		has_value = False
		total = 0
		row = {
			"account": d.name,
			"parent_account": d.parent_account,
			"indent": d.indent,
			"from_date": filters.from_date,
			"to_date": filters.to_date,
			"currency": company_currency,
			"account_name": ('{} - {}'.format(d.account_number, d.account_name)
				if d.account_number else d.account_name)
		}

		for item in dimension_items_list:
			row[frappe.scrub(item)] = flt(d.get(frappe.scrub(item), 0.0), 3)

			if abs(row[frappe.scrub(item)]) >= 0.005:
				# ignore zero values
				has_value = True
				total += flt(d.get(frappe.scrub(item), 0.0), 3)

		row["has_value"] = has_value
		row["total"] = total
		data.append(row)

	return data

def accumulate_values_into_parents(accounts, accounts_by_name, dimension_items_list):
	"""accumulate children's values in parent accounts"""
	for d in reversed(accounts):
		if d.parent_account:
			for item in dimension_items_list:
				accounts_by_name[d.parent_account][frappe.scrub(item)] = \
					accounts_by_name[d.parent_account].get(frappe.scrub(item), 0.0) + d.get(frappe.scrub(item), 0.0)

def get_condition(from_date, item, dimension):
	conditions = []

	if from_date:
		conditions.append("posting_date >= %(from_date)s")
	if dimension:
		if dimension not in ['Cost Center', 'Project']:
			if dimension in ['Customer', 'Supplier']:
				dimension = 'Party'
			else:
				dimension = 'Voucher No'
		txt = "{0} = %(item)s".format(frappe.scrub(dimension))
		conditions.append(txt)

	return " and {}".format(" and ".join(conditions)) if conditions else ""

def get_dimension_items_list(dimension, company):
	meta = frappe.get_meta(dimension, cached=False)
	fieldnames = [d.fieldname for d in meta.get("fields")]
	filters = {}
	if 'company' in fieldnames:
		filters['company'] = company
	return frappe.get_all(dimension, filters, as_list=True)

def get_columns(dimension_items_list, accumulated_values=1, company=None):
	columns = [{
		"fieldname": "account",
		"label": _("Account"),
		"fieldtype": "Link",
		"options": "Account",
		"width": 300
	}]
	if company:
		columns.append({
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1
		})
	for item in dimension_items_list:
		columns.append({
			"fieldname": frappe.scrub(item),
			"label": item,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})
	columns.append({
			"fieldname": "total",
			"label": "Total",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		})

	return columns
