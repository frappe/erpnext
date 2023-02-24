import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if frappe.get_all("Company", filters={"country": "India"}):
		custom_fields = get_non_profit_custom_fields()
		create_custom_fields(custom_fields, update=True)

		if not frappe.db.exists("Party Type", "Donor"):
			frappe.get_doc(
				{"doctype": "Party Type", "party_type": "Donor", "account_type": "Receivable"}
			).insert(ignore_permissions=True, ignore_mandatory=True)


def get_non_profit_custom_fields():
	return {
		"Company": [
			{
				"fieldname": "non_profit_section",
				"label": "Non Profit Settings",
				"fieldtype": "Section Break",
				"insert_after": "asset_received_but_not_billed",
				"collapsible": 1,
			},
			{
				"fieldname": "company_80g_number",
				"label": "80G Number",
				"fieldtype": "Data",
				"insert_after": "non_profit_section",
			},
			{
				"fieldname": "with_effect_from",
				"label": "80G With Effect From",
				"fieldtype": "Date",
				"insert_after": "company_80g_number",
			},
			{
				"fieldname": "pan_details",
				"label": "PAN Number",
				"fieldtype": "Data",
				"insert_after": "with_effect_from",
			},
		],
		"Member": [
			{
				"fieldname": "pan_number",
				"label": "PAN Details",
				"fieldtype": "Data",
				"insert_after": "email_id",
			},
		],
		"Donor": [
			{
				"fieldname": "pan_number",
				"label": "PAN Details",
				"fieldtype": "Data",
				"insert_after": "email",
			},
		],
	}
