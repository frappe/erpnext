# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint

def execute():
	aii_enabled = cint(webnotes.defaults.get_global_default("auto_accounting_for_stock"))
	
	if aii_enabled:
		webnotes.conn.sql("""update `tabGL Entry` gle set is_cancelled = 'Yes' 
			where voucher_type = 'Delivery Note'
			and exists(select name from `tabDelivery Note` 
				where name = gle.voucher_no and docstatus = 2)""")