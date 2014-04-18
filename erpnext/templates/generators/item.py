# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from erpnext.setup.doctype.item_group.item_group import get_parent_item_groups
from frappe.website.doctype.website_slideshow.website_slideshow import get_slideshow

doctype = "Item"
condition_field = "show_in_website"

def get_context(context):
	item_context = context.doc.as_dict()
	item_context["parent_groups"] = get_parent_item_groups(context.doc.item_group) + \
		[{"name":context.doc.name}]
	if context.doc.slideshow:
		item_context.update(get_slideshow(context.doc))

	return item_context
