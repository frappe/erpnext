# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, flt, cint
from six import iteritems
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

def execute(filters=None):
	columns = get_columns(filters)
	item_details = get_fifo_queue(filters)
	to_date = filters["to_date"]
	_func = lambda x: x[1]

	data = []
	for item, item_dict in iteritems(item_details):
		earliest_age, latest_age = 0, 0

		fifo_queue = sorted(filter(_func, item_dict["fifo_queue"]), key=_func)
		details = item_dict["details"]

		if not fifo_queue: continue

		average_age = get_average_age(fifo_queue, to_date)
		earliest_age = date_diff(to_date, fifo_queue[0][1])
		latest_age = date_diff(to_date, fifo_queue[-1][1])
		range1, range2, range3, above_range3 = get_range_age(filters, fifo_queue, to_date)

		row = [details.name, details.item_name,
			details.description, details.item_group, details.brand]

		if filters.get("show_warehouse_wise_stock"):
			row.append(details.warehouse)

		row.extend([item_dict.get("total_qty"), average_age,
			range1, range2, range3, above_range3,
			earliest_age, latest_age, details.stock_uom])

		data.append(row)

	chart_data = get_chart_data(data, filters)

	return columns, data, None, chart_data

def get_average_age(fifo_queue, to_date):
	batch_age = age_qty = total_qty = 0.0
	for batch in fifo_queue:
		batch_age = date_diff(to_date, batch[1])

		if type(batch[0]) in ['int', 'float']:
			age_qty += batch_age * batch[0]
			total_qty += batch[0]
		else:
			age_qty += batch_age * 1
			total_qty += 1

	return flt(age_qty / total_qty, 2) if total_qty else 0.0

def get_range_age(filters, fifo_queue, to_date):
	range1 = range2 = range3 = above_range3 = 0.0
	for item in fifo_queue:
		age = date_diff(to_date, item[1])

		if age <= filters.range1:
			range1 += flt(item[0])
		elif age <= filters.range2:
			range2 += flt(item[0])
		elif age <= filters.range3:
			range3 += flt(item[0])
		else:
			above_range3 += flt(item[0])

	return range1, range2, range3, above_range3

def get_columns(filters):
	range_columns = []
	setup_ageing_columns(filters, range_columns)
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100
		},
		{
			"label": _("Brand"),
			"fieldname": "brand",
			"fieldtype": "Link",
			"options": "Brand",
			"width": 100
		}]

	if filters.get("show_warehouse_wise_stock"):
		columns +=[{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100
		}]

	columns.extend([
		{
			"label": _("Available Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 100
		},
		{
			"label": _("Average Age"),
			"fieldname": "average_age",
			"fieldtype": "Float",
			"width": 100
		}])
	columns.extend(range_columns)
	columns.extend([
		{
			"label": _("Earliest"),
			"fieldname": "earliest",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("Latest"),
			"fieldname": "latest",
			"fieldtype": "Int",
			"width": 80
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100
		}
	])

	return columns

def get_fifo_queue(filters, sle=None):
	item_details = {}
	transferred_item_details = {}
	serial_no_batch_purchase_details = {}

	if sle == None:
		sle = get_stock_ledger_entries(filters)

	for d in sle:
		key = (d.name, d.warehouse) if filters.get('show_warehouse_wise_stock') else d.name
		item_details.setdefault(key, {"details": d, "fifo_queue": []})
		fifo_queue = item_details[key]["fifo_queue"]

		transferred_item_key = (d.voucher_no, d.name, d.warehouse)
		transferred_item_details.setdefault(transferred_item_key, [])

		if d.voucher_type == "Stock Reconciliation":
			d.actual_qty = flt(d.qty_after_transaction) - flt(item_details[key].get("qty_after_transaction", 0))

		serial_no_list = get_serial_nos(d.serial_no) if d.serial_no else []

		if d.actual_qty > 0:
			if transferred_item_details.get(transferred_item_key):
				batch = transferred_item_details[transferred_item_key][0]
				fifo_queue.append(batch)
				transferred_item_details[transferred_item_key].pop(0)
			else:
				if serial_no_list:
					for serial_no in serial_no_list:
						if serial_no_batch_purchase_details.get(serial_no):
							fifo_queue.append([serial_no, serial_no_batch_purchase_details.get(serial_no)])
						else:
							serial_no_batch_purchase_details.setdefault(serial_no, d.posting_date)
							fifo_queue.append([serial_no, d.posting_date])
				else:
					fifo_queue.append([d.actual_qty, d.posting_date])
		else:
			if serial_no_list:
				for serial_no in fifo_queue:
					if serial_no[0] in serial_no_list:
						fifo_queue.remove(serial_no)
			else:
				qty_to_pop = abs(d.actual_qty)
				while qty_to_pop:
					batch = fifo_queue[0] if fifo_queue else [0, None]
					if 0 < flt(batch[0]) <= qty_to_pop:
						# if batch qty > 0
						# not enough or exactly same qty in current batch, clear batch
						qty_to_pop -= flt(batch[0])
						transferred_item_details[transferred_item_key].append(fifo_queue.pop(0))
					else:
						# all from current batch
						batch[0] = flt(batch[0]) - qty_to_pop
						transferred_item_details[transferred_item_key].append([qty_to_pop, batch[1]])
						qty_to_pop = 0

		item_details[key]["qty_after_transaction"] = d.qty_after_transaction

		if "total_qty" not in item_details[key]:
			item_details[key]["total_qty"] = d.actual_qty
		else:
			item_details[key]["total_qty"] += d.actual_qty

	return item_details

def get_stock_ledger_entries(filters):
	return frappe.db.sql("""select
			item.name, item.item_name, item_group, brand, description, item.stock_uom,
			actual_qty, posting_date, voucher_type, voucher_no, serial_no, batch_no, qty_after_transaction, warehouse
		from `tabStock Ledger Entry` sle,
			(select name, item_name, description, stock_uom, brand, item_group
				from `tabItem` {item_conditions}) item
		where item_code = item.name and
			company = %(company)s and
			posting_date <= %(to_date)s and
			is_cancelled != 1
			{sle_conditions}
			order by posting_date, posting_time, sle.creation, actual_qty""" #nosec
		.format(item_conditions=get_item_conditions(filters),
			sle_conditions=get_sle_conditions(filters)), filters, as_dict=True)

def get_item_conditions(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item_code=%(item_code)s")
	if filters.get("brand"):
		conditions.append("brand=%(brand)s")

	return "where {}".format(" and ".join(conditions)) if conditions else ""

def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		lft, rgt = frappe.db.get_value('Warehouse', filters.get("warehouse"), ['lft', 'rgt'])
		conditions.append("""warehouse in (select wh.name from `tabWarehouse` wh
			where wh.lft >= {0} and rgt <= {1})""".format(lft, rgt))

	return "and {}".format(" and ".join(conditions)) if conditions else ""

def get_chart_data(data, filters):
	if not data:
		return []

	labels, datapoints = [], []

	if filters.get("show_warehouse_wise_stock"):
		return {}

	data.sort(key = lambda row: row[6], reverse=True)

	if len(data) > 10:
		data = data[:10]

	for row in data:
		labels.append(row[0])
		datapoints.append(row[6])

	return {
		"data" : {
			"labels": labels,
			"datasets": [
				{
					"name": _("Average Age"),
					"values": datapoints
				}
			]
		},
		"type" : "bar"
	}

def setup_ageing_columns(filters, range_columns):
	for i, label in enumerate(["0-{range1}".format(range1=filters["range1"]),
		"{range1}-{range2}".format(range1=cint(filters["range1"])+ 1, range2=filters["range2"]),
		"{range2}-{range3}".format(range2=cint(filters["range2"])+ 1, range3=filters["range3"]),
		"{range3}-{above}".format(range3=cint(filters["range3"])+ 1, above=_("Above"))]):
			add_column(range_columns, label="Age ("+ label +")", fieldname='range' + str(i+1))

def add_column(range_columns, label, fieldname, fieldtype='Float', width=140):
	range_columns.append(dict(
		label=label,
		fieldname=fieldname,
		fieldtype=fieldtype,
		width=width
	))