# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import date_diff, flt

def execute(filters=None):

	columns = get_columns()
	item_details = get_fifo_queue(filters)
	to_date = filters["to_date"]
	data = []
	for item, item_dict in item_details.items():
		fifo_queue = item_dict["fifo_queue"]
		details = item_dict["details"]
		if not fifo_queue: continue

		average_age = get_average_age(fifo_queue, to_date)
		earliest_age = date_diff(to_date, fifo_queue[0][1])
		latest_age = date_diff(to_date, fifo_queue[-1][1])

		data.append([item, details.item_name, details.description, details.item_group,
			details.brand, average_age, earliest_age, latest_age, details.stock_uom])

	return columns, data

def get_average_age(fifo_queue, to_date):
	batch_age = age_qty = total_qty = 0.0
	for batch in fifo_queue:
		batch_age = date_diff(to_date, batch[1])
		age_qty += batch_age * batch[0]
		total_qty += batch[0]

	return (age_qty / total_qty) if total_qty else 0.0

def get_columns():
	return [_("Item Code") + ":Link/Item:100", _("Item Name") + "::100", _("Description") + "::200",
		_("Item Group") + ":Link/Item Group:100", _("Brand") + ":Link/Brand:100", _("Average Age") + ":Float:100",
		_("Earliest") + ":Int:80", _("Latest") + ":Int:80", _("UOM") + ":Link/UOM:100"]

def get_fifo_queue(filters):
	item_details = {}
	for d in get_stock_ledger_entries(filters):
		item_details.setdefault(d.name, {"details": d, "fifo_queue": []})
		fifo_queue = item_details[d.name]["fifo_queue"]

		if d.voucher_type == "Stock Reconciliation":
			d.actual_qty = flt(d.qty_after_transaction) - flt(item_details[d.name].get("qty_after_transaction", 0))

		if d.actual_qty > 0:
			fifo_queue.append([d.actual_qty, d.posting_date])
		else:
			qty_to_pop = abs(d.actual_qty)
			while qty_to_pop:
				batch = fifo_queue[0] if fifo_queue else [0, None]
				if 0 < batch[0] <= qty_to_pop:
					# if batch qty > 0
					# not enough or exactly same qty in current batch, clear batch
					qty_to_pop -= batch[0]
					fifo_queue.pop(0)
				else:
					# all from current batch
					batch[0] -= qty_to_pop
					qty_to_pop = 0

		item_details[d.name]["qty_after_transaction"] = d.qty_after_transaction

	return item_details

def get_stock_ledger_entries(filters):
	return frappe.db.sql("""select
			item.name, item.item_name, item_group, brand, description, item.stock_uom,
			actual_qty, posting_date, voucher_type, qty_after_transaction
		from `tabStock Ledger Entry` sle,
			(select name, item_name, description, stock_uom, brand, item_group
				from `tabItem` {item_conditions}) item
		where item_code = item.name and
			company = %(company)s and
			posting_date <= %(to_date)s
			{sle_conditions}
			order by posting_date, posting_time, sle.name"""\
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
