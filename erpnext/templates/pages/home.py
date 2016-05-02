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
	
	for item in homepage.products:
		item.route = '/' + '/'.join(frappe.db.get_value('Item', item.item_code, ['parent_website_route', 'page_name']))
		
	
	return {
		'homepage': homepage
	}