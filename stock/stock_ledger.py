# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import webnotes
from webnotes import msgprint, _
from webnotes.utils import cint
from stock.utils import _msgprint, get_valuation_method

# future reposting

_exceptions = []
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
	previous_sle = get_sle_before_datetime(args)
	
	qty_after_transaction = flt(previous_sle.get("qty_after_transaction"))
	valuation_rate = flt(previous_sle.get("valuation_rate"))
	stock_queue = json.loads(previous_sle.get("stock_queue") or "[]")

	entries_to_fix = get_sle_after_datetime(previous_sle or \
		{"item_code": args["item_code"], "warehouse": args["warehouse"]})
		
	valuation_method = get_valuation_method(args["item_code"])
	
	for sle in entries_to_fix:
		if sle.serial_nos or valuation_method == "FIFO" or \
				not cint(webnotes.conn.get_default("allow_negative_stock")):
			# validate negative stock for serialized items, fifo valuation 
			# or when negative stock is not allowed for moving average
			if not validate_negative_stock(qty_after_transaction, sle):
				qty_after_transaction += flt(sle.actual_qty)
				continue

		if sle.serial_nos:
			valuation_rate, incoming_rate = get_serialized_values(qty_after_transaction, sle,
				valuation_rate)
		elif valuation_method == "Moving Average":
			valuation_rate, incoming_rate = get_moving_average_values(qty_after_transaction, sle,
				valuation_rate)
		else:
			valuation_rate, incoming_rate = get_fifo_values(qty_after_transaction, sle,
				stock_queue)
		
		qty_after_transaction += flt(sle.actual_qty)
		
		# get stock value
		if serial_nos:
			stock_value = qty_after_transaction * valuation_rate
		elif valuation_method == "Moving Average":
			stock_value = (qty_after_transaction > 0) and \
				(qty_after_transaction * valuation_rate) or 0
		else:
			stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))

		# update current sle
		webnotes.conn.sql("""update `tabStock Ledger Entry`
			set qty_after_transaction=%s, valuation_rate=%s, stock_queue=%s, stock_value=%s,
			incoming_rate = %s where name=%s""", (qty_after_transaction, valuation_rate,
			json.dumps(stock_queue), stock_value, incoming_rate, sle.name))
		
	if _exceptions:
		_raise_exceptions(args)
	
	# update bin
	webnotes.conn.sql("""update `tabBin` set valuation_rate=%s, actual_qty=%s, stock_value=%s, 
		projected_qty = (actual_qty + indented_qty + ordered_qty + planned_qty - reserved_qty)
		where item_code=%s and warehouse=%s""", (valuation_rate, qty_after_transaction,
		stock_value, args["item_code"], args["warehouse"]))
		
def get_sle_before_datetime(args):
	"""
		get previous stock ledger entry before current time-bucket

		Details:
		get the last sle before the current time-bucket, so that all values
		are reposted from the current time-bucket onwards.
		this is necessary because at the time of cancellation, there may be
		entries between the cancelled entries in the same time-bucket
	"""
	sle = get_stock_ledger_entries(args,
		["timestamp(posting_date, posting_time) < timestamp(%%(posting_date)s, %%(posting_time)s)"],
		"limit 1")
	
	return sle and sle[0] or webnotes._dict()
	
def get_sle_after_datetime(args):
	"""get Stock Ledger Entries after a particular datetime, for reposting"""
	return get_stock_ledger_entries(args,
		["timestamp(posting_date, posting_time) > timestamp(%%(posting_date)s, %%(posting_time)s)"])
				
def get_stock_ledger_entries(args, conditions=None, limit=None):
	"""get stock ledger entries filtered by specific posting datetime conditions"""
	if not args.get("posting_date"):
		args["posting_date"] = "1900-01-01"
	if not args.get("posting_time"):
		args["posting_time"] = "12:00"
	
	return webnotes.conn.sql("""select * from `tabStock Ledger Entry`
		where item_code = %%(item_code)s
		and warehouse = %%(warehouse)s
		and ifnull(is_cancelled, 'No') = 'No'
		%(conditions)s
		order by timestamp(posting_date, posting_time) desc, name desc
		%(limit)s""" % {
			"conditions": conditions and ("and " + " and ".join(conditions)) or "",
			"limit": limit or ""
		}, args, as_dict=1)
		
def validate_negative_stock(qty_after_transaction, sle):
	"""
		validate negative stock for entries current datetime onwards
		will not consider cancelled entries
	"""
	diff = qty_after_transaction + flt(sle.actual_qty)
	
	if diff < 0 and abs(diff) > 0.0001:
		# negative stock!
		global _exceptions
		exc = sle.copy().update({"diff": diff})
		_exceptions.append(exc)
		return False
	else:
		return True
	
def get_serialized_values(qty_after_transaction, sle, valuation_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)
	serial_nos = cstr(sle.serial_nos).split("\n")
	
	if incoming_rate < 0:
		# wrong incoming rate
		incoming_rate = valuation_rate
	elif incoming_rate == 0 or flt(sle.actual_qty) < 0:
		# In case of delivery/stock issue, get average purchase rate
		# of serial nos of current entry
		incoming_rate = flt(webnotes.conn.sql("""select avg(ifnull(purchase_rate, 0))
			from `tabSerial No` where name in (%s)""" % (", ".join(["%s"]*len(serial_nos))),
			tuple(serial_nos))[0][0])
	
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
		
	return valuation_rate, incoming_rate
	
def get_moving_average_values(qty_after_transaction, sle, valuation_rate):
	incoming_rate = flt(sle.incoming_rate)
	actual_qty = flt(sle.actual_qty)
	
	if not incoming_rate or actual_qty < 0:
		# In case of delivery/stock issue in_rate = 0 or wrong incoming rate
		incoming_rate = valuation_rate
	
	# val_rate is same as previous entry if :
	# 1. actual qty is negative(delivery note / stock entry)
	# 2. cancelled entry
	# 3. val_rate is negative
	# Otherwise it will be calculated as per moving average
	new_stock_qty = qty_after_transaction + actual_qty
	new_stock_value = qty_after_transaction * valuation_rate + actual_qty * incoming_rate
	if actual_qty > 0 and new_stock_qty > 0 and new_stock_value > 0:
		valuation_rate = new_stock_value / flt(new_stock_qty)
	elif new_stock_qty <= 0:
		valuation_rate = 0.0
		
	return valuation_rate, incoming_rate
	
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
		
		incoming_rate = incoming_cost / flt(abs(actual_qty))

	stock_value = sum((flt(batch[0]) * flt(batch[1]) for batch in stock_queue))
	stock_qty = sum((flt(batch[0]) for batch in stock_queue))

	valuation_rate = stock_qty and (stock_value / flt(stock_qty)) or 0
	
	return valuation_rate, incoming_rate

def _raise_exceptions(args):
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
		msgprint(msg, raise_exception=1)
	else:
		raise webnotes.ValidationError, msg