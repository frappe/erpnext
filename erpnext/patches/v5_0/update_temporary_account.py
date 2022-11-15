# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.db.sql("""Update `tabAccount` set account_type = 'Temporary' 
		where account_name in ('Temporary Assets', 'Temporary Liabilities', 'Temporary Opening')""")