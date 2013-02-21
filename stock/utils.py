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
import json
from webnotes.utils import flt, cstr

def validate_end_of_life(item_code, end_of_life=None, verbose=1):
	if not end_of_life:
		end_of_life = webnotes.conn.get_value("Item", item_code, "end_of_life")
	
	from webnotes.utils import getdate, now_datetime, formatdate
	if end_of_life and getdate(end_of_life) > now_datetime().date():
		msg = (_("Item") + " %(item_code)s: " + _("reached its end of life on") + \
			" %(date)s. " + _("Please check") + ": %(end_of_life_label)s " + \
			"in Item master") % {
				"item_code": item_code,
				"date": formatdate(end_of_life),
				"end_of_life_label": webnotes.get_doctype("Item").get_label("end_of_life")
			}
		
		_msgprint(msg, verbose)
			
def validate_is_stock_item(item_code, is_stock_item=None, verbose=1):
	if not is_stock_item:
		is_stock_item = webnotes.conn.get_value("Item", item_code, "is_stock_item")
		
	if is_stock_item != "Yes":
		msg = (_("Item") + " %(item_code)s: " + _("is not a Stock Item")) % {
			"item_code": item_code,
		}
		
		_msgprint(msg, verbose)
		
def validate_cancelled_item(item_code, docstatus=None, verbose=1):
	if docstatus is None:
		docstatus = webnotes.conn.get_value("Item", item_code, "docstatus")
	
	if docstatus == 2:
		msg = (_("Item") + " %(item_code)s: " + _("is a cancelled Item")) % {
			"item_code": item_code,
		}
		
		_msgprint(msg, verbose)

def _msgprint(msg, verbose):
	if verbose:
		msgprint(msg, raise_exception=True)
	else:
		raise webnotes.ValidationError, msg

def get_incoming_rate(args):
	"""Get Incoming Rate based on valuation method"""
	from stock.stock_ledger import get_previous_sle
		
	in_rate = 0
	if args.get("serial_no"):
		in_rate = get_avg_purchase_rate(args.get("serial_no"))
	elif args.get("bom_no"):
		result = webnotes.conn.sql("""select ifnull(total_cost, 0) / ifnull(quantity, 1) 
			from `tabBOM` where name = %s and docstatus=1 and is_active=1""", args.get("bom_no"))
		in_rate = result and flt(result[0][0]) or 0
	else:
		valuation_method = get_valuation_method(args.get("item_code"))
		previous_sle = get_previous_sle(args)
		if valuation_method == 'FIFO':
			if not previous_sle:
				return 0.0
			previous_stock_queue = json.loads(previous_sle.get('stock_queue', '[]'))
			in_rate = previous_stock_queue and \
				get_fifo_rate(previous_stock_queue, args.get("qty") or 0) or 0
		elif valuation_method == 'Moving Average':
			in_rate = previous_sle.get('valuation_rate') or 0
	return in_rate
	
def get_avg_purchase_rate(serial_nos):
	"""get average value of serial numbers"""
	
	serial_nos = get_valid_serial_nos(serial_nos)
	return flt(webnotes.conn.sql("""select avg(ifnull(purchase_rate, 0)) from `tabSerial No` 
		where name in (%s)""" % ", ".join(["%s"] * len(serial_nos)),
		tuple(serial_nos))[0][0])

def get_valuation_method(item_code):
	"""get valuation method from item or default"""
	val_method = webnotes.conn.get_value('Item', item_code, 'valuation_method')
	if not val_method:
		from webnotes.utils import get_defaults
		val_method = get_defaults().get('valuation_method', 'FIFO')
	return val_method
		
def get_fifo_rate(previous_stock_queue, qty):
	"""get FIFO (average) Rate from Queue"""
	if qty >= 0:
		total = sum(f[0] for f in previous_stock_queue)	
		return total and sum(f[0] * f[1] for f in previous_stock_queue) / flt(total) or 0.0
	else:
		outgoing_cost = 0
		qty_to_pop = abs(qty)
		while qty_to_pop and previous_stock_queue:
			batch = previous_stock_queue[0]
			if 0 < batch[0] <= qty_to_pop:
				# if batch qty > 0
				# not enough or exactly same qty in current batch, clear batch
				outgoing_cost += flt(batch[0]) * flt(batch[1])
				qty_to_pop -= batch[0]
				previous_stock_queue.pop(0)
			else:
				# all from current batch
				outgoing_cost += flt(qty_to_pop) * flt(batch[1])
				batch[0] -= qty_to_pop
				qty_to_pop = 0
		# if queue gets blank and qty_to_pop remaining, get average rate of full queue
		return outgoing_cost / abs(qty) - qty_to_pop
	
def get_valid_serial_nos(sr_nos, qty=0, item_code=''):
	"""split serial nos, validate and return list of valid serial nos"""
	# TODO: remove duplicates in client side
	serial_nos = cstr(sr_nos).strip().replace(',', '\n').split('\n')
	
	valid_serial_nos = []
	for val in serial_nos:
		if val:
			val = val.strip()
			if val in valid_serial_nos:
				msgprint("You have entered duplicate serial no: '%s'" % val, raise_exception=1)
			else:
				valid_serial_nos.append(val)
	
	if qty and len(valid_serial_nos) != abs(qty):
		msgprint("Please enter serial nos for "
			+ cstr(abs(qty)) + " quantity against item code: " + item_code,
			raise_exception=1)
		
	return valid_serial_nos
	
def get_warehouse_list(doctype, txt, searchfield, start, page_len, filters):
	"""used in search queries"""
	wlist = []
	for w in webnotes.conn.sql_list("""select name from tabWarehouse 
		where name like '%%%s%%'""" % txt):
		if webnotes.session.user=="Administrator":
			wlist.append([w])
		else:
			warehouse_users = webnotes.conn.sql_list("""select user from `tabWarehouse User` 
				where parent=%s""", w)
			if not warehouse_users:
				wlist.append([w])
			elif webnotes.session.user in warehouse_users:
				wlist.append([w])
	return wlist
	