import frappe
from frappe.query_builder.functions import Coalesce


def execute():
	"""Backfill the statuses of documents reposted before those fields existed.

	Without it they show up as drafts and are offered a `Start Reposting` button that would
	repost vouchers which are already reposted.
	"""
	ral = frappe.qb.DocType("Repost Accounting Ledger")
	items = frappe.qb.DocType("Repost Accounting Ledger Items")

	reposted = (
		frappe.qb.from_(ral).select(ral.name).where((ral.docstatus == 1) & (Coalesce(ral.status, "") == ""))
	)
	frappe.qb.update(items).set(items.status, "Reposted").where(items.parent.isin(reposted)).run()

	for docstatus, status in ((1, "Completed"), (2, "Cancelled")):
		(
			frappe.qb.update(ral)
			.set(ral.status, status)
			.where((ral.docstatus == docstatus) & (Coalesce(ral.status, "") == ""))
			.run()
		)
