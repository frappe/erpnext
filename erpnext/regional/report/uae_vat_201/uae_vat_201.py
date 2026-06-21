# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from html import escape
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Sum
from frappe.utils import flt

from erpnext import get_region

# Per-request memoization cache for the helper functions below. Stored on
# ``frappe.local`` so concurrent requests under gevent/threaded workers
# never share or race on this state; cleared at the start of every
# ``execute()`` so each report run gets fresh data.
_CACHE_ATTR = "_uae_vat_201_cache"


def _get_cache():
	cache = getattr(frappe.local, _CACHE_ATTR, None)
	if cache is None:
		cache = {}
		setattr(frappe.local, _CACHE_ATTR, cache)
	return cache


def _drill_down_link(text, filters, **extra):
	"""Return an `<a>` tag pointing at the UAE VAT Register report.

	Filter values are URL-encoded so company names with ``&`` or other
	reserved characters don't break the query string, and the link text
	is HTML-escaped to prevent injection from user-controlled fields.
	"""
	params = {}
	for key in ("company", "from_date", "to_date"):
		value = (filters or {}).get(key)
		if value:
			params[key] = value
	for key, value in extra.items():
		if value is not None:
			params[key] = value
	query = urlencode(params)
	return f'<a href="/app/query-report/UAE VAT Register?{query}">{escape(str(text))}</a>'


def _cached(fn):
	def wrapper(filters, *args, **kwargs):
		# ``frappe.local`` survives across unit-test methods (it is request
		# scoped, not test scoped). Two tests that call the same helper with
		# equivalent filter dicts would otherwise share a cached value from
		# the first test's data set. Bypass the cache in tests so each
		# call hits the DB; production callers (one execute() per HTTP
		# request, cache cleared at its start) still see the optimisation.
		if frappe.flags.in_test:
			return fn(filters, *args, **kwargs)
		cache = _get_cache()
		key = (fn.__name__, tuple(sorted((filters or {}).items())))
		if key not in cache:
			cache[key] = fn(filters, *args, **kwargs)
		return cache[key]

	return wrapper


def execute(filters=None):
	filters = filters or {}
	validate_company_region(filters)
	_get_cache().clear()
	columns = get_columns()
	data = get_data(filters)
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
	amounts_by_emirate = append_vat_on_sales(data, filters)
	append_vat_on_expenses(data, filters)
	net_vat_due(data, filters, amounts_by_emirate)

	dubai_label_override = _company_emirate_label(filters)

	final_data = []
	for row in data:
		key = row.get("_key")
		legend = row.get("legend")
		new_legend = legend

		if key and key.startswith("emirate:"):
			emirate = key.split(":", 1)[1]
			label = dubai_label_override if emirate == "Dubai" and dubai_label_override else legend
			new_legend = _drill_down_link(
				label, filters, doc_type="Sales Invoice", vat=emirate, category="Standard"
			)
		elif key == "reverse_charge_supplies":
			new_legend = _drill_down_link(legend, filters, doc_type="Purchase Invoice", reverse_charge="Y")
		elif key == "zero_rated":
			new_legend = _drill_down_link(legend, filters, doc_type="Sales Invoice", category="Zero Rated")
		elif key == "exempt_supplies":
			new_legend = _drill_down_link(legend, filters, doc_type="Sales Invoice", category="Exempt Rated")
		elif key == "standard_rated_expenses":
			new_legend = _drill_down_link(legend, filters, doc_type="Purchase Invoice")

		final_data.append(
			{
				"no": row.get("no"),
				"legend": new_legend,
				"amount": row.get("amount"),
				"vat_amount": row.get("vat_amount"),
			}
		)

	return final_data


def _company_emirate_label(filters):
	"""Return the home-emirate label for the company in ``filters`` if any.

	The Dubai row is conventionally relabeled with the actual emirate of
	the filtered company's primary address. Falls back to ``None`` when
	no company filter is set or the address has no emirate, in which case
	callers keep the original "Standard rated supplies in Dubai" wording.
	"""
	company = (filters or {}).get("company")
	if not company:
		return None
	address = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company],
			["Address", "is_your_company_address", "=", 1],
		],
		fields=["emirate"],
		limit=1,
	)
	if address and address[0].get("emirate"):
		return _("Standard rated supplies in {0}").format(address[0]["emirate"])
	return None


def append_vat_on_sales(data, filters):
	"""Appends Sales and All Other Outputs."""
	append_data(data, "", _("VAT on Sales and All Other Outputs"), "", "")

	amounts_by_emirate = standard_rated_expenses_emiratewise(data, filters)

	si_amount = amounts_by_emirate[1]
	si_vat = amounts_by_emirate[2]

	append_data(
		data,
		"2",
		_("Tax Refunds provided to Tourists under the Tax Refunds for Tourists Scheme"),
		format_currency_signed((-1) * get_tourist_tax_return_total(filters)),
		format_currency_signed((-1) * get_tourist_tax_return_tax(filters)),
	)

	append_data(
		data,
		"3",
		_("Supplies subject to the reverse charge provision"),
		frappe.format(get_reverse_charge_total(filters), "Currency"),
		frappe.format(get_reverse_charge_tax(filters), "Currency"),
		key="reverse_charge_supplies",
	)

	append_data(
		data,
		"4",
		_("Zero Rated"),
		frappe.format(get_zero_rated_total(filters), "Currency"),
		"-",
		key="zero_rated",
	)

	append_data(
		data,
		"5",
		_("Exempt Supplies"),
		frappe.format(get_exempt_total(filters), "Currency"),
		"-",
		key="exempt_supplies",
	)

	append_data(
		data,
		"8",
		_("Total"),
		frappe.format(
			(-1) * get_tourist_tax_return_total(filters)
			+ get_reverse_charge_total(filters)
			+ get_zero_rated_total(filters)
			+ get_exempt_total(filters)
			+ sum(si_amount),
			"Currency",
		),
		frappe.format(
			(-1) * get_tourist_tax_return_tax(filters) + get_reverse_charge_tax(filters) + sum(si_vat),
			"Currency",
		),
	)

	append_data(data, "", "", "", "")

	return amounts_by_emirate


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
	return amounts_by_emirate


def append_emiratewise_expenses(data, emirates, amounts_by_emirate):
	"""Append emiratewise standard rated expenses and vat."""
	s_amount = []
	v_amount = []
	for no, emirate in enumerate(emirates, 97):
		if emirate in amounts_by_emirate:
			amounts_by_emirate[emirate]["no"] = _("1{0}").format(chr(no))
			amounts_by_emirate[emirate]["legend"] = _("Standard rated supplies in {0}").format(emirate)
			amounts_by_emirate[emirate]["_key"] = f"emirate:{emirate}"
			data.append(amounts_by_emirate[emirate])

			s_amount.append(amounts_by_emirate[emirate].get("raw_amount") or 0)
			v_amount.append(amounts_by_emirate[emirate].get("raw_vat_amount") or 0)
		else:
			append_data(
				data,
				_("1{0}").format(chr(no)),
				_("Standard rated supplies in {0}").format(emirate),
				frappe.format(0, "Currency"),
				frappe.format(0, "Currency"),
				key=f"emirate:{emirate}",
			)
	return amounts_by_emirate, s_amount, v_amount


def append_vat_on_expenses(data, filters):
	"""Appends Expenses and All Other Inputs."""
	append_data(data, "", _("VAT on Expenses and All Other Inputs"), "", "")
	append_data(
		data,
		"9",
		_("Standard Rated Expenses"),
		frappe.format(get_standard_rated_expenses_total(filters), "Currency"),
		frappe.format(get_standard_rated_expenses_tax(filters), "Currency"),
		key="standard_rated_expenses",
	)
	append_data(
		data,
		"10",
		_("Supplies subject to the reverse charge provision"),
		frappe.format(get_reverse_charge_recoverable_total(filters), "Currency"),
		frappe.format(get_reverse_charge_recoverable_tax(filters), "Currency"),
	)

	append_data(
		data,
		"11",
		_("Total"),
		frappe.format(
			get_standard_rated_expenses_total(filters) + get_reverse_charge_recoverable_total(filters),
			"Currency",
		),
		frappe.format(
			get_standard_rated_expenses_tax(filters) + get_reverse_charge_recoverable_tax(filters),
			"Currency",
		),
	)


def net_vat_due(data, filters, amounts_by_emirate):
	si_vat = amounts_by_emirate[2]

	append_data(data, "", "", "", "")
	append_data(data, "", _("Net VAT Due"), "", "")
	append_data(
		data,
		"12",
		_("Total value of due tax for the period"),
		frappe.format(0.00, "Currency"),
		frappe.format(
			sum(si_vat) + (-1) * get_tourist_tax_return_tax(filters) + get_reverse_charge_tax(filters),
			"Currency",
		),
	)
	append_data(
		data,
		"13",
		_("Total value of recoverable tax for the period"),
		frappe.format(0.00, "Currency"),
		frappe.format(
			get_standard_rated_expenses_tax(filters) + get_reverse_charge_recoverable_tax(filters),
			"Currency",
		),
	)

	# Calculate payable tax: Due Tax - Recoverable Tax
	due_tax = sum(si_vat) + (-1) * get_tourist_tax_return_tax(filters) + get_reverse_charge_tax(filters)
	recoverable_tax = get_standard_rated_expenses_tax(filters) + get_reverse_charge_recoverable_tax(filters)
	payable_tax = due_tax - recoverable_tax

	append_data(
		data,
		"14",
		_("Payable tax for the period"),
		frappe.format(0.00, "Currency"),
		frappe.format(payable_tax, "Currency"),
	)


def append_data(data, no, legend, amount, vat_amount, key=None):
	"""Append one row to ``data``.

	``key`` (when provided) is a language-independent identifier used by
	``get_data`` to decide which rows get drill-down links. Without it,
	dispatch would have to match the localized ``legend`` text and would
	silently break under any non-English language.
	"""
	data.append({"no": no, "legend": legend, "amount": amount, "vat_amount": vat_amount, "_key": key})


def format_currency_signed(value):
	"""Format a number as currency, placing the minus sign *before* the currency symbol
	when negative (e.g. "-د.إ 5,000.00" rather than "د.إ -5,000.00")."""
	if value is None:
		value = 0
	if value < 0:
		return "-" + frappe.format(abs(value), "Currency")
	return frappe.format(value, "Currency")


@_cached
def get_total_emiratewise(filters):
	"""Returns Emiratewise Amount and Taxes."""
	si = frappe.qb.DocType("Sales Invoice")
	sii = frappe.qb.DocType("Sales Invoice Item")
	query = (
		frappe.qb.from_(sii)
		.inner_join(si)
		.on(sii.parent == si.name)
		.where(si.docstatus == 1)
		.where(sii.is_exempt != 1)
		.where(sii.is_zero_rated != 1)
		.groupby(si.vat_emirate)
		.select(
			si.vat_emirate.as_("emirate"),
			Coalesce(Sum(sii.base_net_amount), 0).as_("total"),
			Coalesce(Sum(sii.tax_amount), 0),
		)
	)
	query = _apply_period_filters(query, si, filters)
	return query.run()


def get_emirates():
	"""Returns a List of emirates in the order that they are to be displayed."""
	return ["Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Umm Al Quwain", "Ras Al Khaimah", "Fujairah"]


def _apply_period_filters(query, table, filters):
	"""Apply company / posting-date filters from ``filters`` to a frappe.qb query."""
	filters = filters or {}
	if filters.get("company"):
		query = query.where(table.company == filters["company"])
	if filters.get("from_date"):
		query = query.where(table.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(table.posting_date <= filters["to_date"])
	return query


def _sum_invoice_field(doctype, field, filters, extra_where=None):
	"""Return ``sum(field)`` on a submitted invoice doctype with the standard
	period filters. ``extra_where(table)`` may yield additional ``Criterion``s."""
	table = frappe.qb.DocType(doctype)
	query = frappe.qb.from_(table).where(table.docstatus == 1).select(Coalesce(Sum(table[field]), 0))
	query = _apply_period_filters(query, table, filters)
	if extra_where is not None:
		for criterion in extra_where(table):
			query = query.where(criterion)
	result = query.run()
	return flt(result[0][0]) if result else 0


def _sum_item_field(parent_doctype, child_doctype, field, filters, extra_item_where=None):
	"""Return ``sum(child.field)`` for child rows of submitted parents in the period."""
	parent = frappe.qb.DocType(parent_doctype)
	child = frappe.qb.DocType(child_doctype)
	query = (
		frappe.qb.from_(child)
		.inner_join(parent)
		.on(child.parent == parent.name)
		.where(parent.docstatus == 1)
		.select(Coalesce(Sum(child[field]), 0))
	)
	query = _apply_period_filters(query, parent, filters)
	if extra_item_where is not None:
		for criterion in extra_item_where(child):
			query = query.where(criterion)
	result = query.run()
	return flt(result[0][0]) if result else 0


def _sum_vat_account_debit(filters, recoverable=False):
	"""Sum of GL debit for reverse-charge purchases booked to UAE VAT Accounts.

	With ``recoverable=True``, multiplies the debit by the invoice's
	``recoverable_reverse_charge`` percentage (and only sums rows with a
	non-zero recoverable rate). Returns 0 when no company filter is set,
	since UAE VAT Accounts are scoped per company.
	"""
	if not (filters or {}).get("company"):
		return 0

	pi = frappe.qb.DocType("Purchase Invoice")
	gl = frappe.qb.DocType("GL Entry")
	uva = frappe.qb.DocType("UAE VAT Account")

	vat_accounts = frappe.qb.from_(uva).where(uva.parent == filters["company"]).select(uva.account)

	amount = gl.debit
	if recoverable:
		amount = amount * pi.recoverable_reverse_charge / 100

	query = (
		frappe.qb.from_(pi)
		.inner_join(gl)
		.on(gl.voucher_no == pi.name)
		.where(pi.reverse_charge == "Y")
		.where(pi.docstatus == 1)
		.where(gl.docstatus == 1)
		.where(gl.account.isin(vat_accounts))
		.select(Coalesce(Sum(amount), 0))
	)
	if recoverable:
		query = query.where(pi.recoverable_reverse_charge > 0)
	query = _apply_period_filters(query, pi, filters)
	result = query.run()
	return flt(result[0][0]) if result else 0


@_cached
def get_reverse_charge_total(filters):
	"""Returns the sum of the total of each Purchase invoice made."""
	return _sum_invoice_field(
		"Purchase Invoice",
		"base_net_total",
		filters,
		extra_where=lambda t: [t.reverse_charge == "Y"],
	)


@_cached
def get_reverse_charge_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	return _sum_vat_account_debit(filters)


@_cached
def get_reverse_charge_recoverable_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	return _sum_invoice_field(
		"Purchase Invoice",
		"base_net_total",
		filters,
		extra_where=lambda t: [t.reverse_charge == "Y", t.recoverable_reverse_charge > 0],
	)


@_cached
def get_reverse_charge_recoverable_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	return _sum_vat_account_debit(filters, recoverable=True)


@_cached
def get_standard_rated_expenses_total(filters):
	"""Returns the sum of the total of each Purchase invoice made with recoverable reverse charge."""
	return _sum_invoice_field(
		"Purchase Invoice",
		"base_net_total",
		filters,
		extra_where=lambda t: [t.recoverable_standard_rated_expenses > 0],
	)


@_cached
def get_standard_rated_expenses_tax(filters):
	"""Returns the sum of the tax of each Purchase invoice made."""
	return _sum_invoice_field(
		"Purchase Invoice",
		"recoverable_standard_rated_expenses",
		filters,
		extra_where=lambda t: [t.recoverable_standard_rated_expenses > 0],
	)


@_cached
def get_tourist_tax_return_total(filters):
	"""Returns the sum of the total of each Sales invoice with non zero tourist_tax_return."""
	return _sum_invoice_field(
		"Sales Invoice",
		"base_net_total",
		filters,
		extra_where=lambda t: [t.tourist_tax_return > 0],
	)


@_cached
def get_tourist_tax_return_tax(filters):
	"""Returns the sum of the tax of each Sales invoice with non zero tourist_tax_return."""
	return _sum_invoice_field(
		"Sales Invoice",
		"tourist_tax_return",
		filters,
		extra_where=lambda t: [t.tourist_tax_return > 0],
	)


@_cached
def get_zero_rated_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is zero rated."""
	return _sum_item_field(
		"Sales Invoice",
		"Sales Invoice Item",
		"base_net_amount",
		filters,
		extra_item_where=lambda i: [i.is_zero_rated == 1],
	)


@_cached
def get_exempt_total(filters):
	"""Returns the sum of each Sales Invoice Item Amount which is Vat Exempt."""
	return _sum_item_field(
		"Sales Invoice",
		"Sales Invoice Item",
		"base_net_amount",
		filters,
		extra_item_where=lambda i: [i.is_exempt == 1],
	)
