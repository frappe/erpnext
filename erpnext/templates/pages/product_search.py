# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate, cint
from erpnext.setup.doctype.item_group.item_group import get_item_for_list_in_html

no_cache = 1
no_sitemap = 1

def get_context(context):
	context.show_search = True

@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=12):
	# limit = 12 because we show 12 items in the grid view

	# base query
	query = """select tabItem.name, tabItem.item_name, tabItem.item_code, tabItem.route, tabItem.website_image,
			tabItem.thumbnail, tabItem.item_group, tabItem.description, tabItem.web_long_description as website_description,
			case when ifnull(tabBin.actual_qty,0) > 0 then 1 else 0 end as in_stock
		from `tabItem`
		left join tabBin on	tabItem.item_code=tabBin.item_code and tabItem.website_warehouse=tabBin.warehouse
		where (tabItem.show_in_website = 1 or tabItem.show_variant_in_website = 1)
			and tabItem.disabled=0
			and (tabItem.end_of_life is null or tabItem.end_of_life='0000-00-00' or tabItem.end_of_life > %(today)s)"""

	# search term condition
	if search:
		query += """ and (tabItem.web_long_description like %(search)s
				or tabItem.description like %(search)s
				or tabItem.item_name like %(search)s
				or tabItem.name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """ order by tabItem.weightage desc, in_stock desc, tabItem.item_name limit %s, %s""" % (cint(start), cint(limit))

	data = frappe.db.sql(query, {
		"search": search,
		"today": nowdate()
	}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

