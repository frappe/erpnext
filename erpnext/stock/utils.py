# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
import json
from frappe.utils import flt, cstr, nowdate, add_days, cint
from frappe.defaults import get_global_default
from frappe.utils.email_lib import sendmail

class InvalidWarehouseCompany(frappe.ValidationError): pass

def get_stock_balance_on(warehouse, posting_date=None):
	if not posting_date: posting_date = nowdate()

	stock_ledger_entries = frappe.db.sql("""
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
		bin_obj.ignore_permissions = 1
		bin_obj.insert()
	else:
		bin_obj = frappe.get_doc('Bin', bin)
	bin_obj.ignore_permissions = True
	return bin_obj

def update_bin(args):
	is_stock_item = frappe.db.get_value('Item', args.get("item_code"), 'is_stock_item')
	if is_stock_item == 'Yes':
		bin = get_bin(args.get("item_code"), args.get("warehouse"))
		bin.update_stock(args)
		return bin
	else:
		frappe.msgprint(_("Item {0} ignored since it is not a stock item").format(args.get("item_code")))

def get_incoming_rate(args):
	"""Get Incoming Rate based on valuation method"""
	from erpnext.stock.stock_ledger import get_previous_sle

	in_rate = 0
	if args.get("serial_no"):
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
	return flt(frappe.db.sql("""select avg(ifnull(purchase_rate, 0)) from `tabSerial No`
		where name in (%s)""" % ", ".join(["%s"] * len(serial_nos)),
		tuple(serial_nos))[0][0])

def get_valuation_method(item_code):
	"""get valuation method from item or default"""
	val_method = frappe.db.get_value('Item', item_code, 'valuation_method')
	if not val_method:
		val_method = get_global_default('valuation_method') or "FIFO"
	return val_method

def get_fifo_rate(previous_stock_queue, qty):
	"""get FIFO (average) Rate from Queue"""
	if qty >= 0:
		total = sum(f[0] for f in previous_stock_queue)
		return total and sum(f[0] * f[1] for f in previous_stock_queue) / flt(total) or 0.0
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

	# if initial setup not completed, return
	if not frappe.db.sql("select name from `tabFiscal Year` limit 1"):
		return

	if getattr(frappe.local, "auto_indent", None) is None:
		frappe.local.auto_indent = cint(frappe.db.get_value('Stock Settings', None, 'auto_indent'))

	if frappe.local.auto_indent:
		material_requests = {}
		bin_list = frappe.db.sql("""select item_code, warehouse, projected_qty
			from tabBin where ifnull(item_code, '') != '' and ifnull(warehouse, '') != ''
			and exists (select name from `tabItem`
				where `tabItem`.name = `tabBin`.item_code and
				is_stock_item='Yes' and (is_purchase_item='Yes' or is_sub_contracted_item='Yes') and
				(ifnull(end_of_life, '')='' or end_of_life > curdate()))""", as_dict=True)
		for bin in bin_list:
			#check if re-order is required
			item_reorder = frappe.db.get("Item Reorder",
				{"parent": bin.item_code, "warehouse": bin.warehouse})
			if item_reorder:
				reorder_level = item_reorder.warehouse_reorder_level
				reorder_qty = item_reorder.warehouse_reorder_qty
				material_request_type = item_reorder.material_request_type or "Purchase"
			else:
				reorder_level, reorder_qty = frappe.db.get_value("Item", bin.item_code,
					["re_order_level", "re_order_qty"])
				material_request_type = "Purchase"

			if flt(reorder_level) and flt(bin.projected_qty) < flt(reorder_level):
				if flt(reorder_level) - flt(bin.projected_qty) > flt(reorder_qty):
					reorder_qty = flt(reorder_level) - flt(bin.projected_qty)

				company = frappe.db.get_value("Warehouse", bin.warehouse, "company") or \
					frappe.defaults.get_defaults()["company"] or \
					frappe.db.sql("""select name from tabCompany limit 1""")[0][0]

				material_requests.setdefault(material_request_type, frappe._dict()).setdefault(
					company, []).append(frappe._dict({
						"item_code": bin.item_code,
						"warehouse": bin.warehouse,
						"reorder_qty": reorder_qty
					})
				)

		create_material_request(material_requests)

def create_material_request(material_requests):
	"""	Create indent on reaching reorder level	"""
	mr_list = []
	defaults = frappe.defaults.get_defaults()
	exceptions_list = []
	from erpnext.accounts.utils import get_fiscal_year
	current_fiscal_year = get_fiscal_year(nowdate())[0] or defaults.fiscal_year
	for request_type in material_requests:
		for company in material_requests[request_type]:
			try:
				items = material_requests[request_type][company]
				if not items:
					continue

				mr = frappe.new_doc("Material Request")
				mr.update({
					"company": company,
					"fiscal_year": current_fiscal_year,
					"transaction_date": nowdate(),
					"material_request_type": request_type
				})

				for d in items:
					item = frappe.get_doc("Item", d.item_code)
					mr.append("indent_details", {
						"doctype": "Material Request Item",
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

				mr.insert()
				mr.submit()
				mr_list.append(mr)

			except:
				if frappe.local.message_log:
					exceptions_list.append([] + frappe.local.message_log)
					frappe.local.message_log = []
				else:
					exceptions_list.append(frappe.get_traceback())

	if mr_list:
		if getattr(frappe.local, "reorder_email_notify", None) is None:
			frappe.local.reorder_email_notify = cint(frappe.db.get_value('Stock Settings', None,
				'reorder_email_notify'))

		if(frappe.local.reorder_email_notify):
			send_email_notification(mr_list)

	if exceptions_list:
		notify_errors(exceptions_list)

def send_email_notification(mr_list):
	""" Notify user about auto creation of indent"""

	email_list = frappe.db.sql_list("""select distinct r.parent
		from tabUserRole r, tabUser p
		where p.name = r.parent and p.enabled = 1 and p.docstatus < 2
		and r.role in ('Purchase Manager','Material Manager')
		and p.name not in ('Administrator', 'All', 'Guest')""")

	msg="""<h3>Following Material Requests has been raised automatically \
		based on item reorder level:</h3>"""
	for mr in mr_list:
		msg += "<p><b><u>" + mr.name + """</u></b></p><table class='table table-bordered'><tr>
			<th>Item Code</th><th>Warehouse</th><th>Qty</th><th>UOM</th></tr>"""
		for item in mr.get("indent_details"):
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

	from frappe.utils.user import get_system_managers
	sendmail(get_system_managers(), subject=subject, msg=msg)
