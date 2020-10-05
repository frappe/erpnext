import frappe

def execute():
	props = frappe.get_all("Property Setter", filters={
		"doc_type": "Sales Invoice",
		"field_name": ["in", ["stin", "has_stin"]],
		"property": ["!=", "default"]
	})

	for d in props:
		frappe.delete_doc("Property Setter", d.name)
