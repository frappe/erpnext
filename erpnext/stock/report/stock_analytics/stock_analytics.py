# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import datetime

import frappe
from frappe import _, scrub
from frappe.utils import get_first_day as get_first_day_of_month
from frappe.utils import get_first_day_of_week, get_quarter_start, getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.report.stock_balance.stock_balance import (
	get_item_details,
	get_items,
	get_stock_ledger_entries,
)
from erpnext.stock.utils import is_reposting_item_valuation_in_progress


def execute(filters=None):
	is_reposting_item_valuation_in_progress()
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(columns)

	return columns, data, None, chart


def get_columns(filters):
	columns = [
		{"label": _("Item"), "options": "Item", "fieldname": "name", "fieldtype": "Link", "width": 140},
		{
			"label": _("Item Name"),
			"options": "Item",
			"fieldname": "item_name",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Item Group"),
			"options": "Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Brand"), "fieldname": "brand", "fieldtype": "Data", "width": 120},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 120},
	]

	ranges = get_period_date_ranges(filters)

	for dummy, end_date in ranges:
		period = get_period(end_date, filters)

		columns.append(
			{"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120}
		)

	return columns


def get_period_date_ranges(filters):
	from dateutil.relativedelta import relativedelta

	from_date = round_down_to_nearest_frequency(filters.from_date, filters.range)
	to_date = getdate(filters.to_date)

	increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(filters.range, 1)

	periodic_daterange = []
	for dummy in range(1, 53, increment):
		if filters.range == "Weekly":
			period_end_date = from_date + relativedelta(days=6)
		else:
			period_end_date = from_date + relativedelta(months=increment, days=-1)

		if period_end_date > to_date:
			period_end_date = to_date
		periodic_daterange.append([from_date, period_end_date])

		from_date = period_end_date + relativedelta(days=1)
		if period_end_date == to_date:
			break

	return periodic_daterange


def round_down_to_nearest_frequency(date: str, frequency: str) -> datetime.datetime:
	"""Rounds down the date to nearest frequency unit.
	example:

	>>> round_down_to_nearest_frequency("2021-02-21", "Monthly")
	datetime.datetime(2021, 2, 1)

	>>> round_down_to_nearest_frequency("2021-08-21", "Yearly")
	datetime.datetime(2021, 1, 1)
	"""

	def _get_first_day_of_fiscal_year(date):
		fiscal_year = get_fiscal_year(date)
		return fiscal_year and fiscal_year[1] or date

	round_down_function = {
		"Monthly": get_first_day_of_month,
		"Quarterly": get_quarter_start,
		"Weekly": get_first_day_of_week,
		"Yearly": _get_first_day_of_fiscal_year,
	}.get(frequency, getdate)
	return round_down_function(date)


def get_period(posting_date, filters):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

	if filters.range == "Weekly":
		period = "Week " + str(posting_date.isocalendar()[1]) + " " + str(posting_date.year)
	elif filters.range == "Monthly":
		period = str(months[posting_date.month - 1]) + " " + str(posting_date.year)
	elif filters.range == "Quarterly":
		period = "Quarter " + str(((posting_date.month - 1) // 3) + 1) + " " + str(posting_date.year)
	else:
		year = get_fiscal_year(posting_date, company=filters.company)
		period = str(year[2])

	return period


def get_periodic_data(entry, filters):
	"""Structured as:
	Item 1
	        - Balance (updated and carried forward):
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	        - Jun 2021 (sum of warehouse quantities used in report)
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	        - Jul 2021 (sum of warehouse quantities used in report)
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	Item 2
	        - Balance (updated and carried forward):
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	        - Jun 2021 (sum of warehouse quantities used in report)
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	        - Jul 2021 (sum of warehouse quantities used in report)
	                        - Warehouse A : bal_qty/value
	                        - Warehouse B : bal_qty/value
	"""
	periodic_data = {}
	for d in entry:
		period = get_period(d.posting_date, filters)
		bal_qty = 0

		# if period against item does not exist yet, instantiate it
		# insert existing balance dict against period, and add/subtract to it
		if periodic_data.get(d.item_code) and not periodic_data.get(d.item_code).get(period):
			previous_balance = periodic_data[d.item_code]["balance"].copy()
			periodic_data[d.item_code][period] = previous_balance

		if d.voucher_type == "Stock Reconciliation":
			if periodic_data.get(d.item_code) and periodic_data.get(d.item_code).get("balance").get(
				d.warehouse
			):
				bal_qty = periodic_data[d.item_code]["balance"][d.warehouse]

			qty_diff = d.qty_after_transaction - bal_qty
		else:
			qty_diff = d.actual_qty

		if filters["value_quantity"] == "Quantity":
			value = qty_diff
		else:
			value = d.stock_value_difference

		# period-warehouse wise balance
		periodic_data.setdefault(d.item_code, {}).setdefault("balance", {}).setdefault(d.warehouse, 0.0)
		periodic_data.setdefault(d.item_code, {}).setdefault(period, {}).setdefault(d.warehouse, 0.0)

		periodic_data[d.item_code]["balance"][d.warehouse] += value
		periodic_data[d.item_code][period][d.warehouse] = periodic_data[d.item_code]["balance"][
			d.warehouse
		]

	return periodic_data


def get_data(filters):
	data = []
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sle, filters)
	periodic_data = get_periodic_data(sle, filters)
	ranges = get_period_date_ranges(filters)

	for dummy, item_data in item_details.items():
		row = {
			"name": item_data.name,
			"item_name": item_data.item_name,
			"item_group": item_data.item_group,
			"uom": item_data.stock_uom,
			"brand": item_data.brand,
		}
		total = 0
		for dummy, end_date in ranges:
			period = get_period(end_date, filters)
			period_data = periodic_data.get(item_data.name, {}).get(period)
			amount = sum(period_data.values()) if period_data else 0
			row[scrub(period)] = amount
			total += amount
		row["total"] = total
		data.append(row)

	return data


def get_chart_data(columns):
	labels = [d.get("label") for d in columns[5:]]
	chart = {"data": {"labels": labels, "datasets": []}}
	chart["type"] = "line"

	return chart
