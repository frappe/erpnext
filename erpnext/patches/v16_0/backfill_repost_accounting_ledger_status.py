import frappe
from frappe.query_builder.functions import Coalesce


def execute():
	"""Backfill `status` on documents that were reposted before the field existed.

	Without this, older documents show up as `Draft` in the list view and are offered a
	`Start Reposting` button, which would repost vouchers that are already reposted.
	"""
	ral = frappe.qb.DocType("Repost Accounting Ledger")
	items = frappe.qb.DocType("Repost Accounting Ledger Items")

	for docstatus, status in ((1, "Completed"), (2, "Cancelled")):
		names = (
			frappe.qb.from_(ral)
			.select(ral.name)
			.where((ral.docstatus == docstatus) & (Coalesce(ral.status, "") == ""))
			.run(pluck=True)
		)

		if not names:
			continue

		frappe.qb.update(ral).set(ral.status, status).where(ral.name.isin(names)).run()

		if status == "Completed":
			frappe.qb.update(items).set(items.reposted, 1).where(items.parent.isin(names)).run()
