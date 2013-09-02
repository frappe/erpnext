# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

@webnotes.whitelist()
def get_items(price_list, item=None, item_group=None):
	condition = ""
	
	if item_group and item_group != "All Item Groups":
		condition = "and i.item_group='%s'" % item_group

	if item:
		condition = "and i.name='%s'" % item

	return webnotes.conn.sql("""select 
		i.name, i.item_name, i.image, ip.ref_rate, ip.ref_currency 
		from `tabItem` i LEFT JOIN `tabItem Price` ip 
			ON ip.parent=i.name 
			and ip.price_list=%s 
		where
			i.is_sales_item='Yes'%s""" % ('%s', condition), (price_list), as_dict=1)

@webnotes.whitelist()
def get_item_from_barcode(barcode):
	return webnotes.conn.sql("""select name from `tabItem` where barcode=%s""",
		(barcode), as_dict=1)

@webnotes.whitelist()
def get_mode_of_payment():
	return webnotes.conn.sql("""select name from `tabMode of Payment`""", as_dict=1)