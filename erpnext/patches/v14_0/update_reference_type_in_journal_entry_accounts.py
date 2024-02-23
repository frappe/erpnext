import frappe


def execute():
	"""
	Update Propery Setters for Journal Entry with new 'Entry Type'
	"""
	new_reference_type = "Payment Entry"
	prop_setter = frappe.db.get_list(
		"Property Setter",
		filters={
			"doc_type": "Journal Entry Account",
			"field_name": "reference_type",
			"property": "options",
		},
	)
	if prop_setter:
		property_setter_doc = frappe.get_doc("Property Setter", prop_setter[0].get("name"))

		if new_reference_type not in property_setter_doc.value.split("\n"):
			property_setter_doc.value += "\n" + new_reference_type
			property_setter_doc.save()
