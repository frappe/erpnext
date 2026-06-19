import frappe

from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

ENTRY_DOCTYPE = "Inventory Dimension Entry"
LAYOUT_FIELDS = ("inventory_dimension", "inventory_dimension_col_break")


def execute():
	"""Remove the legacy per-dimension custom fields once data is on the sub-ledger.

	The old design scattered a Link field (+ ``to_`` / ``from_`` / ``rejected_`` variants and a
	section/column break) across every stock doctype + Stock Ledger Entry per dimension. After
	``migrate_inventory_dimensions_to_bundles`` reconstructs the quantity sub-ledger, those fields
	are redundant. We only delete the **Custom Field** definitions, identified by their original
	structure, so we never touch a standard field (e.g. the core ``project`` field), a legitimate
	user custom field of the same name, or the new ``Inventory Dimension Entry`` column. The
	physical columns are left as harmless orphans (the data also lives in the sub-ledger).
	"""
	legacy = [
		d for d in get_inventory_dimensions() if frappe.db.has_column("Stock Ledger Entry", d.fieldname)
	]
	if not legacy:
		return

	all_confirmed = True
	for dimension in legacy:
		if not backfill_confirmed(dimension):
			all_confirmed = False
			continue

		for name in get_legacy_custom_fields(dimension):
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)

	# The shared section / column break were created once per doctype and reused by every
	# dimension, so only remove them after every dimension has been migrated.
	if all_confirmed:
		for name in get_layout_custom_fields():
			frappe.delete_doc("Custom Field", name, ignore_permissions=True)


def backfill_confirmed(dimension) -> bool:
	"""True when no live SLE carries this dimension's value without a bundle (backfill complete)."""
	column = dimension.fieldname
	if not frappe.db.has_column("Stock Ledger Entry", column):
		return True

	sle = frappe.qb.DocType("Stock Ledger Entry")
	unlinked = (
		frappe.qb.from_(sle)
		.select(sle.name)
		.where(sle.is_cancelled == 0)
		.where(sle[column].isnotnull() & (sle[column] != ""))
		.where(sle.inventory_dimension_bundle.isnull() | (sle.inventory_dimension_bundle == ""))
		.limit(1)
		.run()
	)
	return not unlinked


def get_legacy_custom_fields(dimension) -> list[str]:
	"""Custom Field names created by the old dimension flow for this dimension (structurally matched)."""
	source = dimension.source_fieldname
	reference = dimension.doctype  # get_inventory_dimensions aliases reference_document -> doctype
	names = []

	# Main Link field on the transaction doctypes + SLE / Stock Closing Balance. The new sub-ledger
	# column is excluded because it sits after `warehouse`, not after the `inventory_dimension` break.
	for row in frappe.get_all(
		"Custom Field",
		filters={"fieldname": source, "options": reference, "insert_after": "inventory_dimension"},
		fields=["name", "dt"],
	):
		if row.dt != ENTRY_DOCTYPE:
			names.append(row.name)

	# Inward/outward transfer variants.
	names += frappe.get_all(
		"Custom Field",
		filters={
			"fieldname": ("in", [f"to_{source}", f"from_{source}"]),
			"options": reference,
			"insert_after": "inventory_dimension_col_break",
		},
		pluck="name",
	)

	# Rejected-warehouse variant.
	names += frappe.get_all(
		"Custom Field",
		filters={"fieldname": f"rejected_{source}", "options": reference, "insert_after": source},
		pluck="name",
	)

	return names


def get_layout_custom_fields() -> list[str]:
	return frappe.get_all(
		"Custom Field",
		filters={"fieldname": ("in", LAYOUT_FIELDS), "fieldtype": ("in", ["Section Break", "Column Break"])},
		pluck="name",
	)
