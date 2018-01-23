# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate, cint
from erpnext.setup.doctype.item_group.item_group import get_item_for_list_in_html
from erpnext.shopping_cart.product_info import get_product_info_for_website

no_cache = 1
no_sitemap = 1

def get_context(context):
	context.show_search = True

@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=12):
	# limit = 12 because we show 12 items in the grid view

	# base query
	query = """select I.name, I.item_name, I.item_code, I.route, I.website_image, I.thumbnail, I.item_group,
			I.description, I.web_long_description as website_description,
			case when (S.actual_qty - S.reserved_qty) > 0 then 1 else 0 end as in_stock
		from `tabItem` I
		left join tabBin S on I.item_code = S.item_code and I.website_warehouse = S.warehouse
		where (I.show_in_website = 1 or I.show_variant_in_website = 1)
			and I.disabled = 0
			and (I.end_of_life is null or I.end_of_life='0000-00-00' or I.end_of_life > %(today)s)"""

	# search term condition
	if search:
		query += """ and (I.web_long_description like %(search)s
				or I.description like %(search)s
				or I.item_name like %(search)s
				or I.name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """ order by I.weightage desc, in_stock desc, I.item_name limit %s, %s""" % (cint(start), cint(limit))

	data = frappe.db.sql(query, {
		"search": search,
		"today": nowdate()
	}, as_dict=1)

	for item in data:
		product_info = get_product_info_for_website(item.item_code)
		if product_info:
			item["stock_uom"] = product_info.get("uom")
			item["sales_uom"] = product_info.get("sales_uom")
			if product_info.get("price"):
				item["price_stock_uom"] = product_info.get("price").get("formatted_price")
				item["price_sales_uom"] = product_info.get("price").get("formatted_price_sales_uom")
			else:
				item["price_stock_uom"] = ""
				item["price_sales_uom"] = ""

	return [get_item_for_list_in_html(r) for r in data]

