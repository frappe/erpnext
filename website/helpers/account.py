# Copyright (c) 2012 Web Notes Technologies Pvt Ltd.
# License: GNU General Public License (v3). For more information see license.txt

from __future__ import unicode_literals

import webnotes
from webnotes.utils import cstr

@webnotes.whitelist()
def get_orders():
	# find customer id
	customer = webnotes.conn.get_value("Contact", {"email_id": webnotes.session.user}, 
		"customer")
	
	if customer:
		orders = webnotes.conn.sql("""select name, creation, currency from `tabSales Order`
			where customer=%s""", customer, as_dict=1)
		for order in orders:
			order.items = webnotes.conn.sql("""select item_name, qty, export_rate, delivered_qty
				from `tabSales Order Item` where parent=%s order by idx""", order.name, as_dict=1)
		return orders
	else:
		return []