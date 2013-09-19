# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint

@webnotes.whitelist()
def get_items(price_list, item=None, item_group=None):
	condition = ""
	
	if item_group and item_group != "All Item Groups":
		condition = "and i.item_group='%s'" % item_group

	if item:
		condition = "and i.name='%s'" % item

	return webnotes.conn.sql("""select i.name, i.item_name, i.image, 
		pl_items.ref_rate, pl_items.currency 
		from `tabItem` i LEFT JOIN 
			(select ip.item_code, ip.ref_rate, pl.currency from 
				`tabItem Price` ip, `tabPrice List` pl 
				where ip.parent=%s and ip.parent = pl.name) pl_items
		ON
			pl_items.item_code=i.name
		where
			i.is_sales_item='Yes'%s""" % ('%s', condition), (price_list), as_dict=1)

@webnotes.whitelist()
def get_item_from_barcode(barcode):
	return webnotes.conn.sql("""select name from `tabItem` where barcode=%s""",
		(barcode), as_dict=1)

@webnotes.whitelist()
def get_mode_of_payment():
	return webnotes.conn.sql("""select name from `tabMode of Payment`""", as_dict=1)