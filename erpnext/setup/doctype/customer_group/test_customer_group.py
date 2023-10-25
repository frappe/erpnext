# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

test_ignore = ["Price List"]


import frappe

test_records = frappe.get_test_records("Customer Group")
