import frappe


def execute():
	"""Index the columns item_query searches, so a leading-wildcard LIKE can use an index.

	PostgreSQL only: add_index ignores `using` on MariaDB, which has no trigram equivalent.
	"""
	if frappe.db.db_type != "postgres":
		return

	for fieldname in ("name", "item_name", "item_group", "customer_code", "description"):
		frappe.db.add_index("Item", [fieldname], index_name=f"item_search_trgm_{fieldname}", using="gin_trgm")
