# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
def execute():
	import webnotes
	webnotes.reload_doc('accounts', 'doctype', 'sales_invoice')
	
	webnotes.conn.sql("update `tabSales Invoice` set recurring_type = 'Monthly' where ifnull(convert_into_recurring_invoice, 0) = 1")