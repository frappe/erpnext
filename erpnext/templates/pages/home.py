# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, nowdate
from erpnext.setup.doctype.item_group.item_group import get_item_for_list_in_html

no_cache = 1
no_sitemap = 1

def get_context(context):
	homepage = frappe.get_doc('Homepage')
	return {
		'homepage': homepage
	}


@frappe.whitelist(allow_guest=True)
def get_product_list(search=None, start=0, limit=6):
	# limit = 12 because we show 12 items in the grid view

	# base query
	query = """select name, item_name, page_name, website_image, thumbnail, item_group,
			web_long_description as website_description, parent_website_route
		from `tabItem`
		where show_in_website = 1
			and disabled=0
			and (end_of_life is null or end_of_life='0000-00-00' or end_of_life > %(today)s)
			and (variant_of is null or variant_of = '')"""

	# order by
	query += """ order by weightage desc, idx desc, modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {
		"today": nowdate()
	}, as_dict=1)

	for d in data:
		d.route = ((d.parent_website_route + "/") if d.parent_website_route else "") \
			+ (d.page_name or "")

	return [get_item_for_list_in_html(r) for r in data]

