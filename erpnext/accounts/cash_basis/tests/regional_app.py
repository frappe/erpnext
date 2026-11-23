# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The function of a test regional app. hooks.py maps it for the country "_Test Cash Basis Region".

A real regional app (for example usa_compliance) adds the same entry to its own hooks.py.
"""

import frappe


def get_accounting_method_advisories(company: str) -> list[dict]:
	# allow_regional finds the country from frappe.flags.company, so the caller has set it.
	return [
		{
			"title": "Test advisory",
			"message": f"Regional advice for {company}, flag {frappe.flags.company}",
			"indicator": "orange",
		}
	]
