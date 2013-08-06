# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	aii_enabled = cint(webnotes.conn.get_value("Global Defaults", None, 
		"auto_inventory_accounting"))
	
	if aii_enabled:
		webnotes.conn.sql("""update `tabGL Entry` gle set is_cancelled = 'Yes' 
			where voucher_type = 'Delivery Note'
			and exists(select name from `tabDelivery Note` 
				where name = gle.voucher_no and docstatus = 2)""")