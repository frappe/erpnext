# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes

def execute():
    webnotes.reload_doc("Stock", "DocType", "Delivery Note Item")
    for dt in ("Journal Voucher Detail", "Sales Taxes and Charges", 
		"Purchase Taxes and Charges", "Delivery Note Item", 
		"Purchase Invoice Item", "Sales Invoice Item"):
			webnotes.conn.sql_ddl("""alter table `tab%s` alter `cost_center` drop default""" \
				% (dt,))
			webnotes.reload_doc(webnotes.conn.get_value("DocType", dt, "module"), "DocType", dt)
