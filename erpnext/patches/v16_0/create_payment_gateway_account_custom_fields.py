import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if frappe.db.exists("Installed Application", {"app_name": "payments"}):
		create_custom_fields(
			{
				"Payment Gateway Account": [
					{
						"fieldname": "payment_gateway",
						"fieldtype": "Link",
						"in_list_view": 1,
						"label": "Payment Gateway",
						"options": "Payment Gateway",
						"reqd": 1,
					}
				]
			}
		)

		frappe.clear_cache(doctype="Payment Gateway Account")
