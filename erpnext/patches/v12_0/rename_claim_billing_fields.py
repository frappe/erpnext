import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	not_hidden_property = frappe.db.get_value("Property Setter",
		{'doc_type': 'Sales Invoice', 'field_name': 'bill_multiple_projects', 'property': 'hidden'})
	label_property = frappe.db.get_value("Property Setter",
		{'doc_type': 'Sales Invoice', 'field_name': 'bill_multiple_projects', 'property': 'label'})

	frappe.reload_doc("accounts", "doctype", "sales_invoice")
	frappe.reload_doc("setup", "doctype", "item_default_rule")
	frappe.reload_doc("selling", "doctype", "campaign")
	frappe.reload_doc("selling", "doctype", "sales_order_item")
	frappe.reload_doc("stock", "doctype", "delivery_note_item")

	# Rename bill_multiple_projects to claim_billing
	if frappe.db.has_column('Sales Invoice', 'bill_multiple_projects'):
		rename_field("Sales Invoice", "bill_multiple_projects", "claim_billing")

	# Rename bill_only_to_customer to claim_customer
	for dt in ['Item Default Rule', 'Campaign', 'Sales Order Item', 'Delivery Note Item']:
		if frappe.db.has_column(dt, 'bill_only_to_customer'):
			rename_field(dt, "bill_only_to_customer", "claim_customer")
		if frappe.db.has_column(dt, 'bill_only_to_customer_name'):
			rename_field(dt, "bill_only_to_customer_name", "claim_customer_name")

	# Reapply property setters
	if not_hidden_property:
		frappe.delete_doc_if_exists("Property Setter", not_hidden_property)
		make_property_setter("Sales Invoice", "claim_billing", "hidden", 0, "Check")

	if label_property:
		frappe.delete_doc_if_exists("Property Setter", label_property)
