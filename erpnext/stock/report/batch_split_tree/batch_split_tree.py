from collections import defaultdict

import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_data(filters):
	roots = get_root_batches(filters)
	if not roots:
		return []

	children_map = get_children_map(roots)

	data = []
	for batch_no in roots:
		add_rows(batch_no, children_map, data, 0)

	return data


def get_root_batches(filters):
	batch = frappe.qb.DocType("Batch")
	child = frappe.qb.DocType("Batch").as_("child")

	if filters.batch:
		return [filters.batch]

	query = (
		frappe.qb.from_(batch)
		.inner_join(child)
		.on(child.parent_batch == batch.name)
		.select(batch.name)
		.distinct()
		.where(batch.parent_batch.isnull())
		.where(child.reference_name.isnotnull() & (child.reference_name != ""))
		.orderby(batch.name)
	)

	if filters.item_code:
		query = query.where(batch.item == filters.item_code)

	return query.run(pluck=True)


def get_children_map(roots):
	batch = frappe.qb.DocType("Batch")
	tree = frappe.qb.Table("batch_split_tree")
	fields = [
		batch.name,
		batch.parent_batch,
		batch.item,
		batch.item_name,
		batch.batch_qty,
		batch.stock_uom,
		batch.reference_doctype,
		batch.reference_name,
		batch.manufacturing_date,
		batch.creation,
	]

	seed = frappe.qb.from_(batch).select(*fields).where(batch.name.isin(roots))
	recursion = (
		frappe.qb.from_(batch)
		.inner_join(tree)
		.on(batch.parent_batch == tree.name)
		.select(*fields)
		.where(batch.reference_name.isnotnull() & (batch.reference_name != ""))
	)

	rows = (
		frappe.qb.with_(seed + recursion, "batch_split_tree", recursive=True).from_(tree).select(tree.star)
	).run(as_dict=True)

	children_map = defaultdict(dict)
	for row in rows:
		children_map[row.parent_batch][row.name] = row

	return children_map


def add_rows(batch_no, children_map, data, indent, batch_details=None):
	if batch_details is None:
		batch_details = get_batch_row(batch_no)

	batch_details.batch_no = batch_no
	batch_details.indent = indent
	data.append(batch_details)

	children = sorted(children_map.get(batch_no, {}).values(), key=lambda row: row.creation)
	for child in children:
		add_rows(child.name, children_map, data, indent + 1, batch_details=child)


def get_batch_row(batch_no):
	return frappe.db.get_value(
		"Batch",
		batch_no,
		[
			"item",
			"item_name",
			"batch_qty",
			"stock_uom",
			"reference_doctype",
			"reference_name",
			"manufacturing_date",
		],
		as_dict=1,
	)


def get_columns():
	return [
		{
			"label": _("Batch"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 260,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 160},
		{"label": _("Batch Qty"), "fieldname": "batch_qty", "fieldtype": "Float", "width": 110},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 100,
		},
		{
			"label": _("Created Via"),
			"fieldname": "reference_doctype",
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"label": _("Reference"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 160,
		},
		{
			"label": _("Manufacturing Date"),
			"fieldname": "manufacturing_date",
			"fieldtype": "Date",
			"width": 130,
		},
	]
