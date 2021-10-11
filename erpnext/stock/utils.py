# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import cstr, flt, get_link_to_form, nowdate, nowtime
from six import string_types

import erpnext


class InvalidWarehouseCompany(frappe.ValidationError): pass

def get_stock_value_from_bin(warehouse=None, item_code=None):
	values = {}
	conditions = ""
	if warehouse:
		conditions += """ and `tabBin`.warehouse in (
						select w2.name from `tabWarehouse` w1
						join `tabWarehouse` w2 on
						w1.name = %(warehouse)s
						and w2.lft between w1.lft and w1.rgt
						) """

		values['warehouse'] = warehouse

	if item_code:
		conditions += " and `tabBin`.item_code = %(item_code)s"

		values['item_code'] = item_code

	query = """select sum(stock_value) from `tabBin`, `tabItem` where 1 = 1
		and `tabItem`.name = `tabBin`.item_code and ifnull(`tabItem`.disabled, 0) = 0 %s""" % conditions

	stock_value = frappe.db.sql(query, values)

	return stock_value

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
		condition += " AND item_code = %s"

	stock_ledger_entries = frappe.db.sql("""
		SELECT item_code, stock_value, name, warehouse
		FROM `tabStock Ledger Entry` sle
		WHERE posting_date <= %s {0}
			and is_cancelled = 0
		ORDER BY timestamp(posting_date, posting_time) DESC, creation DESC
	""".format(condition), values, as_dict=1)

	sle_map = {}
	for sle in stock_ledger_entries:
		if not (sle.item_code, sle.warehouse) in sle_map:
			sle_map[(sle.item_code, sle.warehouse)] = flt(sle.stock_value)

	return sum(sle_map.values())

@frappe.whitelist()
def get_stock_balance(item_code, warehouse, posting_date=None, posting_time=None,
	with_valuation_rate=False, with_serial_no=False):
	"""Returns stock balance quantity at given warehouse on given posting date or current date.

	If `with_valuation_rate` is True, will return tuple (qty, rate)"""

	from erpnext.stock.stock_ledger import get_previous_sle

	if not posting_date: posting_date = nowdate()
	if not posting_time: posting_time = nowtime()

	args = {
		"item_code": item_code,
		"warehouse":warehouse,
		"posting_date": posting_date,
		"posting_time": posting_time
	}

	last_entry = get_previous_sle(args)

	if with_valuation_rate:
		if with_serial_no:
			serial_nos = last_entry.get("serial_no")

			if (serial_nos and
				len(get_serial_nos_data(serial_nos)) < last_entry.qty_after_transaction):
				serial_nos = get_serial_nos_data_after_transactions(args)

			return ((last_entry.qty_after_transaction, last_entry.valuation_rate, serial_nos)
				if last_entry else (0.0, 0.0, 0.0))
		else:
			return (last_entry.qty_after_transaction, last_entry.valuation_rate) if last_entry else (0.0, 0.0)
	else:
		return last_entry.qty_after_transaction if last_entry else 0.0

def get_serial_nos_data_after_transactions(args):
	serial_nos = []
	data = frappe.db.sql(""" SELECT serial_no, actual_qty
		FROM `tabStock Ledger Entry`
		WHERE
			item_code = %(item_code)s and warehouse = %(warehouse)s
			and timestamp(posting_date, posting_time) < timestamp(%(posting_date)s, %(posting_time)s)
			order by posting_date, posting_time asc """, args, as_dict=1)

	for d in data:
		if d.actual_qty > 0:
			serial_nos.extend(get_serial_nos_data(d.serial_no))
		else:
			serial_nos = list(set(serial_nos) - set(get_serial_nos_data(d.serial_no)))

	return '\n'.join(serial_nos)

def get_serial_nos_data(serial_nos):
	from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
	return get_serial_nos(serial_nos)

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
		bin_obj = frappe.get_doc('Bin', bin, for_update=True)
	bin_obj.flags.ignore_permissions = True
	return bin_obj

def get_or_make_bin(item_code, warehouse) -> str:
	bin_record = frappe.db.get_value('Bin', {'item_code': item_code, 'warehouse': warehouse})

	if not bin_record:
		bin_obj = frappe.get_doc({
			"doctype": "Bin",
			"item_code": item_code,
			"warehouse": warehouse,
		})
		bin_obj.flags.ignore_permissions = 1
		bin_obj.insert()
		bin_record = bin_obj.name

	return bin_record

def update_bin(args, allow_negative_stock=False, via_landed_cost_voucher=False):
	from erpnext.stock.doctype.bin.bin import update_stock
	is_stock_item = frappe.get_cached_value('Item', args.get("item_code"), 'is_stock_item')
	if is_stock_item:
		bin_record = get_or_make_bin(args.get("item_code"), args.get("warehouse"))
		update_stock(bin_record, args, allow_negative_stock, via_landed_cost_voucher)
	else:
		frappe.msgprint(_("Item {0} ignored since it is not a stock item").format(args.get("item_code")))

@frappe.whitelist()
def get_incoming_rate(args, raise_error_if_no_rate=True):
	"""Get Incoming Rate based on valuation method"""
	from erpnext.stock.stock_ledger import get_previous_sle, get_valuation_rate
	if isinstance(args, string_types):
		args = json.loads(args)

	in_rate = 0
	if (args.get("serial_no") or "").strip():
		in_rate = get_avg_purchase_rate(args.get("serial_no"))
	else:
		valuation_method = get_valuation_method(args.get("item_code"))
		previous_sle = get_previous_sle(args)
		if valuation_method == 'FIFO':
			if previous_sle:
				previous_stock_queue = json.loads(previous_sle.get('stock_queue', '[]') or '[]')
				in_rate = get_fifo_rate(previous_stock_queue, args.get("qty") or 0) if previous_stock_queue else 0
		elif valuation_method == 'Moving Average':
			in_rate = previous_sle.get('valuation_rate') or 0

	if not in_rate:
		voucher_no = args.get('voucher_no') or args.get('name')
		in_rate = get_valuation_rate(args.get('item_code'), args.get('warehouse'),
			args.get('voucher_type'), voucher_no, args.get('allow_zero_valuation'),
			currency=erpnext.get_company_currency(args.get('company')), company=args.get('company'),
			raise_error_if_no_rate=raise_error_if_no_rate)

	return flt(in_rate)

def get_avg_purchase_rate(serial_nos):
	"""get average value of serial numbers"""

	serial_nos = get_valid_serial_nos(serial_nos)
	return flt(frappe.db.sql("""select avg(purchase_rate) from `tabSerial No`
		where name in (%s)""" % ", ".join(["%s"] * len(serial_nos)),
		tuple(serial_nos))[0][0])

def get_valuation_method(item_code):
	"""get valuation method from item or default"""
	val_method = frappe.db.get_value('Item', item_code, 'valuation_method', cache=True)
	if not val_method:
		val_method = frappe.db.get_value("Stock Settings", None, "valuation_method") or "FIFO"
	return val_method

def get_fifo_rate(previous_stock_queue, qty):
	"""get FIFO (average) Rate from Queue"""
	if flt(qty) >= 0:
		total = sum(f[0] for f in previous_stock_queue)
		return sum(flt(f[0]) * flt(f[1]) for f in previous_stock_queue) / flt(total) if total else 0.0
	else:
		available_qty_for_outgoing, outgoing_cost = 0, 0
		qty_to_pop = abs(flt(qty))
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
	warehouse_company = frappe.db.get_value("Warehouse", warehouse, "company", cache=True)
	if warehouse_company and warehouse_company != company:
		frappe.throw(_("Warehouse {0} does not belong to company {1}").format(warehouse, company),
			InvalidWarehouseCompany)

def is_group_warehouse(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "is_group", cache=True):
		frappe.throw(_("Group node warehouse is not allowed to select for transactions"))

def validate_disabled_warehouse(warehouse):
	if frappe.db.get_value("Warehouse", warehouse, "disabled", cache=True):
		frappe.throw(_("Disabled Warehouse {0} cannot be used for this transaction.").format(get_link_to_form('Warehouse', warehouse)))

def update_included_uom_in_report(columns, result, include_uom, conversion_factors):
	if not include_uom or not conversion_factors:
		return

	convertible_cols = {}
	is_dict_obj = False
	if isinstance(result[0], dict):
		is_dict_obj = True

	convertible_columns = {}
	for idx, d in enumerate(columns):
		key = d.get("fieldname") if is_dict_obj else idx
		if d.get("convertible"):
			convertible_columns.setdefault(key, d.get("convertible"))

			# Add new column to show qty/rate as per the selected UOM
			columns.insert(idx+1, {
				'label': "{0} (per {1})".format(d.get("label"), include_uom),
				'fieldname': "{0}_{1}".format(d.get("fieldname"), frappe.scrub(include_uom)),
				'fieldtype': 'Currency' if d.get("convertible") == 'rate' else 'Float'
			})

	update_dict_values = []
	for row_idx, row in enumerate(result):
		data = row.items() if is_dict_obj else enumerate(row)
		for key, value in data:
			if key not in convertible_columns:
				continue
			# If no conversion factor for the UOM, defaults to 1
			if not conversion_factors[row_idx]:
				conversion_factors[row_idx] = 1

			if convertible_columns.get(key) == 'rate':
				new_value = flt(value) * conversion_factors[row_idx]
			else:
				new_value = flt(value) / conversion_factors[row_idx]

			if not is_dict_obj:
				row.insert(key+1, new_value)
			else:
				new_key = "{0}_{1}".format(key, frappe.scrub(include_uom))
				update_dict_values.append([row, new_key, new_value])

	for data in update_dict_values:
		row, key, value = data
		row[key] = value

def get_available_serial_nos(args):
	return frappe.db.sql(""" SELECT name from `tabSerial No`
		WHERE item_code = %(item_code)s and warehouse = %(warehouse)s
		 and timestamp(purchase_date, purchase_time) <= timestamp(%(posting_date)s, %(posting_time)s)
	""", args, as_dict=1)

def add_additional_uom_columns(columns, result, include_uom, conversion_factors):
	if not include_uom or not conversion_factors:
		return

	convertible_column_map = {}
	for col_idx in list(reversed(range(0, len(columns)))):
		col = columns[col_idx]
		if isinstance(col, dict) and col.get('convertible') in ['rate', 'qty']:
			next_col = col_idx + 1
			columns.insert(next_col, col.copy())
			columns[next_col]['fieldname'] += '_alt'
			convertible_column_map[col.get('fieldname')] = frappe._dict({
				'converted_col': columns[next_col]['fieldname'],
				'for_type': col.get('convertible')
			})
			if col.get('convertible') == 'rate':
				columns[next_col]['label'] += ' (per {})'.format(include_uom)
			else:
				columns[next_col]['label'] += ' ({})'.format(include_uom)

	for row_idx, row in enumerate(result):
		for convertible_col, data in convertible_column_map.items():
			conversion_factor = conversion_factors[row.get('item_code')] or 1
			for_type = data.for_type
			value_before_conversion = row.get(convertible_col)
			if for_type == 'rate':
				row[data.converted_col] = flt(value_before_conversion) * conversion_factor
			else:
				row[data.converted_col] = flt(value_before_conversion) / conversion_factor

		result[row_idx] = row

def get_incoming_outgoing_rate_for_cancel(item_code, voucher_type, voucher_no, voucher_detail_no):
	outgoing_rate = frappe.db.sql("""SELECT abs(stock_value_difference / actual_qty)
		FROM `tabStock Ledger Entry`
		WHERE voucher_type = %s and voucher_no = %s
			and item_code = %s and voucher_detail_no = %s
			ORDER BY CREATION DESC limit 1""",
		(voucher_type, voucher_no, item_code, voucher_detail_no))

	outgoing_rate = outgoing_rate[0][0] if outgoing_rate else 0.0

	return outgoing_rate

def is_reposting_item_valuation_in_progress():
	reposting_in_progress = frappe.db.exists("Repost Item Valuation",
		{'docstatus': 1, 'status': ['in', ['Queued','In Progress']]})
	if reposting_in_progress:
		frappe.msgprint(_("Item valuation reposting in progress. Report might show incorrect item valuation."), alert=1)
