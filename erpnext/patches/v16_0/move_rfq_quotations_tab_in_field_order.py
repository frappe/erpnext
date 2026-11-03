import json

import frappe

QUOTATIONS_FIELDS = ["quotations_tab", "quotations_section", "quotations_html"]


def execute():
	# A saved field order would otherwise slot the new tab right after `title`,
	# pulling any fields placed after `title` into the hidden Quotations tab.
	for setter in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Request for Quotation", "property": "field_order"},
		fields=["name", "value"],
	):
		field_order = [f for f in json.loads(setter.value or "[]") if f not in QUOTATIONS_FIELDS]

		if "address_and_contact_tab" in field_order:
			index = field_order.index("address_and_contact_tab")
		else:
			index = len(field_order)

		field_order[index:index] = QUOTATIONS_FIELDS
		frappe.db.set_value("Property Setter", setter.name, "value", json.dumps(field_order))

	frappe.clear_cache(doctype="Request for Quotation")
