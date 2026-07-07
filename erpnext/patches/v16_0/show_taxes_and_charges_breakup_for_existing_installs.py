import frappe

from erpnext.accounts.doctype.accounts_settings.accounts_settings import (
	toggle_taxes_and_charges_breakup,
)


def execute():
	# "Show Taxes and Charges Breakup" is virtual field.
	# Enable it to preserve old behaviour.
	frappe.db.set_single_value("Accounts Settings", "show_taxes_and_charges_breakup", 1)
	toggle_taxes_and_charges_breakup(hide=0)
