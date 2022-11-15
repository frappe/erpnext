# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	frappe.db.sql('''UPDATE `tabDocType` SET module="Core" 
				WHERE name IN ("SMS Parameter", "SMS Settings");''')