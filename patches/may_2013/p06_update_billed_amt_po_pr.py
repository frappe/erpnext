# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.reload_doc("buying", "doctype", "purchase_order_item")
	webnotes.reload_doc("stock", "doctype", "purchase_receipt_item")
	
	for pi in webnotes.conn.sql("""select name from `tabPurchase Invoice` where docstatus = 1"""):
		webnotes.get_obj("Purchase Invoice", pi[0], 
			with_children=1).update_qty(change_modified=False)
		webnotes.conn.commit()