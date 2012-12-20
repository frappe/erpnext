# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals
import webnotes


@webnotes.whitelist(allow_guest=True)
def get_product_info(item_code):
	"""get product price / stock info"""
	price_list = webnotes.conn.get_value("Item", item_code, "website_price_list")
	warehouse = webnotes.conn.get_value("Item", item_code, "website_warehouse")
	if warehouse:
		in_stock = webnotes.conn.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s""", (item_code, warehouse))
		if in_stock:
			in_stock = in_stock[0][0] > 0 and 1 or 0
	else:
		in_stock = -1
	return {
		"price": price_list and webnotes.conn.sql("""select ref_rate, ref_currency from
			`tabItem Price` where parent=%s and price_list_name=%s""", 
			(item_code, price_list), as_dict=1) or [],
		"stock": in_stock
	}

@webnotes.whitelist(allow_guest=True)
def get_product_list(search=None, product_group=None, start=0):
	import webnotes
	from webnotes.utils import cstr
		
	# base query
	query = """\
		select name, item_name, page_name, website_image, item_group, 
			web_long_description as website_description
		from `tabItem`
		where docstatus = 0
		and show_in_website = 1 """
	
	# search term condition
	if search:
		query += """
			and (
				web_long_description like %(search)s or
				item_name like %(search)s or
				name like %(search)s
			)"""
		search = "%" + cstr(search) + "%"
	
	# product group condition
	if product_group:
		query += """
			and item_group = %(product_group)s """
	
	# order by
	query += """order by item_name asc, name asc limit %s, 10""" % start

	return webnotes.conn.sql(query, {
		"search": search,
		"product_group": product_group
	}, as_dict=1)