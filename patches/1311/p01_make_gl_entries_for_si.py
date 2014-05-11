# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

def execute():
	si_no_gle = webnotes.conn.sql("""select si.name from `tabSales Invoice` si 
		where docstatus=1 and not exists(select name from `tabGL Entry` 
			where voucher_type='Sales Invoice' and voucher_no=si.name) 
		and modified >= '2013-08-01'""")

	for si in si_no_gle:
		webnotes.get_obj("Sales Invoice", si[0]).make_gl_entries()