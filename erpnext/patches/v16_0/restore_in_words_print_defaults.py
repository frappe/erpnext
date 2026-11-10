import frappe


def execute():
	# Global Defaults must not override these fields' standard print visibility.
	for setter in frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": ("in", ["Payment Entry", "Subcontracting Receipt"]),
			"field_name": "in_words",
			"property": "print_hide",
			"is_system_generated": 1,
		},
		fields=["name", "doc_type"],
	):
		frappe.delete_doc("Property Setter", setter.name)
		frappe.clear_cache(doctype=setter.doc_type)
