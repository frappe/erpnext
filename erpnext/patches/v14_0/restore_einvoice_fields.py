import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.regional.india.setup import add_permissions, add_print_formats


def execute():
	# restores back the 2 custom fields that was deleted while removing e-invoicing from v14
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	custom_fields = {
		"Sales Invoice": [
			dict(
				fieldname="irn_cancelled",
				label="IRN Cancelled",
				fieldtype="Check",
				no_copy=1,
				print_hide=1,
				depends_on="eval:(doc.irn_cancelled === 1)",
				read_only=1,
				allow_on_submit=1,
				insert_after="customer",
			),
			dict(
				fieldname="eway_bill_cancelled",
				label="E-Way Bill Cancelled",
				fieldtype="Check",
				no_copy=1,
				print_hide=1,
				depends_on="eval:(doc.eway_bill_cancelled === 1)",
				read_only=1,
				allow_on_submit=1,
				insert_after="customer",
			),
		]
	}
	create_custom_fields(custom_fields, update=True)
	add_permissions()
	add_print_formats()
