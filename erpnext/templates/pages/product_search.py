# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr
from erpnext.setup.doctype.item_group.item_group import get_item_for_list_in_html

no_cache = 1
no_sitemap = 1

@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=10):
	# base query
	query = """select name, item_name, page_name, website_image, thumbnail, item_group,
			web_long_description as website_description, parent_website_route
		from `tabItem` where show_in_website = 1 and (variant_of is null or variant_of = '')"""

	# search term condition
	if search:
		query += """ and (web_long_description like %(search)s
				or description like %(search)s
				or item_name like %(search)s
				or name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """ order by weightage desc, modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {
		"search": search,
	}, as_dict=1)

	for d in data:
		d.route = ((d.parent_website_route + "/") if d.parent_website_route else "") \
			+ (d.page_name or "")

	return [get_item_for_list_in_html(r) for r in data]

