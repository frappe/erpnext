# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

def execute():
	if frappe.db.exists('Module Def', 'Fleet Management'):
		frappe.db.sql("""delete from `tabModule Def`
			where module_name = 'Fleet Management'""")