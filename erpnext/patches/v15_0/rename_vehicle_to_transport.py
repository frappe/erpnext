import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	rename_field("Vehicle", "license_plate", "identifier")
	rename_field("Vehicle", "vehicle_value", "transport_value")
	rename_field("Vehicle", "make", "manufacturer")
	rename_field("Vehicle", "chassis_no", "serial_no")
	frappe.rename_doc("DocType", "Vehicle", "Transport", force=True)
	rename_field("Delivery Trip", "vehicle", "transport")
