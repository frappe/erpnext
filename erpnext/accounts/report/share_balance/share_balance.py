# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Compatibility report: balances now come from the share ledger."""

import frappe
from frappe import _

from erpnext.accounts.report.equity_position.equity_position import get_columns, get_data


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("date"):
		frappe.throw(_("Please select date"))
	filters.as_of_date = filters.date
	return get_columns(), get_data(filters)
