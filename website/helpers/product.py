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
def get_product_list(args=None):
	import webnotes
	from webnotes.utils import cstr
	
	if not args: args = webnotes.form_dict
	if not args.search: args.search = ""
	
	# base query
	query = """\
		select name, item_name, page_name, website_image, item_group, 
			if(ifnull(web_short_description,'')='', web_long_description, 
			web_short_description) as web_short_description
		from `tabItem`
		where docstatus = 0
		and show_in_website = 1 """
	
	# search term condition
	if args.search:
		query += """
			and (
				web_short_description like %(search)s or
				web_long_description like %(search)s or
				description like %(search)s or
				item_name like %(search)s or
				name like %(search)s
			)"""
		args['search'] = "%" + cstr(args.get('search')) + "%"
	
	# product group condition
	if args.get('product_group') and args.get('product_group') != 'All Products':
		query += """
			and item_group = %(product_group)s """
	
	# order by
	query += """order by item_name asc, name asc limit %s, 10""" % args.start

	return webnotes.conn.sql(query, args, as_dict=1)