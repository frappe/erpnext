import frappe


def execute():
	for custom_field in frappe.get_all(
		"Custom Field",
		filters={
			"fieldname": "service_level_agreement",
			"fieldtype": "Link",
			"options": "Service Level Agreement",
		},
		fields=["name", "dt", "link_filters"],
	):
		if custom_field.link_filters:
			continue

		link_filters = frappe.as_json(
			[["Service Level Agreement", "document_type", "=", custom_field.dt]], indent=None
		)
		frappe.db.set_value(
			"Custom Field", custom_field.name, "link_filters", link_filters, update_modified=False
		)
		frappe.clear_cache(doctype=custom_field.dt)
