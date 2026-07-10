import frappe


def execute():
	for docfield in frappe.get_all(
		"DocField",
		filters={
			"parenttype": "DocType",
			"fieldname": "service_level_agreement",
			"fieldtype": "Link",
			"options": "Service Level Agreement",
			"link_filters": ("is", "not set"),
		},
		fields=["name", "parent"],
	):
		link_filters = frappe.as_json(
			[["Service Level Agreement", "document_type", "=", docfield.parent]], indent=None
		)
		frappe.db.set_value("DocField", docfield.name, "link_filters", link_filters, update_modified=False)
		frappe.clear_cache(doctype=docfield.parent)
