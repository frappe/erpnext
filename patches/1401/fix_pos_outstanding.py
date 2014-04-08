# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
from webnotes.utils import flt

def execute():
	for d in webnotes.conn.sql("""select name, debit_to from `tabSales Invoice`
			where ifnull(is_pos, 0)=1 and docstatus=1 and creation > '2014-03-01'"""):
		outstanding_amount = flt(webnotes.conn.sql("""
			select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)) from `tabGL Entry`
			where against_voucher_type='Sales Invoice' and against_voucher=%s and account = %s""",
			(d[0], d[1]))[0][0] or 0.0)
		webnotes.conn.set_value("Sales Invoice", d[0], "outstanding_amount", outstanding_amount)
