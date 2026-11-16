# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe


def get_data():
	transactions = [{"items": ["Delivery Trip"]}]
	if frappe.db.exists("DocType", "Vehicle Log", cache=True):
		transactions.insert(0, {"items": ["Vehicle Log"]})

	return {
		"fieldname": "license_plate",
		"non_standard_fieldnames": {"Delivery Trip": "vehicle"},
		"transactions": transactions,
	}
