"""Migrate Product Bundles to the submittable, versioned model (issue #29462).

Pre-existing bundles were editable drafts named after their parent item
(``name == new_item_code``). This patch:

1. renames each legacy bundle to the versioned name ``PB-<parent item>-001``,
   marks it submitted (``docstatus = 1``) and seeds ``is_active`` from the legacy
   ``disabled`` flag (active = not disabled), and
2. stamps the resolved version onto existing transaction rows, so documents keep a
   reference to the exact bundle version they were packed from.

Both steps ship together (v16 is unreleased), so they are a single migration. No
transaction stores a bundle's *name* (they snapshot components and reference the
parent item code), so renaming is reference-safe. The whole patch is idempotent.
"""

import frappe

from erpnext.selling.doctype.product_bundle.product_bundle import NAME_PREFIX, build_bundle_name

# doctype -> column holding the bundle parent item code
SELLING_ITEM_TABLES = {
	"Sales Order Item": "item_code",
	"Delivery Note Item": "item_code",
	"Sales Invoice Item": "item_code",
	"POS Invoice Item": "item_code",
	"Quotation Item": "item_code",
	"Packed Item": "parent_item",
}

BUYING_ITEM_TABLES = ["Purchase Order Item", "Purchase Invoice Item", "Purchase Receipt Item"]


def execute():
	submit_existing_bundles()
	stamp_versions_on_transactions()


def submit_existing_bundles():
	legacy_bundles = frappe.get_all(
		"Product Bundle",
		filters={"docstatus": 0},
		fields=["name", "new_item_code", "disabled"],
		order_by="creation asc",
	)

	for bundle in legacy_bundles:
		# Submitted bundles are already migrated and excluded by the docstatus filter.
		# A draft that still carries its legacy name needs renaming; a draft already
		# named PB-* is the leftover of an interrupted run and only needs submitting.
		target_name = bundle.name

		if not bundle.name.startswith(f"{NAME_PREFIX}-"):
			new_name = build_bundle_name(bundle.new_item_code, _next_index(bundle.new_item_code))
			if not frappe.db.exists("Product Bundle", new_name):
				frappe.rename_doc(
					"Product Bundle", bundle.name, new_name, force=True, merge=False, show_alert=False
				)
				target_name = new_name

		frappe.db.set_value(
			"Product Bundle",
			target_name,
			{"docstatus": 1, "is_active": 0 if bundle.disabled else 1},
			update_modified=False,
		)

	_enforce_single_active_version()


def stamp_versions_on_transactions():
	"""Backfill the ``product_bundle`` version link onto existing transaction rows.

	- Selling / packed rows: a row whose item is a bundle parent is stamped with that
	  bundle's version (the field was newly added, so only blank rows are touched) and
	  flagged via ``is_product_bundle`` so the version field stays visible.
	- Buying rows: the ``product_bundle`` field previously stored the parent *item code*;
	  convert those legacy values to the bundle version name. Idempotent: once converted,
	  the value is a bundle name and no longer matches a ``new_item_code``.
	"""
	# parent item code -> migrated bundle version name (active version preferred)
	version_by_item = {}
	for bundle in frappe.get_all(
		"Product Bundle",
		filters={"docstatus": 1},
		fields=["name", "new_item_code"],
		order_by="is_active desc, creation asc",
	):
		version_by_item.setdefault(bundle.new_item_code, bundle.name)

	if not version_by_item:
		return

	for doctype, item_field in SELLING_ITEM_TABLES.items():
		if not frappe.db.has_column(doctype, "product_bundle"):
			continue
		table = frappe.qb.DocType(doctype)
		item_column = getattr(table, item_field)
		flag_bundle_rows = frappe.db.has_column(doctype, "is_product_bundle")
		for item_code, version in version_by_item.items():
			(
				frappe.qb.update(table)
				.set(table.product_bundle, version)
				.where(
					(item_column == item_code)
					& ((table.product_bundle.isnull()) | (table.product_bundle == ""))
				)
			).run()
			if flag_bundle_rows:
				# keep the version field visible on bundle rows even if its value is cleared
				(
					frappe.qb.update(table).set(table.is_product_bundle, 1).where(item_column == item_code)
				).run()

	for doctype in BUYING_ITEM_TABLES:
		if not frappe.db.has_column(doctype, "product_bundle"):
			continue
		table = frappe.qb.DocType(doctype)
		for item_code, version in version_by_item.items():
			# only legacy rows still holding the item code are matched
			(
				frappe.qb.update(table)
				.set(table.product_bundle, version)
				.where(table.product_bundle == item_code)
			).run()


def _next_index(item_code: str) -> int:
	"""Next free version index for a parent item among already-migrated bundles."""
	existing = frappe.get_all(
		"Product Bundle",
		filters={"new_item_code": item_code, "name": ("like", f"{NAME_PREFIX}-%")},
		pluck="name",
	)
	from erpnext.selling.doctype.product_bundle.product_bundle import get_next_version_index

	return get_next_version_index(existing)


def _enforce_single_active_version():
	"""Guarantee at most one active version per parent item.

	Under the old unique-name-per-item invariant duplicates can't exist, so this is a
	safety net; if several are somehow active, keep the most recently created one.
	"""
	active = frappe.get_all(
		"Product Bundle",
		filters={"is_active": 1, "docstatus": 1},
		fields=["name", "new_item_code"],
		order_by="new_item_code asc, creation desc",
	)

	seen = set()
	for bundle in active:
		if bundle.new_item_code in seen:
			# a newer version for this item was already kept; deactivate the rest
			frappe.db.set_value("Product Bundle", bundle.name, "is_active", 0, update_modified=False)
		else:
			seen.add(bundle.new_item_code)
