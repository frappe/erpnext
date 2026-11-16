from collections import defaultdict

import frappe

SCRAP_TABLES = (
	("BOM Scrap Item", "BOM Secondary Item", ("item_code", "stock_qty")),
	("Job Card Scrap Item", "Job Card Secondary Item", ("item_code", "stock_qty")),
	(
		"Subcontracting Inward Order Scrap Item",
		"Subcontracting Inward Order Secondary Item",
		("item_code", "fg_item_code", "warehouse", "reference_name"),
	),
)


def execute():
	"""Copy idx of the old scrap rows to the secondary rows co_by_product_patch made from them."""
	for old_doctype, new_doctype, keys in SCRAP_TABLES:
		if frappe.db.has_table(old_doctype):
			set_idx(old_doctype, new_doctype, keys)


def set_idx(old_doctype, new_doctype, keys):
	old_rows = defaultdict(list)
	for row in get_old_rows(old_doctype, keys):
		old_rows[get_key(row, keys)].append(row)

	updates = {}
	for row in frappe.get_all(new_doctype, fields=["name", "parent", "idx", *keys]):
		if not (matches := old_rows.get(get_key(row, keys))):
			continue

		old_row = matches.pop(0)
		# Rows of a document submitted before the upgrade cannot have been reordered since.
		if not row.idx or old_row.docstatus == 1:
			updates[row.name] = {"idx": old_row.idx}

	frappe.db.bulk_update(new_doctype, updates, update_modified=False)


def get_old_rows(old_doctype, keys):
	# The old DocType record may be gone, so read its table directly.
	table = frappe.qb.DocType(old_doctype)
	return (
		frappe.qb.from_(table)
		.select(table.parent, table.idx, table.docstatus, *(table[key] for key in keys))
		.orderby(table.idx)
		.run(as_dict=True)
	)


def get_key(row, keys):
	return (row.parent, *(row[key] for key in keys))
