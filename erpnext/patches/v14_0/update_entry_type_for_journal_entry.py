import frappe


def execute():
	"""
	Update Propery Setters for Journal Entry with new 'Entry Type'
	"""
	new_voucher_type = "Exchange Gain Or Loss"
	prop_setter = frappe.db.get_list(
		"Property Setter",
		filters={"doc_type": "Journal Entry", "field_name": "voucher_type", "property": "options"},
	)
	if prop_setter:
		property_setter_doc = frappe.get_doc("Property Setter", prop_setter[0].get("name"))

		if new_voucher_type not in property_setter_doc.value.split("\n"):
			property_setter_doc.value += "\n" + new_voucher_type
			property_setter_doc.save()
