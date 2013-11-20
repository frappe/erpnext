# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
def execute():
	si_list = webnotes.conn.sql("""select name, debit_to from `tabSales Invoice` 
		where ifnull(is_pos, 1)=1 and docstatus=1 and modified > '2013-09-03'""", as_dict=1)
		
	for si in si_list:
		if not webnotes.conn.get_value("GL Entry", {"voucher_type": "Sales Invoice", 
			"voucher_no": si.name, "account": si.debit_to}):
				debit_to = webnotes.conn.sql("""select account from `tabGL Entry` gle
					where voucher_type='Sales Invoice' and voucher_no=%s 
					and (select master_type from tabAccount where name=gle.account)='Customer'
				""", si.name)
				if debit_to:
					si_bean = webnotes.bean("Sales Invoice", si.name)
					si_bean.doc.debit_to = debit_to[0][0]
					si_bean.doc.customer = None
					si_bean.run_method("set_customer_defaults")
					si_bean.update_after_submit()