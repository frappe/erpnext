import frappe

def execute():
	if not frappe.db.exists("DocType", "HS Code"):
		return

	if frappe.get_meta("Item").has_field("hs_code"):
		frappe.db.sql("update `tabItem` set customs_tariff_number = hs_code")

	frappe.reload_doc("stock", "doctype", "customs_tariff_number")

	hs_codes = frappe.get_all("HS Code", fields=['name', 'description'])
	for d in hs_codes:
		if not frappe.db.exists("Customs Tariff Number", d.name):
			doc = frappe.new_doc("Customs Tariff Number")
			doc.tariff_number = d.name
			doc.description = d.description or d.name
			doc.save()

	frappe.db.sql("update `tabItem Tax` set parent = 'Customs Tariff Number' where parent = 'HS Code'")

	frappe.delete_doc_if_exists("DocType", "HS Code")