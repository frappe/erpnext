import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("stock", "doctype", "packing_slip")
	frappe.reload_doc("stock", "doctype", "packing_slip_item")
	frappe.reload_doc("stock", "doctype", "packing_slip_packaging_material")
	frappe.reload_doc("stock", "doctype", "package_type_packaging_material")

	rename_map = {
		"Item": [("weight_per_unit", "net_weight_per_unit")],

		"Quotation Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Sales Order Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Delivery Note Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Sales Invoice Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Supplier Quotation Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Purchase Order Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Purchase Receipt Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Purchase Invoice Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],

		"Landed Cost Voucher": [("total_weight", "total_net_weight")],
		"Landed Cost Item": [("weight", "net_weight")],

		"Packing Slip Item": [("weight_per_unit", "net_weight_per_unit"), ("total_weight", "net_weight")],
		"Packing Slip Packaging Material": [("weight_per_unit", "tare_weight_per_unit"), ("total_weight", "tare_weight")],
		"Package Type Packaging Material": [("weight_per_unit", "tare_weight_per_unit"), ("total_weight", "tare_weight")],
	}
	for dt, fields in rename_map.items():
		frappe.reload_doctype(dt, force=1)

		for old_field, new_field in fields:
			if frappe.db.has_column(dt, old_field):
				print("{0}: Renaming Field {1} -> {2}".format(dt, old_field, new_field))
				rename_field(dt, old_field, new_field)
			else:
				print("{0}: Old Field {1} not found".format(dt, old_field, new_field))
