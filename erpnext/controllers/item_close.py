# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Row level close and reopen for transaction items.

`REOPEN_STATUS` holds, per closable parent, the status its own Re-open button
passes to `update_status`. `set_status` recomputes from `status_map` anyway, so
the value is mostly a sentinel for "clear the Closed override" -- but not
always: Sales Order re-checks the credit limit only on the literal "Draft".
Reusing each doctype's own value keeps reopening a row indistinguishable from
reopening the document by hand.
"""

import frappe
from frappe import _
from frappe.utils import cint

REOPEN_STATUS = {
	"Purchase Order": "Submitted",
	"Sales Order": "Draft",
	"Delivery Note": "Submitted",
	"Purchase Receipt": "Submitted",
}

SETTLED_BY_CLOSE = ("per_ordered", "per_received", "per_delivered", "per_billed")


def has_closable_items(doctype: str | None) -> bool:
	return doctype in REOPEN_STATUS


def closed_rows_settle(parent_doctype: str, item_doctype: str, percentage_field: str) -> bool:
	"""Whether closed rows count as fully settled for this progress field.

	Returns are excluded: closing a row writes off what is still pending on it,
	it does not turn the row into a return.
	"""
	return (
		percentage_field in SETTLED_BY_CLOSE
		and has_closable_items(parent_doctype)
		and frappe.get_meta(item_doctype).has_field("closed")
	)


@frappe.whitelist()
def update_closed_status(doctype: str, name: str, item_names: str | list[str], closed: int) -> None:
	if not has_closable_items(doctype):
		frappe.throw(_("Rows of {0} cannot be closed individually").format(_(doctype)))

	closed = 1 if cint(closed) else 0
	item_names = set(frappe.parse_json(item_names) or [])
	if not item_names:
		frappe.throw(_("Select at least one row"))

	doc = frappe.get_lazy_doc(doctype, name, check_permission="submit")
	if doc.docstatus != 1:
		frappe.throw(_("{0} {1} is not submitted").format(_(doctype), name))

	changed = [row for row in doc.items if row.name in item_names and cint(row.closed) != closed]
	if not changed:
		return

	if closed:
		settled = [row for row in changed if not doc.is_item_closable(row)]
		if settled:
			frappe.throw(
				_("Row #{0}: {1} is already completed in full, so there is nothing to close").format(
					settled[0].idx, frappe.bold(settled[0].item_code)
				)
			)

		validate_rows = getattr(doc, "validate_item_close", None)
		if validate_rows:
			validate_rows(changed)

	for row in changed:
		row.db_set("closed", closed)

	doc.on_item_close_status_change()
	doc.reload()

	if closed:
		close_parent_if_fully_closed(doc)
	else:
		reopen_parent_if_closed(doc)

	doc.notify_update()


def close_parent_if_fully_closed(doc) -> None:
	"""Close the parent once every row has been closed."""
	if doc.status == "Closed":
		return

	if all(cint(row.closed) for row in doc.items):
		doc.update_status("Closed")


def reopen_parent_if_closed(doc) -> None:
	"""Reopen the parent so the row that was just reopened can be acted on.

	A closed parent suppresses its rows everywhere, so leaving it closed would
	make reopening a row look like it did nothing.
	"""
	if doc.status == "Closed":
		doc.update_status(REOPEN_STATUS[doc.doctype])


def is_bundle_of_closed_row(packed_item) -> bool:
	"""A packed item follows the row of its parent document that bundles it."""
	if not packed_item.parent_detail_docname or not packed_item.parenttype:
		return False

	item_doctype = f"{packed_item.parenttype} Item"

	return bool(frappe.db.get_value(item_doctype, packed_item.parent_detail_docname, "closed"))


def clear_closed_rows_on_amend(doc) -> None:
	"""An amended document starts with nothing written off.

	Frappe copies `no_copy` fields when amending so a cancelled document can be
	corrected and resubmitted, which would otherwise carry a write-off decision
	that was made against the cancelled document onto the new one.
	"""
	if not doc.is_new() or not doc.get("amended_from") or not has_closable_items(doc.doctype):
		return

	for row in doc.get("items") or []:
		row.closed = 0


def validate_parent_reopen(doc) -> None:
	"""Block reopening a parent whose rows are all closed.

	It would read as open while every row stayed suppressed. Reopening the rows
	is the way back, and that reopens the parent on its own.
	"""
	rows = doc.get("items") or []
	if rows and all(cint(row.get("closed")) for row in rows):
		frappe.throw(
			_("Every row of {0} is closed. Reopen the rows you need instead, using {1}.").format(
				frappe.bold(doc.name), frappe.bold(_("Reopen Items"))
			)
		)
