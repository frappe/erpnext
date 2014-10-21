# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from shopping_cart.templates.utils import get_transaction_context

no_cache = 1
no_sitemap = 1

def get_context(context):
	shipment_context = frappe._dict({
		"parent_link": "shipments",
		"parent_title": "Shipments"
	})
	shipment_context.update(get_transaction_context("Delivery Note", frappe.form_dict.name))
	return shipment_context
