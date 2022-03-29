import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from erpnext.regional.india.setup import add_permissions, add_print_formats


def execute():
	company = frappe.get_all("Company", filters={"country": "India"})
	if not company:
		return

	frappe.reload_doc("custom", "doctype", "custom_field")
	frappe.reload_doc("regional", "doctype", "e_invoice_settings")
	custom_fields = {
		"Sales Invoice": [
			dict(
				fieldname="irn",
				label="IRN",
				fieldtype="Data",
				read_only=1,
				insert_after="customer",
				no_copy=1,
				print_hide=1,
				depends_on='eval:in_list(["Registered Regular", "SEZ", "Overseas", "Deemed Export"], doc.gst_category) && doc.irn_cancelled === 0',
			),
			dict(
				fieldname="ack_no",
				label="Ack. No.",
				fieldtype="Data",
				read_only=1,
				hidden=1,
				insert_after="irn",
				no_copy=1,
				print_hide=1,
			),
			dict(
				fieldname="ack_date",
				label="Ack. Date",
				fieldtype="Data",
				read_only=1,
				hidden=1,
				insert_after="ack_no",
				no_copy=1,
				print_hide=1,
			),
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
			dict(
				fieldname="signed_einvoice",
				fieldtype="Code",
				options="JSON",
				hidden=1,
				no_copy=1,
				print_hide=1,
				read_only=1,
			),
			dict(
				fieldname="signed_qr_code",
				fieldtype="Code",
				options="JSON",
				hidden=1,
				no_copy=1,
				print_hide=1,
				read_only=1,
			),
			dict(
				fieldname="qrcode_image",
				label="QRCode",
				fieldtype="Attach Image",
				hidden=1,
				no_copy=1,
				print_hide=1,
				read_only=1,
			),
		]
	}
	create_custom_fields(custom_fields, update=True)
	add_permissions()
	add_print_formats()

	einvoice_cond = (
		'in_list(["Registered Regular", "SEZ", "Overseas", "Deemed Export"], doc.gst_category)'
	)
	t = {
		"mode_of_transport": [{"default": None}],
		"distance": [{"mandatory_depends_on": f"eval:{einvoice_cond} && doc.transporter"}],
		"gst_vehicle_type": [
			{"mandatory_depends_on": f'eval:{einvoice_cond} && doc.mode_of_transport == "Road"'}
		],
		"lr_date": [
			{
				"mandatory_depends_on": f'eval:{einvoice_cond} && in_list(["Air", "Ship", "Rail"], doc.mode_of_transport)'
			}
		],
		"lr_no": [
			{
				"mandatory_depends_on": f'eval:{einvoice_cond} && in_list(["Air", "Ship", "Rail"], doc.mode_of_transport)'
			}
		],
		"vehicle_no": [
			{"mandatory_depends_on": f'eval:{einvoice_cond} && doc.mode_of_transport == "Road"'}
		],
		"ewaybill": [
			{"read_only_depends_on": "eval:doc.irn && doc.ewaybill"},
			{"depends_on": "eval:((doc.docstatus === 1 || doc.ewaybill) && doc.eway_bill_cancelled === 0)"},
		],
	}

	for field, conditions in t.items():
		for c in conditions:
			[(prop, value)] = c.items()
			frappe.db.set_value("Custom Field", {"fieldname": field}, prop, value)
