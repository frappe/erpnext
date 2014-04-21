# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow
from erpnext.setup.doctype.item_group.item_group import get_parent_item_groups

doctype = "Item Group"
condition_field = "show_in_website"

def get_context(context):
	item_group_context = context.doc.as_dict()
	item_group_context.update({
		"items": get_product_list_for_group(product_group = context.docname, limit=100),
		"parent_groups": get_parent_item_groups(context.docname),
		"title": context.docname
	})

	if context.doc.slideshow:
		item_group_context.update(get_slideshow(context.doc))

	return item_group_context

def get_product_list_for_group(product_group=None, start=0, limit=10):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(product_group)])

	# base query
	query = """select t1.name, t1.item_name, t1.page_name, t1.website_image, t1.item_group,
			t1.web_long_description as website_description, t2.name as route
		from `tabItem` t1, `tabWebsite Route` t2
		where t1.show_in_website = 1 and (item_group in (%s)
			or t1.name in (select parent from `tabWebsite Item Group` where item_group in (%s)))
			and t1.name = t2.docname and t2.ref_doctype='Item' """ % (child_groups, child_groups)

	query += """order by t1.weightage desc, t1.modified desc limit %s, %s""" % (start, limit)

	data = frappe.db.sql(query, {"product_group": product_group}, as_dict=1)

	return [get_item_for_list_in_html(r) for r in data]

def get_child_groups(item_group_name):
	item_group = frappe.get_doc("Item Group", item_group_name)
	return frappe.db.sql("""select name
		from `tabItem Group` where lft>=%(lft)s and rgt<=%(rgt)s
			and show_in_website = 1""", item_group.as_dict())

def get_item_for_list_in_html(context):
	return frappe.get_template("templates/includes/product_in_grid.html").render(context)

def get_group_item_count(item_group):
	child_groups = ", ".join(['"' + i[0] + '"' for i in get_child_groups(item_group)])
	return frappe.db.sql("""select count(*) from `tabItem`
		where docstatus = 0 and show_in_website = 1
		and (item_group in (%s)
			or name in (select parent from `tabWebsite Item Group`
				where item_group in (%s))) """ % (child_groups, child_groups))[0][0]

