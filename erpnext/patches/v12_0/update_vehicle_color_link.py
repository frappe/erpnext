import frappe
from frappe.utils import cstr

def execute():
	frappe.reload_doc("vehicles", "doctype", "vehicle_color")

	if "Vehicles" not in frappe.get_active_domains():
		return

	dts = ['Project', 'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Vehicle']

	all_colors = set()
	for dt in dts:
		color_field = 'color' if dt == "Vehicle" else 'vehicle_color'
		colors = frappe.get_all(dt, filters={color_field: ['is', 'set']}, fields=['name', color_field])
		for d in colors:
			color = d[color_field]
			formatted_color = cstr(color).title().strip()
			if color != formatted_color:
				frappe.db.set_value(dt, d.name, color_field, formatted_color)

			all_colors.add(formatted_color)

	for color in all_colors:
		doc = frappe.new_doc("Vehicle Color")
		doc.vehicle_color = color
		doc.insert()

	frappe.reload_doc("projects", "doctype", "project")
	frappe.reload_doc("selling", "doctype", "quotation")
	frappe.reload_doc("selling", "doctype", "sales_order")
	frappe.reload_doc("stock", "doctype", "delivery_note")
	frappe.reload_doc("accounts", "doctype", "sales_invoice")
