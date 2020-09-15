import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_custom_pos_fields():
	"""
		Create custom fields corresponding to POS Settings and POS Invoice
	"""
	pos_field = {
		"POS Invoice": [
			{
				"fieldname": "request_for_payment",
				"label": "Request for Payment",
				"fieldtype": "Button",
				"hidden": 1,
				"insert_after": "contact_email"
			},
		]
	}
	if not frappe.get_meta("POS Invoice").has_field("request_for_payment"):
		create_custom_fields(pos_field)

	record_dict = [{
			"doctype": "POS Field",
			"fieldname": "contact_mobile",
			"label": "Mobile No",
			"fieldtype": "Data",
			"options": "Phone",
			"parent": "POS Settings"
		},
		{
			"doctype": "POS Field",
			"fieldname": "request_for_payment",
			"label": "Request for Payment",
			"fieldtype": "Button",
			"parent": "POS Settings"
		}
	]
	create_pos_settings(record_dict)

def create_pos_settings(record_dict):
	for record in record_dict:
		if frappe.db.exists("POS Field", {"fieldname": record.get("fieldname")}):
			continue
		frappe.get_doc(record).insert()