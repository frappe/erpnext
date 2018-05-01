import frappe, json
from frappe import _

def execute():

	frappe.reload_doc("setup", "doctype", "UOM Conversion Factor")
	frappe.reload_doc("setup", "doctype", "UOM")
	frappe.reload_doc("stock", "doctype", "UOM Category")
	categories = [
		"Length", "Area", "Angle", "Agriculture", "Speed", "Mass", "Density",\
			"Volume", "Time", "Pressure", "Force", "Energy", "Power", "Temperature", "Frequency And Wavelength",\
				"Electrical Charge", "Electric Current", "Magnetic Induction"
	]
	for category in categories:
		if not frappe.db.exists("UOM Category", category):
			frappe.get_doc({
				"doctype": "UOM Category",
				"category_name": category 
			}).insert(ignore_permissions=True)

	if not frappe.db.a_row_exists("UOM Conversion Factor"):
		uom_conversions = json.loads(open(frappe.get_app_path("erpnext", "setup", "setup_wizard", "data", "uom_data.json")).read())
		for d in uom_conversions:
			if not frappe.db.exists("UOM Conversion Factor", d):
				uom_conversion = frappe.new_doc('UOM Conversion Factor')
				uom_conversion.flags.ignore_mandatory = True
				uom_conversion.update(d)
				uom_conversion.save(ignore_permissions=True)

	uom = frappe.db.sql("""select to_uom from `tabUOM Conversion Factor`\
		where to_uom not in ("Kg", "Gram", "Meter", "Hour", "Minute", "Litre")""", as_dict=True)
	for d in uom:
		if not frappe.db.exists("UOM", d.to_uom):
			doc = frappe.new_doc('UOM')
			doc.update({
				"uom_name": d.to_uom
			})
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)