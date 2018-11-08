# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import getdate, flt
from erpnext.stock.report.stock_balance.stock_balance import (get_items, get_stock_ledger_entries, get_item_details)
from erpnext.accounts.utils import get_fiscal_year
from six import iteritems

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(columns)

	return columns, data, None, chart

def get_columns(filters):
	columns = [
		{
			"label": _("Item"),
			"options":"Item",
			"fieldname": "name",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Item Name"),
			"options":"Item",
			"fieldname": "item_name",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Item Group"),
			"options":"Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"width": 140
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Data",
			"width": 120
		}]

	ranges = get_period_date_ranges(filters)

	for dummy, end_date in ranges:
		period = get_period(end_date, filters)

		columns.append({
			"label": _(period),
			"fieldname":scrub(period),
			"fieldtype": "Float",
			"width": 120
		})

	return columns

def get_period_date_ranges(filters):
		from dateutil.relativedelta import relativedelta
		from_date, to_date = getdate(filters.from_date), getdate(filters.to_date)

		increment = {
			"Monthly": 1,
			"Quarterly": 3,
			"Half-Yearly": 6,
			"Yearly": 12
		}.get(filters.range,1)

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

def get_period(posting_date, filters):
	months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

	if filters.range == 'Weekly':
		period = "Week " + str(posting_date.isocalendar()[1])
	elif filters.range == 'Monthly':
		period = months[posting_date.month - 1]
	elif filters.range == 'Quarterly':
		period = "Quarter " + str(((posting_date.month-1)//3)+1)
	else:
		year = get_fiscal_year(posting_date, company=filters.company)
		period = str(year[2])

	return period


def get_periodic_data(entry, filters):
	periodic_data = {}
	for d in entry:
		period = get_period(d.posting_date, filters)
		bal_qty = 0

		if d.voucher_type == "Stock Reconciliation":
			if periodic_data.get(d.item_code):
				bal_qty = periodic_data[d.item_code]["balance"]

			qty_diff = d.qty_after_transaction - bal_qty
		else:
			qty_diff = d.actual_qty

		if filters["value_quantity"] == 'Quantity':
			value = qty_diff
		else:
			value = d.stock_value_difference

		periodic_data.setdefault(d.item_code, {}).setdefault(period, 0.0)
		periodic_data.setdefault(d.item_code, {}).setdefault("balance", 0.0)

		periodic_data[d.item_code]["balance"] += value
		periodic_data[d.item_code][period] = periodic_data[d.item_code]["balance"]


	return periodic_data

def get_data(filters):
	data = []
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sle, filters)
	periodic_data = get_periodic_data(sle, filters)
	ranges = get_period_date_ranges(filters)

	for item, item_data in iteritems(item_details):
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
			amount = flt(periodic_data.get(item_data.name, {}).get(period))
			row[scrub(period)] = amount
			total += amount
		row["total"] = total
		data.append(row)

	return data

def get_chart_data(columns):
	labels = [d.get("label") for d in columns[4:]]
	chart = {
		"data": {
			'labels': labels,
			'datasets':[
				{ "values": ['0' for d in columns[4:]] }
			]
		}
	}
	chart["type"] = "line"

	return chart




