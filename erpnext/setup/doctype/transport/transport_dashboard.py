# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


def get_data():
	return {
		"fieldname": "license_plate",
		"non_standard_fieldnames": {"Delivery Trip": "transport"},
		"transactions": [{"items": ["Transport Log"]}, {"items": ["Delivery Trip"]}],
	}
