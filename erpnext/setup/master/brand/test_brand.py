# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

test_records = frappe.get_file_json(
	frappe.get_module_path("Setup", "master", "brand", "test_records.json")
)
