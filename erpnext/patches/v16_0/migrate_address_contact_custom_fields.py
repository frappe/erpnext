import frappe

from erpnext.setup.install import create_address_and_contact_custom_fields


def execute():
	"""Replace fixture-based custom fields on Address and Contact with programmatic ones."""
	for custom_field in (
		"Address-tax_category",
		"Address-is_your_company_address",
		"Contact-is_billing_contact",
	):
		if frappe.db.exists("Custom Field", custom_field):
			frappe.delete_doc("Custom Field", custom_field, ignore_missing=True, force=True)

	create_address_and_contact_custom_fields()
