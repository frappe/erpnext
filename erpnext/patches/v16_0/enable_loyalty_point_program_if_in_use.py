import frappe
from frappe.utils import cint

from erpnext.accounts.doctype.accounts_settings.accounts_settings import (
	toggle_loyalty_point_program_section,
)


def execute():
	"""Turn on the Loyalty Point Program setting where loyalty is in use or still shown.

	Invoices now earn and redeem points only when the setting is on. It was added later with no
	default. Sites set up after that hide the loyalty fields while it is off. Sites set up before
	it still show them, so a program made there later would earn nothing with no message.
	"""
	if frappe.db.get_single_value("Accounts Settings", "enable_loyalty_point_program", cache=False):
		return

	if not frappe.db.count("Loyalty Program") and is_loyalty_section_hidden():
		return

	frappe.db.set_single_value("Accounts Settings", "enable_loyalty_point_program", 1)
	toggle_loyalty_point_program_section(False)


def is_loyalty_section_hidden() -> bool:
	hidden = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Sales Invoice", "field_name": "loyalty_points_redemption", "property": "hidden"},
		"value",
	)
	return bool(cint(hidden))
