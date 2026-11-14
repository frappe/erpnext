from collections import defaultdict

import frappe

SCRAP_TABLES = (
	("BOM Scrap Item", "BOM Secondary Item", ("item_code", "stock_qty")),
	("Job Card Scrap Item", "Job Card Secondary Item", ("item_code", "stock_qty")),
	(
		"Subcontracting Inward Order Scrap Item",
		"Subcontracting Inward Order Secondary Item",
		("item_code", "fg_item_code", "reference_name"),
	),
)


def execute():
	"""Copy idx of the old scrap rows to secondary rows that co_by_product_patch left at idx 0."""
	for old_doctype, new_doctype, keys in SCRAP_TABLES:
		if frappe.db.has_table(old_doctype):
			set_idx(old_doctype, new_doctype, keys)


def set_idx(old_doctype, new_doctype, keys):
	rows = frappe.get_all(new_doctype, {"idx": 0}, ["name", "parent", *keys])
	if not rows:
		return

	# The old DocType record may be gone, so read its table directly.
	old_table = frappe.qb.Table(f"tab{old_doctype}")
	old_rows = (
		frappe.qb.from_(old_table)
		.select(old_table.parent, old_table.idx, *(old_table[key] for key in keys))
		.where(old_table.docstatus < 2)
		.orderby(old_table.idx)
		.run(as_dict=True)
	)

	old_idx = defaultdict(list)
	for row in old_rows:
		old_idx[get_key(row, keys)].append(row.idx)

	updates = {}
	for row in rows:
		if idx_list := old_idx.get(get_key(row, keys)):
			updates[row.name] = {"idx": idx_list.pop(0)}

	frappe.db.bulk_update(new_doctype, updates, update_modified=False)


def get_key(row, keys):
	return (row.parent, *(row[key] for key in keys))
