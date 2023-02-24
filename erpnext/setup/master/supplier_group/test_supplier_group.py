# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

test_records = frappe.get_file_json(
	frappe.get_module_path("Setup", "master", "supplier_group", "test_records.json")
)
