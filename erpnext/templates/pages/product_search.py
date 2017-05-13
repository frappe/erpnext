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
	query = """select name, item_name, item_code, route, website_image, thumbnail, item_group,
			description, web_long_description as website_description
		from `tabItem`
		where (show_in_website = 1 or show_variant_in_website = 1)
			and disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %(today)s)"""

	# search term condition
	if search:
		query += """ and (web_long_description like %(search)s
				or description like %(search)s
				or item_name like %(search)s
				or name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """ order by weightage desc, idx desc, modified desc limit %s, %s""" % (cint(start), cint(limit))

	data = frappe.db.sql(query, {
		"search": search,
		"today": nowdate()
	}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

