# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Sum

from erpnext import get_region


def execute(filters=None):
	validate_company(filters)
	validate_company_region(filters)
	columns = get_columns()
	data, emirates, amounts_by_emirate = get_data(filters)
	return columns, data


def validate_company(filters):
	if not filters.get("company"):
		frappe.throw(_("Company is required"), title=_("Missing Company"))
	frappe.has_permission("Company", doc=filters.get("company"), throw=True)


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
	append_supplies_without_emirate(data, emirates, amounts_by_emirate)
	return amounts_by_emirate


def append_supplies_without_emirate(data, emirates, amounts_by_emirate):
	"""Append standard rated supplies of invoices with no VAT Emirate, so they are not left out of box 1."""
	rows = [row for emirate, row in amounts_by_emirate.items() if emirate not in emirates]
	if not rows:
		return
	append_data(
		data,
		"1",
		_("Standard rated supplies with no VAT Emirate"),
		frappe.format(sum(row["raw_amount"] for row in rows), "Currency"),
		frappe.format(sum(row["raw_vat_amount"] for row in rows), "Currency"),
	)


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
	for condition in get_conditions(filters, s):
		query = query.where(condition)
	return dict(query.run())


def get_emiratewise_vat_amount(filters):
	"""Returns emiratewise VAT on standard rated supplies in company currency.

	Item Wise Tax Detail.amount is the item's share of the tax row already converted to
	company currency, so it keeps the item level exempt / zero rated split.
	"""
	i = frappe.qb.DocType("Sales Invoice Item")
	s = frappe.qb.DocType("Sales Invoice")
	t = frappe.qb.DocType("Sales Taxes and Charges")
	d = frappe.qb.DocType("Item Wise Tax Detail")
	uae_vat = frappe.qb.DocType("UAE VAT Account")
	query = (
		frappe.qb.from_(d)
		.inner_join(s)
		.on(d.parent == s.name)
		.inner_join(i)
		.on(d.item_row == i.name)
		.inner_join(t)
		.on(d.tax_row == t.name)
		.select(s.vat_emirate, Sum(d.amount))
		.where(
			(d.parenttype == "Sales Invoice")
			& (s.docstatus == 1)
			& (i.is_exempt != 1)
			& (i.is_zero_rated != 1)
			& t.account_head.isin(
				frappe.qb.from_(uae_vat)
				.select(uae_vat.account)
				.where(uae_vat.parent == filters.get("company"))
			)
		)
		.groupby(s.vat_emirate)
	)
	for condition in get_conditions(filters, s):
		query = query.where(condition)
	return dict(query.run())


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
	if filters.get("to_date"):
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
				"Purchase Invoice",
				filters=query_filters,
				fields=[{"SUM": "base_total"}],
				as_list=True,
				limit=1,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_reverse_charge_tax(filters):
	"""Returns the reverse charge VAT of Purchase Invoices, net of their debit notes."""
	return get_reverse_charge_vat(filters)


def get_reverse_charge_recoverable_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	query_filters = get_filters(filters)
	query_filters.append(["reverse_charge", "=", "Y"])
	query_filters.append(["recoverable_reverse_charge", ">", "0"])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice",
				filters=query_filters,
				fields=[{"SUM": "base_total"}],
				as_list=True,
				limit=1,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_reverse_charge_recoverable_tax(filters):
	"""Returns the recoverable reverse charge VAT of Purchase Invoices, net of their debit notes."""
	return get_reverse_charge_vat(filters, recoverable=True)


def get_reverse_charge_vat(filters, recoverable=False):
	"""Sums the UAE VAT rows of reverse charge invoices, so debit notes reduce the total."""
	p = frappe.qb.DocType("Purchase Invoice")
	t = frappe.qb.DocType("Purchase Taxes and Charges")
	uae_vat = frappe.qb.DocType("UAE VAT Account")
	tax = t.base_tax_amount_after_discount_amount
	if recoverable:
		tax = tax * p.recoverable_reverse_charge / 100
	query = (
		frappe.qb.from_(t)
		.inner_join(p)
		.on(t.parent == p.name)
		.select(Sum(tax))
		.where(
			(t.parenttype == "Purchase Invoice")
			& (p.reverse_charge == "Y")
			& (p.docstatus == 1)
			& t.category.isin(["Total", "Valuation and Total"])
			& t.account_head.isin(
				frappe.qb.from_(uae_vat)
				.select(uae_vat.account)
				.where(uae_vat.parent == filters.get("company"))
			)
		)
	)
	if recoverable:
		query = query.where(p.recoverable_reverse_charge > 0)
	for condition in get_conditions_join(filters, p):
		query = query.where(condition)
	return query.run()[0][0] or 0


def get_conditions_join(filters, p):
	"""The conditions to be used to filter data to calculate the total vat."""
	conditions = []
	if filters.get("company"):
		conditions.append(p.company == filters.get("company"))
	if filters.get("from_date"):
		conditions.append(p.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(p.posting_date <= filters.get("to_date"))
	return conditions


def get_standard_rated_expenses_total(filters):
	"""Returns the net amount of the Purchase Invoice lines with UAE VAT, on invoices with recoverable VAT."""
	i = frappe.qb.DocType("Purchase Invoice Item")
	p = frappe.qb.DocType("Purchase Invoice")
	query = (
		frappe.qb.from_(i)
		.inner_join(p)
		.on(i.parent == p.name)
		.select(Sum(i.base_net_amount))
		.where(
			(p.docstatus == 1)
			& (p.recoverable_standard_rated_expenses != 0)
			& i.name.isin(get_purchase_items_with_vat(filters))
		)
	)
	for condition in get_conditions_join(filters, p):
		query = query.where(condition)
	return query.run()[0][0] or 0


def get_purchase_items_with_vat(filters):
	"""Returns a sub query of the Purchase Invoice Item rows that carry UAE VAT."""
	d = frappe.qb.DocType("Item Wise Tax Detail")
	t = frappe.qb.DocType("Purchase Taxes and Charges")
	uae_vat = frappe.qb.DocType("UAE VAT Account")
	return (
		frappe.qb.from_(d)
		.inner_join(t)
		.on(d.tax_row == t.name)
		.select(d.item_row)
		.where(
			(d.parenttype == "Purchase Invoice")
			& (d.amount != 0)
			& t.account_head.isin(
				frappe.qb.from_(uae_vat)
				.select(uae_vat.account)
				.where(uae_vat.parent == filters.get("company"))
			)
		)
	)


def get_standard_rated_expenses_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	query_filters = get_filters(filters)
	query_filters.append(["recoverable_standard_rated_expenses", "!=", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Purchase Invoice",
				filters=query_filters,
				fields=[{"SUM": "recoverable_standard_rated_expenses"}],
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
	query_filters.append(["tourist_tax_return", "!=", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Sales Invoice", filters=query_filters, fields=[{"SUM": "base_total"}], as_list=True, limit=1
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_tourist_tax_return_tax(filters):
	"""Returns the sum of the tax of each Sales invoice with non zero tourist_tax_return."""
	query_filters = get_filters(filters)
	query_filters.append(["tourist_tax_return", "!=", 0])
	query_filters.append(["docstatus", "=", 1])
	try:
		return (
			frappe.db.get_all(
				"Sales Invoice",
				filters=query_filters,
				fields=[{"SUM": "tourist_tax_return"}],
				as_list=True,
				limit=1,
			)[0][0]
			or 0
		)
	except (IndexError, TypeError):
		return 0


def get_zero_rated_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is zero rated."""
	i = frappe.qb.DocType("Sales Invoice Item")
	s = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(i)
		.inner_join(s)
		.on(i.parent == s.name)
		.select(Sum(i.base_net_amount).as_("total"))
		.where((s.docstatus == 1) & (i.is_zero_rated == 1))
	)
	for condition in get_conditions(filters, s):
		query = query.where(condition)
	try:
		return query.run()[0][0] or 0
	except (IndexError, TypeError):
		return 0


def get_exempt_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is Vat Exempt."""
	i = frappe.qb.DocType("Sales Invoice Item")
	s = frappe.qb.DocType("Sales Invoice")
	query = (
		frappe.qb.from_(i)
		.inner_join(s)
		.on(i.parent == s.name)
		.select(Sum(i.base_net_amount).as_("total"))
		.where((s.docstatus == 1) & (i.is_exempt == 1))
	)
	for condition in get_conditions(filters, s):
		query = query.where(condition)
	try:
		return query.run()[0][0] or 0
	except (IndexError, TypeError):
		return 0


def get_conditions(filters, s):
	"""The conditions to be used to filter data to calculate the total sale."""
	conditions = []
	if filters.get("company"):
		conditions.append(s.company == filters.get("company"))
	if filters.get("from_date"):
		conditions.append(s.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		conditions.append(s.posting_date <= filters.get("to_date"))
	return conditions
