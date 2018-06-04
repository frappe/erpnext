import frappe, json

def execute():
	frappe.reload_doc("setup", "doctype", "UOM Conversion Factor")
	frappe.reload_doc("setup", "doctype", "UOM")
	frappe.reload_doc("stock", "doctype", "UOM Category")

	if not frappe.db.a_row_exists("UOM Conversion Factor"):
		uom_conversions = json.loads(open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read())
		for d in uom_conversions:
			# Add UOM Category
			if not frappe.db.exists("UOM Category", d.get("category")):
				frappe.get_doc({
					"doctype": "UOM Category",
					"category_name": d.get("category")
				}).insert(ignore_permissions=True)
			# Add UOM
			if not frappe.db.exists("UOM", d.get("to_uom")):
				frappe.get_doc({
					"doctype": "UOM",
					"uom_name": d.get("to_uom")
				}).insert(ignore_permissions=True, ignore_mandatory=True)
			# Add UOM Conversion Factors
			uom_conversion = frappe.new_doc('UOM Conversion Factor')
			uom_conversion.update(d)
			uom_conversion.save(ignore_permissions=True)