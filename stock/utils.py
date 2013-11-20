# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes import msgprint, _
import json
from webnotes.utils import flt, cstr, nowdate, add_days, cint
from webnotes.defaults import get_global_default
from webnotes.utils.email_lib import sendmail

class UserNotAllowedForWarehouse(webnotes.ValidationError): pass
class InvalidWarehouseCompany(webnotes.ValidationError): pass
	
def get_stock_balance_on(warehouse, posting_date=None):
	if not posting_date: posting_date = nowdate()
	
	stock_ledger_entries = webnotes.conn.sql("""
		SELECT 
			item_code, stock_value
		FROM 
			`tabStock Ledger Entry`
		WHERE 
			warehouse=%s AND posting_date <= %s
		ORDER BY timestamp(posting_date, posting_time) DESC, name DESC
	""", (warehouse, posting_date), as_dict=1)
	 
	sle_map = {}
	for sle in stock_ledger_entries:
		sle_map.setdefault(sle.item_code, flt(sle.stock_value))
		
	return sum(sle_map.values())
	
def get_latest_stock_balance():
	bin_map = {}
	for d in webnotes.conn.sql("""SELECT item_code, warehouse, stock_value as stock_value 
		FROM tabBin""", as_dict=1):
			bin_map.setdefault(d.warehouse, {}).setdefault(d.item_code, flt(d.stock_value))
			
	return bin_map
	
def get_bin(item_code, warehouse):
	bin = webnotes.conn.get_value("Bin", {"item_code": item_code, "warehouse": warehouse})
	if not bin:
		bin_wrapper = webnotes.bean([{
			"doctype": "Bin",
			"item_code": item_code,
			"warehouse": warehouse,
		}])
		bin_wrapper.ignore_permissions = 1
		bin_wrapper.insert()
		bin_obj = bin_wrapper.make_controller()
	else:
		from webnotes.model.code import get_obj
		bin_obj = get_obj('Bin', bin)
	return bin_obj

def update_bin(args):
	is_stock_item = webnotes.conn.get_value('Item', args.get("item_code"), 'is_stock_item')
	if is_stock_item == 'Yes':
		bin = get_bin(args.get("item_code"), args.get("warehouse"))
		bin.update_stock(args)
		return bin
	else:
		msgprint("[Stock Update] Ignored %s since it is not a stock item" 
			% args.get("item_code"))

def validate_end_of_life(item_code, end_of_life=None, verbose=1):
	if not end_of_life:
		end_of_life = webnotes.conn.get_value("Item", item_code, "end_of_life")
	
	from webnotes.utils import getdate, now_datetime, formatdate
	if end_of_life and getdate(end_of_life) <= now_datetime().date():
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
			previous_stock_queue = json.loads(previous_sle.get('stock_queue', '[]') or '[]')
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
		val_method = get_global_default('valuation_method') or "FIFO"
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

def validate_warehouse_user(warehouse):
	if webnotes.session.user=="Administrator" or not warehouse:
		return
	warehouse_users = [p[0] for p in webnotes.conn.sql("""select user from `tabWarehouse User`
		where parent=%s""", warehouse)]
				
	if warehouse_users and not (webnotes.session.user in warehouse_users):
		webnotes.throw(_("Not allowed entry in Warehouse") \
			+ ": " + warehouse, UserNotAllowedForWarehouse)
			
def validate_warehouse_company(warehouse, company):
	warehouse_company = webnotes.conn.get_value("Warehouse", warehouse, "company")
	if warehouse_company and warehouse_company != company:
		webnotes.msgprint(_("Warehouse does not belong to company.") + " (" + \
			warehouse + ", " + company +")", raise_exception=InvalidWarehouseCompany)

def get_sales_bom_buying_amount(item_code, warehouse, voucher_type, voucher_no, voucher_detail_no, 
		stock_ledger_entries, item_sales_bom):
	# sales bom item
	buying_amount = 0.0
	for bom_item in item_sales_bom[item_code]:
		if bom_item.get("parent_detail_docname")==voucher_detail_no:
			buying_amount += get_buying_amount(voucher_type, voucher_no, voucher_detail_no, 
				stock_ledger_entries.get((bom_item.item_code, warehouse), []))

	return buying_amount
		
def get_buying_amount(voucher_type, voucher_no, item_row, stock_ledger_entries):
	# IMP NOTE
	# stock_ledger_entries should already be filtered by item_code and warehouse and 
	# sorted by posting_date desc, posting_time desc
	for i, sle in enumerate(stock_ledger_entries):
		if sle.voucher_type == voucher_type and sle.voucher_no == voucher_no and \
			sle.voucher_detail_no == item_row:
				previous_stock_value = len(stock_ledger_entries) > i+1 and \
					flt(stock_ledger_entries[i+1].stock_value) or 0.0
				buying_amount =  previous_stock_value - flt(sle.stock_value)						
				
				return buying_amount
	return 0.0
	

def reorder_item():
	""" Reorder item if stock reaches reorder level"""
	if getattr(webnotes.local, "auto_indent", None) is None:
		webnotes.local.auto_indent = cint(webnotes.conn.get_value('Stock Settings', None, 'auto_indent'))
	
	if webnotes.local.auto_indent:
		material_requests = {}
		bin_list = webnotes.conn.sql("""select item_code, warehouse, projected_qty
			from tabBin where ifnull(item_code, '') != '' and ifnull(warehouse, '') != ''
			and exists (select name from `tabItem` 
				where `tabItem`.name = `tabBin`.item_code and 
				is_stock_item='Yes' and (is_purchase_item='Yes' or is_sub_contracted_item='Yes') and
				(ifnull(end_of_life, '')='' or end_of_life > now()))""", as_dict=True)
		for bin in bin_list:
			#check if re-order is required
			item_reorder = webnotes.conn.get("Item Reorder", 
				{"parent": bin.item_code, "warehouse": bin.warehouse})
			if item_reorder:
				reorder_level = item_reorder.warehouse_reorder_level
				reorder_qty = item_reorder.warehouse_reorder_qty
				material_request_type = item_reorder.material_request_type or "Purchase"
			else:
				reorder_level, reorder_qty = webnotes.conn.get_value("Item", bin.item_code,
					["re_order_level", "re_order_qty"])
				material_request_type = "Purchase"
		
			if flt(reorder_level) and flt(bin.projected_qty) < flt(reorder_level):
				if flt(reorder_level) - flt(bin.projected_qty) > flt(reorder_qty):
					reorder_qty = flt(reorder_level) - flt(bin.projected_qty)
					
				company = webnotes.conn.get_value("Warehouse", bin.warehouse, "company") or \
					webnotes.defaults.get_defaults()["company"] or \
					webnotes.conn.sql("""select name from tabCompany limit 1""")[0][0]
					
				material_requests.setdefault(material_request_type, webnotes._dict()).setdefault(
					company, []).append(webnotes._dict({
						"item_code": bin.item_code,
						"warehouse": bin.warehouse,
						"reorder_qty": reorder_qty
					})
				)
		
		create_material_request(material_requests)

def create_material_request(material_requests):
	"""	Create indent on reaching reorder level	"""
	mr_list = []
	defaults = webnotes.defaults.get_defaults()
	exceptions_list = []
	for request_type in material_requests:
		for company in material_requests[request_type]:
			try:
				items = material_requests[request_type][company]
				if not items:
					continue
					
				mr = [{
					"doctype": "Material Request",
					"company": company,
					"fiscal_year": defaults.fiscal_year,
					"transaction_date": nowdate(),
					"material_request_type": request_type
				}]
			
				for d in items:
					item = webnotes.doc("Item", d.item_code)
					mr.append({
						"doctype": "Material Request Item",
						"parenttype": "Material Request",
						"parentfield": "indent_details",
						"item_code": d.item_code,
						"schedule_date": add_days(nowdate(),cint(item.lead_time_days)),
						"uom":	item.stock_uom,
						"warehouse": d.warehouse,
						"item_name": item.item_name,
						"description": item.description,
						"item_group": item.item_group,
						"qty": d.reorder_qty,
						"brand": item.brand,
					})
			
				mr_bean = webnotes.bean(mr)
				mr_bean.insert()
				mr_bean.submit()
				mr_list.append(mr_bean)

			except:
				if webnotes.local.message_log:
					exceptions_list.append([] + webnotes.local.message_log)
					webnotes.local.message_log = []
				else:
					exceptions_list.append(webnotes.getTraceback())

	if mr_list:
		if getattr(webnotes.local, "reorder_email_notify", None) is None:
			webnotes.local.reorder_email_notify = cint(webnotes.conn.get_value('Stock Settings', None, 
				'reorder_email_notify'))
			
		if(webnotes.local.reorder_email_notify):
			send_email_notification(mr_list)

	if exceptions_list:
		notify_errors(exceptions_list)
		
def send_email_notification(mr_list):
	""" Notify user about auto creation of indent"""
	
	email_list = webnotes.conn.sql_list("""select distinct r.parent 
		from tabUserRole r, tabProfile p
		where p.name = r.parent and p.enabled = 1 and p.docstatus < 2
		and r.role in ('Purchase Manager','Material Manager') 
		and p.name not in ('Administrator', 'All', 'Guest')""")
	
	msg="""<h3>Following Material Requests has been raised automatically \
		based on item reorder level:</h3>"""
	for mr in mr_list:
		msg += "<p><b><u>" + mr.doc.name + """</u></b></p><table class='table table-bordered'><tr>
			<th>Item Code</th><th>Warehouse</th><th>Qty</th><th>UOM</th></tr>"""
		for item in mr.doclist.get({"parentfield": "indent_details"}):
			msg += "<tr><td>" + item.item_code + "</td><td>" + item.warehouse + "</td><td>" + \
				cstr(item.qty) + "</td><td>" + cstr(item.uom) + "</td></tr>"
		msg += "</table>"
	sendmail(email_list, subject='Auto Material Request Generation Notification', msg = msg)
	
def notify_errors(exceptions_list):
	subject = "[Important] [ERPNext] Error(s) while creating Material Requests based on Re-order Levels"
	msg = """Dear System Manager,

		An error occured for certain Items while creating Material Requests based on Re-order level.
		
		Please rectify these issues:
		---

		%s

		---
		Regards,
		Administrator""" % ("\n\n".join(["\n".join(msg) for msg in exceptions_list]),)

	from webnotes.profile import get_system_managers
	sendmail(get_system_managers(), subject=subject, msg=msg)
