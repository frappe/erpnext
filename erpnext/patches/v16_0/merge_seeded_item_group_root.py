import frappe
from frappe.utils.nestedset import get_root_of

SEEDED_ROOT = "All Item Groups"


def execute():
	"""Collapse the "All Item Groups" node seeded under a pre-existing root.

	Setup seeding always inserted "All Item Groups" as a parentless group. On a
	site where another app had already created the root (under a translated
	name), it was re-parented instead, leaving a second group-root holding the
	standard Item Groups.
	"""
	root = get_root_of("Item Group")
	if not root or root == SEEDED_ROOT:
		return

	seeded = frappe.db.get_value("Item Group", SEEDED_ROOT, ["parent_item_group", "is_group"], as_dict=True)
	if not seeded or not seeded.is_group or seeded.parent_item_group != root:
		return

	frappe.rename_doc("Item Group", SEEDED_ROOT, root, merge=True, show_alert=False)
