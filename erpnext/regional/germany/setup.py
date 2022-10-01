import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def setup(company=None, patch=True):
	make_custom_fields()
	add_custom_roles_for_reports()


def make_custom_fields():
	custom_fields = {
		"Party Account": [
			dict(
				fieldname="debtor_creditor_number",
				label="Debtor/Creditor Number",
				fieldtype="Data",
				insert_after="account",
				translatable=0,
			)
		]
	}

	create_custom_fields(custom_fields)


def add_custom_roles_for_reports():
	"""Add Access Control to UAE VAT 201."""
	if not frappe.db.get_value("Custom Role", dict(report="DATEV")):
		frappe.get_doc(
			dict(
				doctype="Custom Role",
				report="DATEV",
				roles=[dict(role="Accounts User"), dict(role="Accounts Manager")],
			)
		).insert()
