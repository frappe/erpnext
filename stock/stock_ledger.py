# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes import msgprint
from webnotes.utils import cint, flt, cstr, now
from stock.utils import get_valuation_method
import json

# future reposting
class NegativeStockError(webnotes.ValidationError): pass

_exceptions = webnotes.local('stockledger_exceptions')
# _exceptions = []

def make_sl_entries(sl_entries, is_amended=None):
	if sl_entries:
		from stock.utils import update_bin
	
		cancel = True if sl_entries[0].get("is_cancelled") == "Yes" else False
		if cancel:
			set_as_cancel(sl_entries[0].get('voucher_no'), sl_entries[0].get('voucher_type'))
	
		for sle in sl_entries:
			sle_id = None
			if sle.get('is_cancelled') == 'Yes':
				sle['actual_qty'] = -flt(sle['actual_qty'])
		
			if sle.get("actual_qty"):
				sle_id = make_entry(sle)
			
			args = sle.copy()
			args.update({
				"sle_id": sle_id,
				"is_amended": is_amended
			})
			update_bin(args)
		
		if cancel:
			delete_cancelled_entry(sl_entries[0].get('voucher_type'), 
				sl_entries[0].get('voucher_no'))
			
def set_as_cancel(voucher_type, voucher_no):
	webnotes.conn.sql("""update `tabStock Ledger Entry` set is_cancelled='Yes',
		modified=%s, modified_by=%s
		where voucher_no=%s and voucher_type=%s""", 
		(now(), webnotes.session.user, voucher_type, voucher_no))
		
def make_entry(args):
	args.update({"doctype": "Stock Ledger Entry"})
	sle = webnotes.bean([args])
	sle.ignore_permissions = 1
	sle.insert()
	sle.submit()
	return sle.doc.name
	
def delete_cancelled_entry(voucher_type, voucher_no):
	webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
		where voucher_type=%s and voucher_no=%s""", (voucher_type, voucher_no))

def update_entries_after(args, verbose=1):
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
		webnotes.local.stockledger_exceptions = []
	
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
		if sle.serial_no or not cint(webnotes.conn.get_default("allow_negative_stock")):
			# validate negative stock for serialized items, fifo valuation 
			# or when negative stock is not allowed for moving average
			if not validate_negative_stock(qty_after_transaction, sle):
				qty_after_transaction += flt(sle.actual_qty)
				continue

		if sle.serial_no:
			valuation_rate = get_serialized_values(qty_after_transaction, sle, valuation_rate)
		elif valuation_method == "Moving Average":
			valuation_rate = get_moving_average_values(qty_after_transaction, sle, valuation_rate)
		else:
			valuation_rate = get_fifo_values(qty_after_transaction, sle, stock_queue)
				
		qty_after_transaction += flt(sle.actual_qty)
		
		# get stock value
		if sle.serial_no:
			stock_value = qty_after_transaction * valuation_rate
		elif valuation_method == "Moving Average":
			stock_value = (qty_after_transaction > 0) and \
				(qty_after_transaction * valuation_rate) or 0
		else:
			stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))
			
		stock_value_difference = stock_value - prev_stock_value
		prev_stock_value = stock_value
			
		# update current sle
		webnotes.conn.sql("""update `tabStock Ledger Entry`
			set qty_after_transaction=%s, valuation_rate=%s, stock_queue=%s,
			stock_value=%s, stock_value_difference=%s where name=%s""", 
			(qty_after_transaction, valuation_rate,
			json.dumps(stock_queue), stock_value, stock_value_difference, sle.name))
	
	if _exceptions:
		_raise_exceptions(args, verbose)
	
	# update bin
	if not webnotes.conn.exists({"doctype": "Bin", "item_code": args["item_code"], 
			"warehouse": args["warehouse"]}):
		bin_wrapper = webnotes.bean([{
			"doctype": "Bin",
			"item_code": args["item_code"],
			"warehouse": args["warehouse"],
		}])
		bin_wrapper.ignore_permissions = 1
		bin_wrapper.insert()
	
	webnotes.conn.sql("""update `tabBin` set valuation_rate=%s, actual_qty=%s,
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
	
	return sle and sle[0] or webnotes._dict()
	
def get_sle_after_datetime(args, for_update=False):
	"""get Stock Ledger Entries after a particular datetime, for reposting"""
	# NOTE: using for update of 
	return get_stock_ledger_entries(args,
		["timestamp(posting_date, posting_time) > timestamp(%(posting_date)s, %(posting_time)s)"],
		"asc", for_update=for_update)
				
def get_stock_ledger_entries(args, conditions=None, order="desc", limit=None, for_update=False):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	if not args.get("posting_date"):
		args["posting_date"] = "1900-01-01"
	if not args.get("posting_time"):
		args["posting_time"] = "00:00"
	
	return webnotes.conn.sql("""select * from `tabStock Ledger Entry`
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
		webnotes.local.stockledger_exceptions = []
	
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
		incoming_rate = flt(webnotes.conn.sql("""select avg(ifnull(purchase_rate, 0))
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
	
def get_moving_average_values(qty_after_transaction, sle, valuation_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)	
	
	if not incoming_rate:
		# In case of delivery/stock issue in_rate = 0 or wrong incoming rate
		incoming_rate = valuation_rate
	
	elif qty_after_transaction < 0:
		# if negative stock, take current valuation rate as incoming rate
		valuation_rate = incoming_rate
		
	new_stock_qty = qty_after_transaction + actual_qty
	new_stock_value = qty_after_transaction * valuation_rate + actual_qty * incoming_rate
	
	if new_stock_qty > 0 and new_stock_value > 0:
		valuation_rate = new_stock_value / flt(new_stock_qty)
	elif new_stock_qty <= 0:
		valuation_rate = 0.0
	
	# NOTE: val_rate is same as previous entry if new stock value is negative
	
	return valuation_rate
	
def get_fifo_values(qty_after_transaction, sle, stock_queue):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)
	if not stock_queue:
		stock_queue.append([0, 0])

	if actual_qty > 0:
		if stock_queue[-1][0] > 0:
			stock_queue.append([actual_qty, incoming_rate])
		else:
			qty = stock_queue[-1][0] + actual_qty
			stock_queue[-1] = [qty, qty > 0 and incoming_rate or 0]
	else:
		incoming_cost = 0
		qty_to_pop = abs(actual_qty)
		while qty_to_pop:
			if not stock_queue:
				stock_queue.append([0, 0])
			
			batch = stock_queue[0]
			
			if 0 < batch[0] <= qty_to_pop:
				# if batch qty > 0
				# not enough or exactly same qty in current batch, clear batch
				incoming_cost += flt(batch[0]) * flt(batch[1])
				qty_to_pop -= batch[0]
				stock_queue.pop(0)
			else:
				# all from current batch
				incoming_cost += flt(qty_to_pop) * flt(batch[1])
				batch[0] -= qty_to_pop
				qty_to_pop = 0
		
	stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))
	stock_qty = sum((flt(batch[0]) for batch in stock_queue))

	valuation_rate = stock_qty and (stock_value / flt(stock_qty)) or 0

	return valuation_rate

def _raise_exceptions(args, verbose=1):
	deficiency = min(e["diff"] for e in _exceptions)
	msg = """Negative stock error: 
		Cannot complete this transaction because stock will start
		becoming negative (%s) for Item <b>%s</b> in Warehouse 
		<b>%s</b> on <b>%s %s</b> in Transaction %s %s.
		Total Quantity Deficiency: <b>%s</b>""" % \
		(_exceptions[0]["diff"], args.get("item_code"), args.get("warehouse"),
		_exceptions[0]["posting_date"], _exceptions[0]["posting_time"],
		_exceptions[0]["voucher_type"], _exceptions[0]["voucher_no"],
		abs(deficiency))
	if verbose:
		msgprint(msg, raise_exception=NegativeStockError)
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
