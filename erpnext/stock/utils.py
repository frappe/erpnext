# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
import json
from frappe.utils import flt, cstr, nowdate, nowtime

class InvalidWarehouseCompany(frappe.ValidationError): pass

def get_stock_value_on(warehouse=None, posting_date=None, item_code=None):
	if not posting_date: posting_date = nowdate()

	values, condition = [posting_date], ""

	if warehouse:
		
		lft, rgt, is_group = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt", "is_group"])
		
		if is_group:
			values.extend([lft, rgt])
			condition += "and exists (\
				select name from `tabWarehouse` wh where wh.name = sle.warehouse\
				and wh.lft >= %s and wh.rgt <= %s)"
		
		else:
			values.append(warehouse)
			condition += " AND warehouse = %s"

	if item_code:
		values.append(item_code)
		condition.append(" AND item_code = %s")

	stock_ledger_entries = frappe.db.sql("""
		SELECT item_code, stock_value, name, warehouse
		FROM `tabStock Ledger Entry` sle
		WHERE posting_date <= %s {0}
		ORDER BY timestamp(posting_date, posting_time) DESC, name DESC
	""".format(condition), values, as_dict=1)

	sle_map = {}
	for sle in stock_ledger_entries:
		if not sle_map.has_key((sle.item_code, sle.warehouse)):
			sle_map[(sle.item_code, sle.warehouse)] = flt(sle.stock_value)
		
	return sum(sle_map.values())

@frappe.whitelist()
def get_stock_balance(item_code, warehouse, posting_date=None, posting_time=None, with_valuation_rate=False):
	"""Returns stock balance quantity at given warehouse on given posting date or current date.

	If `with_valuation_rate` is True, will return tuple (qty, rate)"""

	from erpnext.stock.stock_ledger import get_previous_sle

	if not posting_date: posting_date = nowdate()
	if not posting_time: posting_time = nowtime()

	last_entry = get_previous_sle({
		"item_code": item_code,
		"warehouse":warehouse,
		"posting_date": posting_date,
		"posting_time": posting_time })

	if with_valuation_rate:
		return (last_entry.qty_after_transaction, last_entry.valuation_rate) if last_entry else (0.0, 0.0)
	else:
		return last_entry.qty_after_transaction if last_entry else 0.0

@frappe.whitelist()
def get_latest_stock_qty(item_code, warehouse=None):
	values, condition = [item_code], ""
	if warehouse:
		lft, rgt, is_group = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt", "is_group"])
	
		if is_group:
			values.extend([lft, rgt])
			condition += "and exists (\
				select name from `tabWarehouse` wh where wh.name = tabBin.warehouse\
				and wh.lft >= %s and wh.rgt <= %s)"
	
		else:
			values.append(warehouse)
			condition += " AND warehouse = %s"
	
	actual_qty = frappe.db.sql("""select sum(actual_qty) from tabBin
		where item_code=%s {0}""".format(condition), values)[0][0]

	return actual_qty


def get_latest_stock_balance():
	bin_map = {}
	for d in frappe.db.sql("""SELECT item_code, warehouse, stock_value as stock_value
		FROM tabBin""", as_dict=1):
			bin_map.setdefault(d.warehouse, {}).setdefault(d.item_code, flt(d.stock_value))

	return bin_map

def get_bin(item_code, warehouse):
	bin = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
	if not bin:
		bin_obj = frappe.get_doc({
			"doctype": "Bin",
			"item_code": item_code,
			"warehouse": warehouse,
		})
		bin_obj.flags.ignore_permissions = 1
		bin_obj.insert()
	else:
		bin_obj = frappe.get_doc('Bin', bin)
	bin_obj.flags.ignore_permissions = True
	return bin_obj

def update_bin(args, allow_negative_stock=False, via_landed_cost_voucher=False):
	is_stock_item = frappe.db.get_value('Item', args.get("item_code"), 'is_stock_item')
	if is_stock_item:
		bin = get_bin(args.get("item_code"), args.get("warehouse"))
		bin.update_stock(args, allow_negative_stock, via_landed_cost_voucher)
		return bin
	else:
		frappe.msgprint(_("Item {0} ignored since it is not a stock item").format(args.get("item_code")))

@frappe.whitelist()
def get_incoming_rate(args):
	"""Get Incoming Rate based on valuation method"""
	from erpnext.stock.stock_ledger import get_previous_sle
	
	if isinstance(args, basestring):
		args = json.loads(args)

	in_rate = 0
	if (args.get("serial_no") or "").strip():
		in_rate = get_avg_purchase_rate(args.get("serial_no"))
	else:
		valuation_method = get_valuation_method(args.get("item_code"))
		previous_sle = get_previous_sle(args)
		if valuation_method == 'FIFO':
			if not previous_sle:
				return 0.0
			previous_stock_queue = json.loads(previous_sle.get('stock_queue', '[]') or '[]')
			in_rate = get_fifo_rate(previous_stock_queue, args.get("qty") or 0) if previous_stock_queue else 0
		elif valuation_method == 'Moving Average':
			in_rate = previous_sle.get('valuation_rate') or 0

	return in_rate

def get_avg_purchase_rate(serial_nos):
	"""get average value of serial numbers"""

	serial_nos = get_valid_serial_nos(serial_nos)
	return flt(frappe.db.sql("""select avg(purchase_rate) from `tabSerial No`
		where name in (%s)""" % ", ".join(["%s"] * len(serial_nos)),
		tuple(serial_nos))[0][0])

def get_valuation_method(item_code):
	"""get valuation method from item or default"""
	val_method = frappe.db.get_value('Item', item_code, 'valuation_method')
	if not val_method:
		val_method = frappe.db.get_value("Stock Settings", None, "valuation_method") or "FIFO"
	return val_method

def get_fifo_rate(previous_stock_queue, qty):
	"""get FIFO (average) Rate from Queue"""
	if qty >= 0:
		total = sum(f[0] for f in previous_stock_queue)
		return sum(flt(f[0]) * flt(f[1]) for f in previous_stock_queue) / flt(total) if total else 0.0
	else:
		available_qty_for_outgoing, outgoing_cost = 0, 0
		qty_to_pop = abs(qty)
		while qty_to_pop and previous_stock_queue:
			batch = previous_stock_queue[0]
			if 0 < batch[0] <= qty_to_pop:
				# if batch qty > 0
				# not enough or exactly same qty in current batch, clear batch
				available_qty_for_outgoing += flt(batch[0])
				outgoing_cost += flt(batch[0]) * flt(batch[1])
				qty_to_pop -= batch[0]
				previous_stock_queue.pop(0)
			else:
				# all from current batch
				available_qty_for_outgoing += flt(qty_to_pop)
				outgoing_cost += flt(qty_to_pop) * flt(batch[1])
				batch[0] -= qty_to_pop
				qty_to_pop = 0

		return outgoing_cost / available_qty_for_outgoing

def get_valid_serial_nos(sr_nos, qty=0, item_code=''):
	"""split serial nos, validate and return list of valid serial nos"""
	# TODO: remove duplicates in client side
	serial_nos = cstr(sr_nos).strip().replace(',', '\n').split('\n')

	valid_serial_nos = []
	for val in serial_nos:
		if val:
			val = val.strip()
			if val in valid_serial_nos:
				frappe.throw(_("Serial number {0} entered more than once").format(val))
			else:
				valid_serial_nos.append(val)

	if qty and len(valid_serial_nos) != abs(qty):
		frappe.throw(_("{0} valid serial nos for Item {1}").format(abs(qty), item_code))

	return valid_serial_nos

def validate_warehouse_company(warehouse, company):
	warehouse_company = frappe.db.get_value("Warehouse", warehouse, "company")
	if warehouse_company and warehouse_company != company:
		frappe.throw(_("Warehouse {0} does not belong to company {1}").format(warehouse, company),
			InvalidWarehouseCompany)

def is_group_warehouse(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "is_group"):
		frappe.throw(_("Group node warehouse is not allowed to select for transactions"))
	
