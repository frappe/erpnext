# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Populate the Shareholder child-table projection from existing ledger entries."""

import frappe

from erpnext.accounts.doctype.shareholder.shareholder import rebuild_current_holdings


def execute():
	shareholders = {
		folio.shareholder
		for folio in frappe.get_all(
			"Share Folio", filters={"is_treasury": 0}, fields=["shareholder"], limit_page_length=0
		)
		if folio.shareholder
	}
	for shareholder in sorted(shareholders):
		rebuild_current_holdings(shareholder)
