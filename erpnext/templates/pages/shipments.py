# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from shopping_cart.templates.utils import get_currency_context

no_cache = 1
no_sitemap = 1

def get_context(context):
	shipments_context = get_currency_context()
	shipments_context.update({
		"title": "Shipments",
		"method": "shopping_cart.templates.pages.shipments.get_shipments",
		"icon": "icon-truck",
		"empty_list_message": "No Shipments Found",
		"page": "shipment"
	})
	return shipments_context
	
@frappe.whitelist()
def get_shipments(start=0):
	from shopping_cart.templates.utils import get_transaction_list
	return get_transaction_list("Delivery Note", start)
