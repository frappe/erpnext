from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	if has_default_finance_book() or has_more_than_one_finance_book():
		for company in frappe.get_all("Companies"):
			frappe.db.set_value("Company", company, "enable_finance_books", 1)
	else:
		make_property_setter("Asset Finance Book", "finance_book", "hidden", 1, "Check", validate_fields_for_doctype=False)
		make_property_setter("Depreciation Schedule", "finance_book", "hidden", 1, "Check", validate_fields_for_doctype=False)
		make_property_setter("Journal Entry", "finance_book", "hidden", 1, "Check", validate_fields_for_doctype=False)

def has_default_finance_book():
	return frappe.get_all(
		"Company",
		filters = {
			"default_finance_book": ["not in", None]
		},
		pluck = "default_finance_book"
	)

def has_more_than_one_finance_book():
	if len(frappe.get_all('Finance Book')) > 1:
		return True
	else:
		return False
