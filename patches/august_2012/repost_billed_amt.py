# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	from webnotes.model.code import get_obj
	from selling.doctype.sales_common.sales_common import StatusUpdater
	
	invoices = webnotes.conn.sql("select name from `tabSales Invoice` where docstatus = 1")
	for inv in invoices:
		inv_obj = get_obj('Sales Invoice', inv[0], with_children=1)
		StatusUpdater(inv_obj, 1).update_all_qty()