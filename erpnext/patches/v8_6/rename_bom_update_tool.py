import frappe
def execute():
	frappe.delete_doc_if_exists("DocType", "BOM Replace Tool")

	frappe.reload_doctype("BOM")
	frappe.db.sql("update tabBOM set conversion_rate=1 where conversion_rate is null or conversion_rate=0")
	frappe.db.sql("update tabBOM set set_rate_of_sub_assembly_item_based_on_bom=1")