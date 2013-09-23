# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

no_cache = True

def get_context():
	from portal.utils import get_currency_context
	context = get_currency_context()
	context.update({
		"title": "My Orders",
		"method": "selling.doctype.sales_order.templates.pages.orders.get_orders",
		"icon": "icon-list",
		"empty_list_message": "No Orders Yet",
		"page": "order",
	})
	return context
	
@webnotes.whitelist()
def get_orders(start=0):
	from portal.utils import get_transaction_list
	from selling.doctype.sales_order.templates.pages.order import modify_status
	orders = get_transaction_list("Sales Order", start, ["per_billed", "per_delivered"])
	for d in orders:
		modify_status(d)
		
	return orders
	