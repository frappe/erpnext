# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from shopping_cart.templates.utils import get_currency_context

no_cache = 1
no_sitemap = 1

def get_context(context):
	invoices_context = get_currency_context()
	invoices_context.update({
		"title": "Invoices",
		"method": "shopping_cart.templates.pages.invoices.get_invoices",
		"icon": "icon-file-text",
		"empty_list_message": "No Invoices Found",
		"page": "invoice"
	})
	return invoices_context
	
@frappe.whitelist()
def get_invoices(start=0):
	from shopping_cart.templates.utils import get_transaction_list
	from shopping_cart.templates.pages.invoice import modify_status
	invoices = get_transaction_list("Sales Invoice", start, ["outstanding_amount"])
	for d in invoices:
		modify_status(d)
	return invoices