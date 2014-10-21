# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from shopping_cart.templates.utils import get_currency_context, get_transaction_list
from shopping_cart.templates.pages.order import modify_status

no_cache = 1
no_sitemap = 1

def get_context(context):
	orders_context = get_currency_context()
	orders_context.update({
		"title": "My Orders",
		"method": "shopping_cart.templates.pages.orders.get_orders",
		"icon": "icon-list",
		"empty_list_message": "No Orders Yet",
		"page": "order",
	})
	return orders_context
	
@frappe.whitelist()
def get_orders(start=0):
	orders = get_transaction_list("Sales Order", start, ["per_billed", "per_delivered"])
	for d in orders:
		modify_status(d)
		
	return orders
	