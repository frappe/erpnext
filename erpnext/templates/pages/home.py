# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

no_cache = 1
no_sitemap = 1

def get_context(context):
	homepage = frappe.get_doc('Homepage')

	for item in homepage.products:
		route = frappe.db.get_value('Item', item.item_code, 'route')
		if route:
			item.route = '/' + route

	context.title = homepage.title or homepage.company

	# show atleast 3 products
	if len(homepage.products) < 3:
		for i in range(3 - len(homepage.products)):
			homepage.append('products', {
				'item_code': 'product-{0}'.format(i),
				'item_name': frappe._('Product {0}').format(i),
				'route': '#'
			})

	context.homepage = homepage
