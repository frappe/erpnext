# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
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
	query = """select t1.name, t1.item_name, t1.page_name, t1.website_image, t1.item_group,
			t1.web_long_description as website_description, t2.name as route
		from `tabItem` t1, `tabWebsite Route` t2 where t1.show_in_website = 1
			and t1.name = t2.docname and t2.ref_doctype = 'Item'"""

	# search term condition
	if search:
		query += """and (t1.web_long_description like %(search)s or t1.description like %(search)s or
				t1.item_name like %(search)s or t1.name like %(search)s)"""
		search = "%" + cstr(search) + "%"

	# order by
	query += """order by t1.weightage desc, t1.modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {
		"search": search,
	}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

