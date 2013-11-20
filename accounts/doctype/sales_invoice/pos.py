# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def get_items(price_list, sales_or_purchase, item=None, item_group=None):
	condition = ""
	
	if sales_or_purchase == "Sales":
		condition = "i.is_sales_item='Yes'"
	else:
		condition = "i.is_purchase_item='Yes'"
	
	if item_group and item_group != "All Item Groups":
		condition += " and i.item_group='%s'" % item_group

	if item:
		condition += " and i.name='%s'" % item

	return webnotes.conn.sql("""select i.name, i.item_name, i.image, 
		item_det.ref_rate, item_det.currency 
		from `tabItem` i LEFT JOIN 
			(select item_code, ref_rate, currency from 
				`tabItem Price`	where price_list=%s) item_det
		ON
			item_det.item_code=i.name
		where
			%s""" % ('%s', condition), (price_list), as_dict=1)

@webnotes.whitelist()
def get_item_code(barcode_serial_no):
	input_via = "serial_no"
	item_code = webnotes.conn.sql("""select name, item_code from `tabSerial No` where 
		name=%s""", (barcode_serial_no), as_dict=1)

	if not item_code:
		input_via = "barcode"
		item_code = webnotes.conn.sql("""select name from `tabItem` where barcode=%s""",
			(barcode_serial_no), as_dict=1)

	if item_code:
		return item_code, input_via
	else:
		webnotes.throw("Invalid Barcode / Serial No")

@webnotes.whitelist()
def get_mode_of_payment():
	return webnotes.conn.sql("""select name from `tabMode of Payment`""", as_dict=1)