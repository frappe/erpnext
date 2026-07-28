import frappe


def execute():
	"""Carry the `reposted` flag of every voucher over to its new status field."""
	items = frappe.qb.DocType("Repost Accounting Ledger Items")

	for reposted, status in ((1, "Reposted"), (0, "Pending")):
		frappe.qb.update(items).set(items.status, status).where(items.reposted == reposted).run()
