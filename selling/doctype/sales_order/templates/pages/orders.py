# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

no_cache = True

def get_context():
	from portal.website_transactions import get_currency_context
	context = get_currency_context()
	context.update({
		"title": "My Orders",
		"method": "portal.templates.pages.orders.get_orders",
		"icon": "icon-list",
		"empty_list_message": "No Orders Yet",
		"page": "order",
	})
	return context
	
@webnotes.whitelist()
def get_orders(start=0):
	from portal.website_transactions import get_transaction_list
	return get_transaction_list("Sales Order", start)
	