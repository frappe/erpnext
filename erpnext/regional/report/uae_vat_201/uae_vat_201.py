# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from erpnext import get_region


def execute(filters=None):
	validate_company_region(filters)
	columns = get_columns()
	data, emirates, amounts_by_emirate = get_data(filters)
	return columns, data


def validate_company_region(filters):
	if filters.get("company") and get_region(filters.get("company")) != "United Arab Emirates":
		frappe.throw(
			_(
				"The company {0} is not in United Arab Emirates. UAE VAT 201 report is only available for companies in United Arab Emirates."
			).format(frappe.bold(filters.get("company")))
		)


def get_columns():
	"""Creates a list of dictionaries that are used to generate column headers of the data table."""
	return [
		{"fieldname": "no", "label": _("No"), "fieldtype": "Data", "width": 50},
		{"fieldname": "legend", "label": _("Legend"), "fieldtype": "Data", "width": 300},
		{
			"fieldname": "amount",
			"label": _("Amount (AED)"),
			"fieldtype": "Currency",
			"width": 125,
		},
		{
			"fieldname": "vat_amount",
			"label": _("VAT Amount (AED)"),
			"fieldtype": "Currency",
			"width": 150,
		},
	]


def get_data(filters=None):
	"""Returns the list of dictionaries. Each dictionary is a row in the datatable and chart data."""
	data = []
	emirates, amounts_by_emirate = append_vat_on_sales(data, filters)
	append_vat_on_expenses(data, filters)
	return data, emirates, amounts_by_emirate


def append_vat_on_sales(data, filters):
	"""Appends Sales and All Other Outputs."""
	append_data(data, "", _("VAT on Sales and All Other Outputs"), "", "")

	emirates, amounts_by_emirate = standard_rated_expenses_emiratewise(data, filters)

	append_data(
		data,
		"2",
		_("Tax Refunds provided to Tourists under the Tax Refunds for Tourists Scheme"),
		frappe.format((-1) * get_tourist_tax_return_total(filters), "Currency"),
		frappe.format((-1) * get_tourist_tax_return_tax(filters), "Currency"),
	)

	append_data(
		data,
		"3",
		_("Supplies subject to the reverse charge provision"),
		frappe.format(get_reverse_charge_total(filters), "Currency"),
		frappe.format(get_reverse_charge_tax(filters), "Currency"),
	)

	append_data(data, "4", _("Zero Rated"), frappe.format(get_zero_rated_total(filters), "Currency"), "-")

	append_data(data, "5", _("Exempt Supplies"), frappe.format(get_exempt_total(filters), "Currency"), "-")

	append_data(data, "", "", "", "")

	return emirates, amounts_by_emirate


def standard_rated_expenses_emiratewise(data, filters):
	"""Append emiratewise standard rated expenses and vat."""
	total_emiratewise = get_total_emiratewise(filters)
	emirates = get_emirates()
	amounts_by_emirate = {}
	for emirate, amount, vat in total_emiratewise:
		amounts_by_emirate[emirate] = {
			"legend": emirate,
			"raw_amount": amount,
			"raw_vat_amount": vat,
			"amount": frappe.format(amount, "Currency"),
			"vat_amount": frappe.format(vat, "Currency"),
		}
	amounts_by_emirate = append_emiratewise_expenses(data, emirates, amounts_by_emirate)
	return emirates, amounts_by_emirate


def append_emiratewise_expenses(data, emirates, amounts_by_emirate):
	"""Append emiratewise standard rated expenses and vat."""
	for no, emirate in enumerate(emirates, 97):
		if emirate in amounts_by_emirate:
			amounts_by_emirate[emirate]["no"] = _("1{0}").format(chr(no))
			amounts_by_emirate[emirate]["legend"] = _("Standard rated supplies in {0}").format(emirate)
			data.append(amounts_by_emirate[emirate])
		else:
			append_data(
				data,
				_("1{0}").format(chr(no)),
				_("Standard rated supplies in {0}").format(emirate),
				frappe.format(0, "Currency"),
				frappe.format(0, "Currency"),
			)
	return amounts_by_emirate


def append_vat_on_expenses(data, filters):
	"""Appends Expenses and All Other Inputs."""
	append_data(data, "", _("VAT on Expenses and All Other Inputs"), "", "")
	append_data(
		data,
		"9",
		_("Standard Rated Expenses"),
		frappe.format(get_standard_rated_expenses_total(filters), "Currency"),
		frappe.format(get_standard_rated_expenses_tax(filters), "Currency"),
	)
	append_data(
		data,
		"10",
		_("Supplies subject to the reverse charge provision"),
		frappe.format(get_reverse_charge_recoverable_total(filters), "Currency"),
		frappe.format(get_reverse_charge_recoverable_tax(filters), "Currency"),
	)


def append_data(data, no, legend, amount, vat_amount):
	"""Returns data with appended value."""
	data.append({"no": no, "legend": legend, "amount": amount, "vat_amount": vat_amount})


def get_total_emiratewise(filters):
	"""Returns Emiratewise Amount and Taxes."""
	amounts = get_emiratewise_standard_rated_amount(filters)
	vat_amounts = get_emiratewise_vat_amount(filters)
	return [
		(emirate, amounts.get(emirate, 0), vat_amounts.get(emirate, 0))
		for emirate in dict.fromkeys([*amounts, *vat_amounts])
	]


def get_emiratewise_standard_rated_amount(filters):
	"""Returns emiratewise net amount of standard rated supplies in company currency."""
	i = frappe.qb.DocType("Sales Invoice Item")
	s = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(i)
		.inner_join(s)
		.on(i.parent == s.name)
		.select(s.vat_emirate, Sum(i.base_net_amount))
		.where((s.docstatus == 1) & (i.is_exempt != 1) & (i.is_zero_rated != 1))
		.groupby(s.vat_emirate)
	)
	for condition in get_sales_conditions(filters, s):
		query = query.where(condition)
	return dict(query.run())


def get_emiratewise_vat_amount(filters):
	"""Returns emiratewise VAT on standard rated supplies in company currency.

	Sales Taxes and Charges.item_wise_tax_detail stores each item's share of the tax
	row in company currency, so it keeps the item level exempt / zero rated split.
	"""
	i = frappe.qb.DocType("Sales Invoice Item")
	s = frappe.qb.DocType("Sales Invoice")
	t = frappe.qb.DocType("Sales Taxes and Charges")
	uae_vat = frappe.qb.DocType("UAE VAT Account")

	standard_rated_items_query = (
		frappe.qb.from_(i)
		.inner_join(s)
		.on(i.parent == s.name)
		.select(s.name, i.item_code)
		.where((s.docstatus == 1) & (i.is_exempt != 1) & (i.is_zero_rated != 1))
	)
	for condition in get_sales_conditions(filters, s):
		standard_rated_items_query = standard_rated_items_query.where(condition)

	standard_rated_items = defaultdict(set)
	for invoice, item_code in standard_rated_items_query.run():
		standard_rated_items[invoice].add(item_code)

	vat_query = (
		frappe.qb.from_(t)
		.inner_join(s)
		.on(t.parent == s.name)
		.select(s.name, s.vat_emirate, t.item_wise_tax_detail)
		.where(
			(s.docstatus == 1)
			& t.account_head.isin(
				frappe.qb.from_(uae_vat)
				.select(uae_vat.account)
				.where(uae_vat.parent == filters.get("company"))
			)
		)
	)
	for condition in get_sales_conditions(filters, s):
		vat_query = vat_query.where(condition)

	vat_amounts = defaultdict(float)
	for invoice, emirate, item_wise_tax_detail in vat_query.run():
		for item_code, tax_detail in json.loads(item_wise_tax_detail or "{}").items():
			if item_code in standard_rated_items[invoice]:
				vat_amounts[emirate] += flt(tax_detail[1])
	return vat_amounts


def get_emirates():
	"""Returns a List of emirates in the order that they are to be displayed."""
	return ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Umm Al Quwain", "Ras Al Khaimah", "Fujairah"]


def get_filters(filters):
	"""The conditions to be used to filter data to calculate the total sale."""
	query_filters = []
	if filters.get("company"):
		query_filters.append(["company", "=", filters["company"]])
	if filters.get("from_date"):
		query_filters.append(["posting_date", ">=", filters["from_date"]])
	if filters.get("from_date"):
		query_filters.append(["posting_date", "<=", filters["to_date"]])
	return query_filters


def get_reverse_charge_total(filters):
	"""Returns the sum of the total of each Purchase invoice made."""
	query_filters = get_filters(filters)
	query_filters.append(["reverse_charge", "=", "Y"])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice", filters=query_filters, fields=["sum(base_total)"], as_list=True, limit=1
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_reverse_charge_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	conditions = get_conditions_join(filters)
	return (
		frappe.db.sql(
			f"""
		select sum(debit)  from
			`tabPurchase Invoice` p inner join `tabGL Entry` gl
		on
			gl.voucher_no =  p.name
		where
			p.reverse_charge = "Y"
			and p.docstatus = 1
			and gl.docstatus = 1
			and account in (select account from `tabUAE VAT Account` where  parent=%(company)s)
			{conditions} ;
		""",
			filters,
		)[0][0]
		or 0
	)


def get_reverse_charge_recoverable_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	query_filters = get_filters(filters)
	query_filters.append(["reverse_charge", "=", "Y"])
	query_filters.append(["recoverable_reverse_charge", ">", "0"])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice", filters=query_filters, fields=["sum(base_total)"], as_list=True, limit=1
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_reverse_charge_recoverable_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	conditions = get_conditions_join(filters)
	return (
		frappe.db.sql(
			f"""
		select
			sum(debit * p.recoverable_reverse_charge / 100)
		from
			`tabPurchase Invoice` p  inner join `tabGL Entry` gl
		on
			gl.voucher_no = p.name
		where
			p.reverse_charge = "Y"
			and p.docstatus = 1
			and p.recoverable_reverse_charge > 0
			and gl.docstatus = 1
			and account in (select account from `tabUAE VAT Account` where  parent=%(company)s)
			{conditions} ;
		""",
			filters,
		)[0][0]
		or 0
	)


def get_conditions_join(filters):
	"""The conditions to be used to filter data to calculate the total vat."""
	conditions = ""
	for opts in (
		("company", " and p.company=%(company)s"),
		("from_date", " and p.posting_date>=%(from_date)s"),
		("to_date", " and p.posting_date<=%(to_date)s"),
	):
		if filters.get(opts[0]):
			conditions += opts[1]
	return conditions


def get_standard_rated_expenses_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	query_filters = get_filters(filters)
	query_filters.append(["recoverable_standard_rated_expenses", ">", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice", filters=query_filters, fields=["sum(base_total)"], as_list=True, limit=1
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_standard_rated_expenses_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	query_filters = get_filters(filters)
	query_filters.append(["recoverable_standard_rated_expenses", ">", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice",
				filters=query_filters,
				fields=["sum(recoverable_standard_rated_expenses)"],
				as_list=True,
				limit=1,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_tourist_tax_return_total(filters):
	"""Returns the sum of the total of each Sales invoice with non zero tourist_tax_return."""
	query_filters = get_filters(filters)
	query_filters.append(["tourist_tax_return", ">", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Sales Invoice", filters=query_filters, fields=["sum(base_total)"], as_list=True, limit=1
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_tourist_tax_return_tax(filters):
	"""Returns the sum of the tax of each Sales invoice with non zero tourist_tax_return."""
	query_filters = get_filters(filters)
	query_filters.append(["tourist_tax_return", ">", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Sales Invoice",
				filters=query_filters,
				fields=["sum(tourist_tax_return)"],
				as_list=True,
				limit=1,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_zero_rated_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is zero rated."""
	conditions = get_conditions(filters)
	try:
		return (
			frappe.db.sql(
				f"""
			select
				sum(i.base_net_amount) as total
			from
				`tabSales Invoice Item` i inner join `tabSales Invoice` s
			on
				i.parent = s.name
			where
				s.docstatus = 1 and  i.is_zero_rated = 1
				{conditions} ;
			""",
				filters,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_exempt_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is Vat Exempt."""
	conditions = get_conditions(filters)
	try:
		return (
			frappe.db.sql(
				f"""
			select
				sum(i.base_net_amount) as total
			from
				`tabSales Invoice Item` i inner join `tabSales Invoice` s
			on
				i.parent = s.name
			where
				s.docstatus = 1 and  i.is_exempt = 1
				{conditions} ;
			""",
				filters,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_conditions(filters):
	"""The conditions to be used to filter data to calculate the total sale."""
	conditions = ""
	for opts in (
		("company", " and company=%(company)s"),
		("from_date", " and posting_date>=%(from_date)s"),
		("to_date", " and posting_date<=%(to_date)s"),
	):
		if filters.get(opts[0]):
			conditions += opts[1]
	return conditions


def get_sales_conditions(filters, sales_invoice):
	"""Return Query Builder conditions for Sales Invoice report filters."""
	conditions = []
	if filters.get("company"):
		conditions.append(sales_invoice.company == filters.get("company"))
	if filters.get("from_date"):
		conditions.append(sales_invoice.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(sales_invoice.posting_date <= filters.get("to_date"))
	return conditions
