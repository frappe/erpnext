# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	if "master_name" in frappe.db.get_table_columns("Account"):	
		frappe.db.sql("""update tabAccount set warehouse=master_name
			where ifnull(account_type, '') = 'Warehouse' and ifnull(master_name, '') != ''""")