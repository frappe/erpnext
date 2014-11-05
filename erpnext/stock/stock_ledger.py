# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import cint, flt, cstr, now
from erpnext.stock.utils import get_valuation_method
import json

# future reposting
class NegativeStockError(frappe.ValidationError): pass

_exceptions = frappe.local('stockledger_exceptions')
# _exceptions = []

def make_sl_entries(sl_entries, is_amended=None):
	if sl_entries:
		from erpnext.stock.utils import update_bin

		cancel = True if sl_entries[0].get("is_cancelled") == "Yes" else False
		if cancel:
			set_as_cancel(sl_entries[0].get('voucher_no'), sl_entries[0].get('voucher_type'))

		for sle in sl_entries:
			sle_id = None
			if sle.get('is_cancelled') == 'Yes':
				sle['actual_qty'] = -flt(sle['actual_qty'])

			if sle.get("actual_qty") or sle.get("voucher_type")=="Stock Reconciliation":
				sle_id = make_entry(sle)

			args = sle.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended
			})
			update_bin(args)

		if cancel:
			delete_cancelled_entry(sl_entries[0].get('voucher_type'), sl_entries[0].get('voucher_no'))

def set_as_cancel(voucher_type, voucher_no):
	frappe.db.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
		modified=%s, modified_by=%s
		where voucher_no=%s and voucher_type=%s""",
		(now(), frappe.session.user, voucher_type, voucher_no))

def make_entry(args):
	args.update({"doctype": "Stock Ledger Entry"})
	sle = frappe.get_doc(args)
	sle.ignore_permissions = 1
	sle.insert()
	sle.submit()
	return sle.name

def delete_cancelled_entry(voucher_type, voucher_no):
	frappe.db.sql("""delete from `tabStock Ledger Entry`
		where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

def update_entries_after(args, allow_zero_rate=False, verbose=1):
	"""
		update valution rate and qty after transaction
		from the current time-bucket onwards

		args = {
			"item_code": "ABC",
			"warehouse": "XYZ",
			"posting_date": "2012-12-12",
			"posting_time": "12:00"
		}
	"""
	if not _exceptions:
		frappe.local.stockledger_exceptions = []

	previous_sle = get_sle_before_datetime(args)

	qty_after_transaction = flt(previous_sle.get("qty_after_transaction"))
	valuation_rate = flt(previous_sle.get("valuation_rate"))
	stock_queue = json.loads(previous_sle.get("stock_queue") or "[]")
	stock_value = flt(previous_sle.get("stock_value"))
	prev_stock_value = flt(previous_sle.get("stock_value"))

	entries_to_fix = get_sle_after_datetime(previous_sle or \
		{"item_code": args["item_code"], "warehouse": args["warehouse"]}, for_update=True)
	valuation_method = get_valuation_method(args["item_code"])
	stock_value_difference = 0.0

	for sle in entries_to_fix:
		if sle.serial_no or not cint(frappe.db.get_default("allow_negative_stock")):
			# validate negative stock for serialized items, fifo valuation
			# or when negative stock is not allowed for moving average
			if not validate_negative_stock(qty_after_transaction, sle):
				qty_after_transaction += flt(sle.actual_qty)
				continue


		if sle.serial_no:
			valuation_rate = get_serialized_values(qty_after_transaction, sle, valuation_rate)
			qty_after_transaction += flt(sle.actual_qty)

		else:
			if sle.voucher_type=="Stock Reconciliation":
				valuation_rate = sle.valuation_rate
				qty_after_transaction = sle.qty_after_transaction
				stock_queue = [[qty_after_transaction, valuation_rate]]
			else:
				if valuation_method == "Moving Average":
					valuation_rate = get_moving_average_values(qty_after_transaction, sle, valuation_rate, allow_zero_rate)
				else:
					valuation_rate = get_fifo_values(qty_after_transaction, sle, stock_queue, allow_zero_rate)


				qty_after_transaction += flt(sle.actual_qty)

		# get stock value
		if sle.serial_no:
			stock_value = qty_after_transaction * valuation_rate
		elif valuation_method == "Moving Average":
			stock_value = qty_after_transaction * valuation_rate
		else:
			stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))

		# rounding as per precision
		from frappe.model.meta import get_field_precision
		meta = frappe.get_meta("Stock Ledger Entry")

		stock_value = flt(stock_value, get_field_precision(meta.get_field("stock_value"),
			frappe._dict({"fields": sle})))

		stock_value_difference = stock_value - prev_stock_value
		prev_stock_value = stock_value

		# update current sle
		frappe.db.sql("""update `tabStock Ledger Entry`
			set qty_after_transaction=%s, valuation_rate=%s, stock_queue=%s,
			stock_value=%s, stock_value_difference=%s where name=%s""",
			(qty_after_transaction, valuation_rate,
			json.dumps(stock_queue), stock_value, stock_value_difference, sle.name))

	if _exceptions:
		_raise_exceptions(args, verbose)

	# update bin
	if not frappe.db.exists({"doctype": "Bin", "item_code": args["item_code"],
			"warehouse": args["warehouse"]}):
		bin_wrapper = frappe.get_doc({
			"doctype": "Bin",
			"item_code": args["item_code"],
			"warehouse": args["warehouse"],
		})
		bin_wrapper.ignore_permissions = 1
		bin_wrapper.insert()

	frappe.db.sql("""update `tabBin` set valuation_rate=%s, actual_qty=%s,
		stock_value=%s,
		projected_qty = (actual_qty + indented_qty + ordered_qty + planned_qty - reserved_qty)
		where item_code=%s and warehouse=%s""", (valuation_rate, qty_after_transaction,
		stock_value, args["item_code"], args["warehouse"]))

def get_sle_before_datetime(args, for_update=False):
	"""
		get previous stock ledger entry before current time-bucket

		Details:
		get the last sle before the current time-bucket, so that all values
		are reposted from the current time-bucket onwards.
		this is necessary because at the time of cancellation, there may be
		entries between the cancelled entries in the same time-bucket
	"""
	sle = get_stock_ledger_entries(args,
		["timestamp(posting_date, posting_time) < timestamp(%(posting_date)s, %(posting_time)s)"],
		"desc", "limit 1", for_update=for_update)

	return sle and sle[0] or frappe._dict()

def get_sle_after_datetime(args, for_update=False):
	"""get Stock Ledger Entries after a particular datetime, for reposting"""
	# NOTE: using for update of
	conditions = ["timestamp(posting_date, posting_time) > timestamp(%(posting_date)s, %(posting_time)s)"]

	# Excluding name: Workaround for MariaDB timestamp() floating microsecond issue
	if args.get("name"):
		conditions.append("name!=%(name)s")

	return get_stock_ledger_entries(args, conditions, "asc", for_update=for_update)

def get_stock_ledger_entries(args, conditions=None, order="desc", limit=None, for_update=False):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	if not args.get("posting_date"):
		args["posting_date"] = "1900-01-01"
	if not args.get("posting_time"):
		args["posting_time"] = "00:00"

	return frappe.db.sql("""select *, timestamp(posting_date, posting_time) as "timestamp" from `tabStock Ledger Entry`
		where item_code = %%(item_code)s
		and warehouse = %%(warehouse)s
		and ifnull(is_cancelled, 'No')='No'
		%(conditions)s
		order by timestamp(posting_date, posting_time) %(order)s, name %(order)s
		%(limit)s %(for_update)s""" % {
			"conditions": conditions and ("and " + " and ".join(conditions)) or "",
			"limit": limit or "",
			"for_update": for_update and "for update" or "",
			"order": order
		}, args, as_dict=1)

def validate_negative_stock(qty_after_transaction, sle):
	"""
		validate negative stock for entries current datetime onwards
		will not consider cancelled entries
	"""
	diff = qty_after_transaction + flt(sle.actual_qty)

	if not _exceptions:
		frappe.local.stockledger_exceptions = []

	if diff < 0 and abs(diff) > 0.0001:
		# negative stock!
		exc = sle.copy().update({"diff": diff})
		_exceptions.append(exc)
		return False
	else:
		return True

def get_serialized_values(qty_after_transaction, sle, valuation_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)
	serial_no = cstr(sle.serial_no).split("\n")

	if incoming_rate < 0:
		# wrong incoming rate
		incoming_rate = valuation_rate
	elif incoming_rate == 0 or flt(sle.actual_qty) < 0:
		# In case of delivery/stock issue, get average purchase rate
		# of serial nos of current entry
		incoming_rate = flt(frappe.db.sql("""select avg(ifnull(purchase_rate, 0))
			from `tabSerial No` where name in (%s)""" % (", ".join(["%s"]*len(serial_no))),
			tuple(serial_no))[0][0])

	if incoming_rate and not valuation_rate:
		valuation_rate = incoming_rate
	else:
		new_stock_qty = qty_after_transaction + actual_qty
		if new_stock_qty > 0:
			new_stock_value = qty_after_transaction * valuation_rate + actual_qty * incoming_rate
			if new_stock_value > 0:
				# calculate new valuation rate only if stock value is positive
				# else it remains the same as that of previous entry
				valuation_rate = new_stock_value / new_stock_qty

	return valuation_rate

def get_moving_average_values(qty_after_transaction, sle, valuation_rate, allow_zero_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)

	if flt(sle.actual_qty) > 0:
		if qty_after_transaction < 0 and not valuation_rate:
			# if negative stock, take current valuation rate as incoming rate
			valuation_rate = incoming_rate

		new_stock_qty = abs(qty_after_transaction) + actual_qty
		new_stock_value = (abs(qty_after_transaction) * valuation_rate) + (actual_qty * incoming_rate)

		if new_stock_qty:
			valuation_rate = new_stock_value / flt(new_stock_qty)
	elif not valuation_rate and qty_after_transaction <= 0:
		valuation_rate = get_valuation_rate(sle.item_code, sle.warehouse, allow_zero_rate)

	return abs(flt(valuation_rate))

def get_fifo_values(qty_after_transaction, sle, stock_queue, allow_zero_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)

	if actual_qty > 0:
		if not stock_queue:
			stock_queue.append([0, 0])

		if stock_queue[-1][0] > 0:
			stock_queue.append([actual_qty, incoming_rate])
		else:
			qty = stock_queue[-1][0] + actual_qty
			if qty == 0:
				stock_queue.pop(-1)
			else:
				stock_queue[-1] = [qty, incoming_rate]
	else:
		qty_to_pop = abs(actual_qty)
		while qty_to_pop:
			if not stock_queue:
				stock_queue.append([0, get_valuation_rate(sle.item_code, sle.warehouse, allow_zero_rate)
					if qty_after_transaction <= 0 else 0])

			batch = stock_queue[0]

			if qty_to_pop >= batch[0]:
				# consume current batch
				qty_to_pop = qty_to_pop - batch[0]
				stock_queue.pop(0)
				if not stock_queue and qty_to_pop:
					# stock finished, qty still remains to be withdrawn
					# negative stock, keep in as a negative batch
					stock_queue.append([-qty_to_pop, batch[1]])
					break

			else:
				# qty found in current batch
				# consume it and exit
				batch[0] = batch[0] - qty_to_pop
				qty_to_pop = 0

	stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))
	stock_qty = sum((flt(batch[0]) for batch in stock_queue))

	valuation_rate = (stock_value / flt(stock_qty)) if stock_qty else 0

	return abs(valuation_rate)

def _raise_exceptions(args, verbose=1):
	deficiency = min(e["diff"] for e in _exceptions)
	msg = _("Negative Stock Error ({6}) for Item {0} in Warehouse {1} on {2} {3} in {4} {5}").format(args["item_code"],
		args.get("warehouse"), _exceptions[0]["posting_date"], _exceptions[0]["posting_time"],
		_(_exceptions[0]["voucher_type"]), _exceptions[0]["voucher_no"], deficiency)
	if verbose:
		frappe.throw(msg, NegativeStockError)
	else:
		raise NegativeStockError, msg

def get_previous_sle(args, for_update=False):
	"""
		get the last sle on or before the current time-bucket,
		to get actual qty before transaction, this function
		is called from various transaction like stock entry, reco etc

		args = {
			"item_code": "ABC",
			"warehouse": "XYZ",
			"posting_date": "2012-12-12",
			"posting_time": "12:00",
			"sle": "name of reference Stock Ledger Entry"
		}
	"""
	if not args.get("sle"): args["sle"] = ""

	sle = get_stock_ledger_entries(args, ["name != %(sle)s",
		"timestamp(posting_date, posting_time) <= timestamp(%(posting_date)s, %(posting_time)s)"],
		"desc", "limit 1", for_update=for_update)
	return sle and sle[0] or {}

def get_valuation_rate(item_code, warehouse, allow_zero_rate=False):
	last_valuation_rate = frappe.db.sql("""select valuation_rate
		from `tabStock Ledger Entry`
		where item_code = %s and warehouse = %s
		and ifnull(valuation_rate, 0) > 0
		order by posting_date desc, posting_time desc, name desc limit 1""", (item_code, warehouse))

	if not last_valuation_rate:
		last_valuation_rate = frappe.db.sql("""select valuation_rate
			from `tabStock Ledger Entry`
			where item_code = %s and ifnull(valuation_rate, 0) > 0
			order by posting_date desc, posting_time desc, name desc limit 1""", item_code)

	valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

	if not valuation_rate:
		valuation_rate = frappe.db.get_value("Item Price", {"item_code": item_code, "buying": 1}, "price_list_rate")

	if not allow_zero_rate and not valuation_rate and cint(frappe.db.get_value("Accounts Settings", None, "auto_accounting_for_stock")):
		frappe.throw(_("Purchase rate for item: {0} not found, which is required to book accounting entry (expense). Please mention item price against a buying price list.").format(item_code))

	return valuation_rate
