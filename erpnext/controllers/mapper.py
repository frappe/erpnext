# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import flt


def get_qty_already_mapped(target_doc, ref_field: str, qty_field: str = "qty") -> frappe._dict:
	"""Return a map: {source row name: qty} of rows already mapped into the target document.

	"Get Items From" passes the in-progress (unsaved) document back as `target_doc`. Its rows
	are invisible to the pending-qty queries in the mappers, which only count submitted
	documents -- so without this, selecting the same source document twice maps every row
	again. Rows are keyed by `ref_field` (dn_detail, so_detail, ...), and a row is present in
	the map even when its qty is 0, so mappers without qty tracking can dedupe on presence.
	"""
	if isinstance(target_doc, str):
		target_doc = frappe.parse_json(target_doc)

	qty_map = frappe._dict()
	for row in (target_doc and target_doc.get("items")) or []:
		if ref := row.get(ref_field):
			qty_map[ref] = qty_map.get(ref, 0) + flt(row.get(qty_field))

	return qty_map
