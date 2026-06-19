# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Document-mapping and query helpers for BOM (extracted from bom.py)."""

from functools import partial

import frappe
from frappe import _
from frappe.core.doctype.version.version import get_diff
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder import Field
from frappe.query_builder.functions import IfNull
from frappe.utils import today

from erpnext.stock.doctype.item.item import get_item_details

_BOM_DIFF_IDENTIFIERS = {
	"operations": "operation",
	"items": "item_code",
	"secondary_items": "item_code",
	"exploded_items": "item_code",
}

_VARIANT_BOM_MAPPING = {
	"BOM": {"doctype": "BOM", "validation": {"docstatus": ["=", 1]}},
	"BOM Item": {
		"doctype": "BOM Item",
		# stop get_mapped_doc copying parent bom_no to children
		"field_no_map": ["bom_no"],
		"condition": lambda doc: doc.has_variants == 0,
	},
}


@frappe.whitelist()
def get_children(parent: str | None = None, is_root: bool = False, **filters):
	frappe.has_permission("BOM", "read", throw=True)

	if not parent or parent == "BOM":
		frappe.msgprint(_("Please select a BOM"))
		return

	frappe.form_dict.parent = parent
	bom_doc = frappe.get_cached_doc("BOM", parent)
	frappe.has_permission("BOM", doc=bom_doc, throw=True)

	bom_items = _bom_child_items(parent)
	_enrich_bom_items(bom_items, bom_doc)
	return bom_items


def _bom_child_items(parent):
	return frappe.get_all(
		"BOM Item",
		fields=["item_code", "bom_no as value", "stock_qty", "qty", "is_phantom_item", "bom_no"],
		filters=[["parent", "=", parent]],
		order_by="idx",
	)


def _enrich_bom_items(bom_items, bom_doc):
	item_names = tuple(d.get("item_code") for d in bom_items)
	items = frappe.get_list(
		"Item",
		fields=["image", "description", "name", "stock_uom", "item_name", "is_sub_contracted_item"],
		filters=[["name", "in", item_names]],
	)
	for bom_item in bom_items:
		bom_item.update(next(item for item in items if item.get("name") == bom_item.get("item_code")))
		bom_item.parent_bom_qty = bom_doc.quantity
		bom_item.expandable = 0 if bom_item.value in ("", None) else 1
		bom_item.image = frappe.db.escape(bom_item.image)


@frappe.whitelist()
def get_bom_diff(bom1: str, bom2: str):
	frappe.has_permission("BOM", "read", throw=True)
	if bom1 == bom2:
		frappe.throw(
			_("BOM 1 {0} and BOM 2 {1} should not be same").format(frappe.bold(bom1), frappe.bold(bom2))
		)

	doc1 = frappe.get_doc("BOM", bom1)
	doc2 = frappe.get_doc("BOM", bom2)

	out = get_diff(doc1, doc2)
	out.row_changed, out.added, out.removed = [], [], []
	for df in doc1.meta.fields:
		_diff_table_field(df, doc1, doc2, out)
	return out


def _diff_table_field(df, doc1, doc2, out):
	from frappe.model import table_fields

	if df.fieldtype not in table_fields:
		return

	identifier = _BOM_DIFF_IDENTIFIERS[df.fieldname]
	old_value, new_value = doc1.get(df.fieldname), doc2.get(df.fieldname)
	old_map = {d.get(identifier): d for d in old_value}
	new_map = {d.get(identifier): d for d in new_value}

	_collect_row_changes(df, identifier, old_map, new_value, out)
	for d in old_value:
		if d.get(identifier) not in new_map:
			out.removed.append([df.fieldname, d.as_dict()])


def _collect_row_changes(df, identifier, old_map, new_value, out):
	for i, d in enumerate(new_value):
		if d.get(identifier) not in old_map:
			out.added.append([df.fieldname, d.as_dict()])
			continue

		diff = get_diff(old_map[d.get(identifier)], d, for_child=True)
		if diff and diff.changed:
			out.row_changed.append((df.fieldname, i, d.get(identifier), diff.changed))


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_query(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None
):
	frappe.has_permission("Item", "read", throw=True)

	searchfields = frappe.get_meta("Item", cached=True).get_search_fields()
	fields = ["name", "item_name", "item_group", "description"]
	fields.extend(f for f in searchfields if f not in ["name", "item_group", "description"])

	query_filters = _item_query_filters(filters)
	or_filters = _item_query_or_filters(txt, searchfields or ["name"], query_filters)
	return frappe.get_list(
		"Item",
		fields=fields,
		filters=query_filters,
		or_filters=or_filters,
		order_by="idx desc, name, item_name",
		limit_start=start,
		limit_page_length=page_len,
		as_list=1,
	)


def _item_query_filters(filters):
	query_filters = [["disabled", "=", 0], [IfNull(Field("end_of_life"), "3099-12-31"), ">", today()]]
	if filters and filters.get("item_code"):
		if not frappe.get_cached_value("Item", filters.get("item_code"), "has_variants"):
			query_filters.append(["has_variants", "=", 0])

	for fieldname, value in (filters or {}).items():
		query_filters.append([fieldname, "=", value])
	return query_filters


def _item_query_or_filters(txt, searchfields, query_filters):
	if not txt:
		return {}

	or_filters = {s_field: ("like", f"%{txt}%") for s_field in searchfields}
	barcodes = frappe.get_all(
		"Item Barcode",
		fields=["parent as item_code"],
		filters={"barcode": ("like", f"%{txt}%")},
		distinct=True,
	)
	barcode_codes = [d.item_code for d in barcodes]
	if barcode_codes:
		or_filters["name"] = ("in", barcode_codes)
	return or_filters


@frappe.whitelist()
def make_variant_bom(
	source_name: str,
	bom_no: str,
	item: str,
	variant_items: str | list,
	target_doc: Document | str | None = None,
):
	frappe.has_permission("BOM", "write", throw=True)

	postprocess = partial(
		_postprocess_variant_bom, item=item, variant_items=variant_items, source_name=source_name
	)
	return get_mapped_doc("BOM", source_name, _VARIANT_BOM_MAPPING, target_doc, postprocess)


def _postprocess_variant_bom(source, doc, item, variant_items, source_name):
	from erpnext.manufacturing.doctype.work_order.work_order import add_variant_item

	item_data = get_item_details(item)
	doc.item = item
	doc.quantity = 1
	doc.update(
		{
			"item_name": item_data.item_name,
			"description": item_data.description,
			"uom": item_data.stock_uom,
			"allow_alternative_item": item_data.allow_alternative_item,
		}
	)
	add_variant_item(variant_items, doc, source_name)
