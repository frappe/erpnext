import frappe

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.repost_accounting_ledger.repost_accounting_ledger import (
	get_allowed_types_from_settings,
)


def execute():
<<<<<<< HEAD
	for dt in get_allowed_types_from_settings(child_doc=True):
=======
	for dt in get_allowed_types_from_settings():
>>>>>>> 7c4cf3e834 (Favicon.svg)
		for dimension in get_accounting_dimensions():
			frappe.db.set_value("Custom Field", dt + "-" + dimension, "allow_on_submit", 1)
