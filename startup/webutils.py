# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import cint

def get_website_settings(context):
	post_login = []
	cart_enabled = cint(webnotes.conn.get_default("shopping_cart_enabled"))
	if cart_enabled:
		post_login += [{"label": "Cart", "url": "cart", "icon": "icon-shopping-cart", "class": "cart-count"},
			{"class": "divider"}]
		
	post_login += [
				{"label": "Profile", "url": "profile", "icon": "icon-user"},
				{"label": "Addresses", "url": "addresses", "icon": "icon-map-marker"},
				{"label": "My Orders", "url": "orders", "icon": "icon-list"},
				{"label": "My Tickets", "url": "tickets", "icon": "icon-tags"},
				{"label": "Invoices", "url": "invoices", "icon": "icon-file-text"},
				{"label": "Shipments", "url": "shipments", "icon": "icon-truck"},
				{"class": "divider"}
			]
	context.update({
		"shopping_cart_enabled": cart_enabled,
		"post_login": post_login + context.get("post_login", [])
	})
	
	if not context.get("favicon"):
		context["favicon"] = "app/images/favicon.ico"