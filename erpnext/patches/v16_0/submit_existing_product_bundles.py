"""Make existing Product Bundles submittable & versioned.

Product Bundle became a submittable, versioned doctype (issue #29462). Pre-existing
bundles were drafts named after their parent item (``name == new_item_code``). This
patch migrates them to the new model:

1. rename each legacy bundle to the versioned name ``PB-<parent item>-001``
2. mark it submitted (``docstatus = 1``)
3. seed ``is_active`` from the legacy ``disabled`` flag (active = not disabled)

No transaction stores a bundle's *name* (they snapshot components into their own
``packed_items`` tables and reference the parent item code), so renaming is
reference-safe. The patch is idempotent: already-migrated bundles (docstatus != 0 or
already prefixed) are skipped.
"""

import frappe

from erpnext.selling.doctype.product_bundle.product_bundle import NAME_PREFIX, build_bundle_name


def execute():
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
