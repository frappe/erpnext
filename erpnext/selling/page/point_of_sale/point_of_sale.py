# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, json
from frappe.utils.nestedset import get_root_of
from frappe.utils import cint
from erpnext.accounts.doctype.pos_profile.pos_profile import get_item_groups
from erpnext.accounts.doctype.pos_invoice.pos_invoice import get_stock_availability

from six import string_types

@frappe.whitelist()
def get_items(start, page_length, price_list, item_group, search_value="", pos_profile=None):
	data = dict()
	warehouse = ""
	display_items_in_stock = 0

	if pos_profile:
		warehouse, display_items_in_stock = frappe.db.get_value('POS Profile', pos_profile, ['warehouse', 'display_items_in_stock'])

	if not frappe.db.exists('Item Group', item_group):
		item_group = get_root_of('Item Group')

	if search_value:
		data = search_serial_or_batch_or_barcode_number(search_value)

	item_code = data.get("item_code") if data.get("item_code") else search_value
	serial_no = data.get("serial_no") if data.get("serial_no") else ""
	batch_no = data.get("batch_no") if data.get("batch_no") else ""
	barcode = data.get("barcode") if data.get("barcode") else ""

	condition = get_conditions(item_code, serial_no, batch_no, barcode)

	if pos_profile:
		condition += get_item_group_condition(pos_profile)

	lft, rgt = frappe.db.get_value('Item Group', item_group, ['lft', 'rgt'])
	# locate function is used to sort by closest match from the beginning of the value

	result = []

	items_data = frappe.db.sql("""
		SELECT
			name AS item_code,
			item_name,
			description,
			stock_uom,
			image AS item_image,
			idx AS idx,
			is_stock_item
		FROM
			`tabItem`
		WHERE
			disabled = 0
				AND has_variants = 0
				AND is_sales_item = 1
				AND is_fixed_asset = 0
				AND item_group in (SELECT name FROM `tabItem Group` WHERE lft >= {lft} AND rgt <= {rgt})
				AND {condition}
		ORDER BY
			name asc
		LIMIT
			{start}, {page_length}"""
		.format(
			start=start,
			page_length=page_length,
			lft=lft,
			rgt=rgt,
			condition=condition
		), as_dict=1)

	if items_data:
		items = [d.item_code for d in items_data]
		item_prices_data = frappe.get_all("Item Price",
			fields = ["item_code", "price_list_rate", "currency"],
			filters = {'price_list': price_list, 'item_code': ['in', items]})

		item_prices = {}
		for d in item_prices_data:
			item_prices[d.item_code] = d

		for item in items_data:
			item_code = item.item_code
			item_price = item_prices.get(item_code) or {}
			item_stock_qty = get_stock_availability(item_code, warehouse)

			if display_items_in_stock and not item_stock_qty:
				pass
			else:
				row = {}
				row.update(item)
				row.update({
					'price_list_rate': item_price.get('price_list_rate'),
					'currency': item_price.get('currency'),
					'actual_qty': item_stock_qty,
				})
				result.append(row)

	res = {
		'items': result
	}

	if len(res['items']) == 1:
		res['items'][0].setdefault('serial_no', serial_no)
		res['items'][0].setdefault('batch_no', batch_no)
		res['items'][0].setdefault('barcode', barcode)

		return res

	if serial_no:
		res.update({
			'serial_no': serial_no
		})

	if batch_no:
		res.update({
			'batch_no': batch_no
		})

	if barcode:
		res.update({
			'barcode': barcode
		})

	return res

@frappe.whitelist()
def search_serial_or_batch_or_barcode_number(search_value):
	# search barcode no
	barcode_data = frappe.db.get_value('Item Barcode', {'barcode': search_value}, ['barcode', 'parent as item_code'], as_dict=True)
	if barcode_data:
		return barcode_data

	# search serial no
	serial_no_data = frappe.db.get_value('Serial No', search_value, ['name as serial_no', 'item_code'], as_dict=True)
	if serial_no_data:
		return serial_no_data

	# search batch no
	batch_no_data = frappe.db.get_value('Batch', search_value, ['name as batch_no', 'item as item_code'], as_dict=True)
	if batch_no_data:
		return batch_no_data

	return {}

def get_conditions(item_code, serial_no, batch_no, barcode):
	if serial_no or batch_no or barcode:
		return "name = {0}".format(frappe.db.escape(item_code))

	return """(name like {item_code}
		or item_name like {item_code})""".format(item_code = frappe.db.escape('%' + item_code + '%'))

def get_item_group_condition(pos_profile):
	cond = "and 1=1"
	item_groups = get_item_groups(pos_profile)
	if item_groups:
		cond = "and item_group in (%s)"%(', '.join(['%s']*len(item_groups)))

	return cond % tuple(item_groups)

@frappe.whitelist()
def item_group_query(doctype, txt, searchfield, start, page_len, filters):
	item_groups = []
	cond = "1=1"
	pos_profile= filters.get('pos_profile')

	if pos_profile:
		item_groups = get_item_groups(pos_profile)

		if item_groups:
			cond = "name in (%s)"%(', '.join(['%s']*len(item_groups)))
			cond = cond % tuple(item_groups)

	return frappe.db.sql(""" select distinct name from `tabItem Group`
			where {condition} and (name like %(txt)s) limit {start}, {page_len}"""
		.format(condition = cond, start=start, page_len= page_len),
			{'txt': '%%%s%%' % txt})

@frappe.whitelist()
def check_opening_entry(user):
	open_vouchers = frappe.db.get_all("POS Opening Entry", 
		filters = { 
			"user": user, 
			"pos_closing_entry": ["in", ["", None]],
			"docstatus": 1
		}, 
		fields = ["name", "company", "pos_profile", "period_start_date"],
		order_by = "period_start_date desc"
	)

	return open_vouchers

@frappe.whitelist()
def create_opening_voucher(pos_profile, company, balance_details):
	import json
	balance_details = json.loads(balance_details)

	new_pos_opening = frappe.get_doc({
		'doctype': 'POS Opening Entry',
		"period_start_date": frappe.utils.get_datetime(),
		"posting_date": frappe.utils.getdate(),
		"user": frappe.session.user,
		"pos_profile": pos_profile,
		"company": company,
	})
	new_pos_opening.set("balance_details", balance_details)
	new_pos_opening.submit()

	return new_pos_opening.as_dict()

@frappe.whitelist()
def get_past_order_list(search_term, status, limit=20):
	fields = ['name', 'grand_total', 'currency', 'customer', 'posting_time', 'posting_date']
	invoice_list = []

	if search_term and status:
		invoices_by_customer = frappe.db.get_all('POS Invoice', filters={
			'customer': ['like', '%{}%'.format(search_term)],
			'status': status
		}, fields=fields)
		invoices_by_name = frappe.db.get_all('POS Invoice', filters={
			'name': ['like', '%{}%'.format(search_term)],
			'status': status
		}, fields=fields)

		invoice_list = invoices_by_customer + invoices_by_name
	elif status:
		invoice_list = frappe.db.get_all('POS Invoice', filters={
			'status': status
		}, fields=fields)
	
	return invoice_list

@frappe.whitelist()
def set_customer_info(fieldname, customer, value=""):
	if fieldname == 'loyalty_program':
		frappe.db.set_value('Customer', customer, 'loyalty_program', value)

	contact = frappe.get_cached_value('Customer', customer, 'customer_primary_contact')

	if contact:
		contact_doc = frappe.get_doc('Contact', contact)
		if fieldname == 'email_id':
			contact_doc.set('email_ids', [{ 'email_id': value, 'is_primary': 1}])
			frappe.db.set_value('Customer', customer, 'email_id', value)
		elif fieldname == 'mobile_no': 
			contact_doc.set('phone_nos', [{ 'phone': value, 'is_primary_mobile_no': 1}])
			frappe.db.set_value('Customer', customer, 'mobile_no', value)
		contact_doc.save()