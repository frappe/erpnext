# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import frappe.defaults
from frappe.utils import cint

def show_cart_count():
	if (frappe.db.get_default("shopping_cart_enabled") and
		frappe.db.get_value("User", frappe.session.user, "user_type") == "Website User"):
		return True

	return False

def set_cart_count(login_manager):
	if show_cart_count():
		from .shopping_cart.cart import set_cart_count
		set_cart_count()

def clear_cart_count(login_manager):
	if show_cart_count():
		frappe.local.cookie_manager.delete_cookie("cart_count")

def update_website_context(context):
	post_login = []
	cart_enabled = cint(frappe.db.get_default("shopping_cart_enabled"))
	context["shopping_cart_enabled"] = cart_enabled

	if cart_enabled:
		post_login += [
			{"label": "Cart", "url": "cart", "icon": "icon-shopping-cart", "class": "cart-count"},
			{"class": "divider"}
		]

	post_login += [
		{"label": "User", "url": "user", "icon": "icon-user"},
		{"label": "Addresses", "url": "addresses", "icon": "icon-map-marker"},
		{"label": "My Orders", "url": "orders", "icon": "icon-list"},
		{"label": "My Tickets", "url": "tickets", "icon": "icon-tags"},
		{"label": "Invoices", "url": "invoices", "icon": "icon-file-text"},
		{"label": "Shipments", "url": "shipments", "icon": "icon-truck"},
		{"class": "divider"}
	]

	context["post_login"] = post_login + context.get("post_login", [])
