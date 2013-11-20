# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import webnotes
from webnotes.utils import cstr, cint, fmt_money, get_base_path
from webnotes.webutils import delete_page_cache
from selling.utils.cart import _get_cart_quotation

@webnotes.whitelist(allow_guest=True)
def get_product_info(item_code):
	"""get product price / stock info"""
	if not cint(webnotes.conn.get_default("shopping_cart_enabled")):
		return {}
	
	cart_quotation = _get_cart_quotation()
	
	price_list = webnotes.cookies.get("selling_price_list").value

	warehouse = webnotes.conn.get_value("Item", item_code, "website_warehouse")
	if warehouse:
		in_stock = webnotes.conn.sql("""select actual_qty from tabBin where
			item_code=%s and warehouse=%s""", (item_code, warehouse))
		if in_stock:
			in_stock = in_stock[0][0] > 0 and 1 or 0
	else:
		in_stock = -1
		
	price = price_list and webnotes.conn.sql("""select ref_rate, currency from
		`tabItem Price` where item_code=%s and price_list=%s""", 
		(item_code, price_list), as_dict=1) or []
	
	price = price and price[0] or None
	qty = 0

	if price:
		price["formatted_price"] = fmt_money(price["ref_rate"], currency=price["currency"])
		
		price["currency"] = not cint(webnotes.conn.get_default("hide_currency_symbol")) \
			and (webnotes.conn.get_value("Currency", price.currency, "symbol") or price.currency) \
			or ""
		
		if webnotes.session.user != "Guest":
			item = cart_quotation.doclist.get({"item_code": item_code})
			if item:
				qty = item[0].qty

	return {
		"price": price,
		"stock": in_stock,
		"uom": webnotes.conn.get_value("Item", item_code, "stock_uom"),
		"qty": qty
	}

@webnotes.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=10):
	# base query
	query = """select name, item_name, page_name, website_image, item_group, 
			web_long_description as website_description
		from `tabItem` where docstatus = 0 and show_in_website = 1 """
	
	# search term condition
	if search:
		query += """and (web_long_description like %(search)s or
				item_name like %(search)s or name like %(search)s)"""
		search = "%" + cstr(search) + "%"
	
	# order by
	query += """order by weightage desc, modified desc limit %s, %s""" % (start, limit)

	data = webnotes.conn.sql(query, {
		"search": search,
	}, as_dict=1)
	
	return [get_item_for_list_in_html(r) for r in data]


def get_product_list_for_group(product_group=None, start=0, limit=10):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(product_group)])

	# base query
	query = """select name, item_name, page_name, website_image, item_group, 
			web_long_description as website_description
		from `tabItem` where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group` where item_group in (%s))) """ % (child_groups, child_groups)
	
	query += """order by weightage desc, modified desc limit %s, %s""" % (start, limit)

	data = webnotes.conn.sql(query, {"product_group": product_group}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

def get_child_groups(item_group_name):
	item_group = webnotes.doc("Item Group", item_group_name)
	return webnotes.conn.sql("""select name 
		from `tabItem Group` where lft>=%(lft)s and rgt<=%(rgt)s
			and show_in_website = 1""", item_group.fields)

def get_group_item_count(item_group):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(item_group)])
	return webnotes.conn.sql("""select count(*) from `tabItem` 
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group` 
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]

def get_item_for_list_in_html(context):
	from jinja2 import Environment, FileSystemLoader
	scrub_item_for_list(context)
	jenv = Environment(loader = FileSystemLoader(get_base_path()))
	template = jenv.get_template("app/stock/doctype/item/templates/includes/product_in_grid.html")
	return template.render(context)

def scrub_item_for_list(r):
	if not r.website_description:
		r.website_description = "No description given"
	if len(r.website_description.split(" ")) > 24:
		r.website_description = " ".join(r.website_description.split(" ")[:24]) + "..."

def get_parent_item_groups(item_group_name):
	item_group = webnotes.doc("Item Group", item_group_name)
	return webnotes.conn.sql("""select name, page_name from `tabItem Group`
		where lft <= %s and rgt >= %s 
		and ifnull(show_in_website,0)=1
		order by lft asc""", (item_group.lft, item_group.rgt), as_dict=True)
		
def invalidate_cache_for(item_group):
	for i in get_parent_item_groups(item_group):
		if i.page_name:
			delete_page_cache(i.page_name)