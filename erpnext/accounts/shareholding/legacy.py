# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Prevent new ownership postings while old ownership history is incomplete."""

import frappe
from frappe import _
from frappe.utils import cint


def assert_legacy_history_backfilled(company):
	if not frappe.db.table_exists("Share Transfer"):
		return
	if (
		frappe.db.table_exists("Share Balance")
		and not frappe.db.table_exists("Shareholding Legacy Balance Staging")
		and frappe.db.exists("Share Balance", {"parenttype": "Shareholder"})
	):
		frappe.throw(_("Legacy Share Balance rows were not staged for migration."))

	expected = cint(
		frappe.db.sql(
			"""
			select coalesce(sum(case when transfer_type = 'Transfer' then 2 else 1 end), 0)
			from `tabShare Transfer`
			where company = %s and docstatus = 1
			""",
			(company,),
		)[0][0]
	)
	if not expected:
		if (
			frappe.db.table_exists("Shareholding Legacy Staging")
			and frappe.db.table_exists("Shareholding Legacy Balance Staging")
			and frappe.db.sql(
				"""
				select balance.name
				from `tabShareholding Legacy Balance Staging` balance
				inner join `tabShareholding Legacy Staging` holder on holder.name = balance.parent
				where holder.company = %s and holder.is_company = 0 and balance.is_company = 0
				limit 1
				""",
				(company,),
			)
		):
			frappe.throw(
				_("Legacy share balances for {0} require an approved opening balance.").format(
					frappe.bold(company)
				)
			)
		return
	posted = frappe.db.count("Share Ledger Entry", {"company": company, "source_doctype": "Share Transfer"})
	if posted != expected:
		frappe.throw(
			_(
				"Legacy Share Transfers for {0} have not been reconciled into the share ledger. "
				"Complete the migration before submitting new Share Transactions."
			).format(frappe.bold(company))
		)
