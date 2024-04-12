# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data, emirates, amounts_by_emirate = get_data(filters)
	return columns, data


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
	conditions = get_conditions(filters)
	try:
		return frappe.db.sql(
			f"""
			select
				s.vat_emirate as emirate, sum(i.base_net_amount) as total, sum(i.tax_amount)
			from
				`tabSales Invoice Item` i inner join `tabSales Invoice` s
			on
				i.parent = s.name
			where
				s.docstatus = 1 and  i.is_exempt != 1 and i.is_zero_rated != 1
				{conditions}
			group by
				s.vat_emirate;
			""",
			filters,
		)
	except (IndexError, TypeError):
		return 0


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
				"Purchase Invoice", filters=query_filters, fields=["sum(total)"], as_list=True, limit=1
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
				"Purchase Invoice", filters=query_filters, fields=["sum(total)"], as_list=True, limit=1
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
				"Purchase Invoice", filters=query_filters, fields=["sum(total)"], as_list=True, limit=1
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
				"Sales Invoice", filters=query_filters, fields=["sum(total)"], as_list=True, limit=1
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
