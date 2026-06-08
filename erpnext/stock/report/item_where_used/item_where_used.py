# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

WHERE_USED_SECTION = "Where Used"
REFERENCES_SECTION = "References"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()

	if not filters.get("item"):
		return columns, []

	return columns, get_data(filters)


def get_columns():
	return [
		{
			"fieldname": "section",
			"label": _("Section"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "reference_type",
			"label": _("Reference Type"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "document_type",
			"label": _("Document Type"),
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"fieldname": "document_name",
			"label": _("Document"),
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 220,
		},
		{
			"fieldname": "related_item",
			"label": _("Related Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 180,
		},
		{
			"fieldname": "matched_field",
			"label": _("Matched Field"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "row_index",
			"label": _("Row"),
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"fieldname": "quantity",
			"label": _("Qty"),
			"fieldtype": "Float",
			"width": 90,
		},
		{
			"fieldname": "uom",
			"label": _("UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
		{
			"fieldname": "stock_quantity",
			"label": _("Stock Qty"),
			"fieldtype": "Float",
			"width": 100,
		},
		{
			"fieldname": "stock_uom",
			"label": _("Stock UOM"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 110,
		},
		{
			"fieldname": "company",
			"label": _("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 160,
		},
		{
			"fieldname": "is_default",
			"label": _("Default"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "is_active",
			"label": _("Active"),
			"fieldtype": "Check",
			"width": 80,
		},
		{
			"fieldname": "disabled",
			"label": _("Disabled"),
			"fieldtype": "Check",
			"width": 90,
		},
		{
			"fieldname": "details",
			"label": _("Details"),
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data(filters):
	data = []

	if not filters.get("section") or filters.section == WHERE_USED_SECTION:
		data.extend(get_where_used_data(filters))

	if not filters.get("section") or filters.section == REFERENCES_SECTION:
		data.extend(get_reference_data(filters))

	return data


def get_where_used_data(filters):
	item = filters.item
	data = []

	data.extend(get_bom_component_rows(item, filters.get("company")))
	data.extend(get_product_bundle_component_rows(item))
	data.extend(get_bom_secondary_item_rows(item, filters.get("company")))
	data.extend(get_subcontracting_bom_rows(item))

	return data


def get_reference_data(filters):
	item = filters.item
	data = []

	data.extend(get_bom_output_rows(item, filters.get("company")))
	data.extend(get_product_bundle_parent_rows(item))
	data.extend(get_variant_rows(item))
	data.extend(get_item_alternative_rows(item))

	return data


def get_bom_component_rows(item, company=None):
	rows = frappe.get_all(
		"BOM Item",
		filters={"item_code": item, "parenttype": "BOM", "docstatus": 1},
		fields=["parent", "idx", "qty", "uom", "stock_qty", "stock_uom", "bom_no"],
		order_by="parent asc, idx asc",
	)
	bom_map = get_bom_map([row.parent for row in rows], company)

	data = []
	for row in rows:
		if bom := bom_map.get(row.parent):
			data.append(
				build_row(
					section=WHERE_USED_SECTION,
					reference_type=_("BOM Component"),
					document_type="BOM",
					document_name=row.parent,
					related_item=bom.item,
					matched_field="BOM Item.item_code",
					row_index=row.idx,
					quantity=row.qty,
					uom=row.uom,
					stock_quantity=row.stock_qty,
					stock_uom=row.stock_uom,
					company=bom.company,
					is_default=bom.is_default,
					is_active=bom.is_active,
					details=row.bom_no,
				)
			)

	return data


def get_bom_secondary_item_rows(item, company=None):
	rows = frappe.get_all(
		"BOM Secondary Item",
		filters={"item_code": item, "parenttype": "BOM", "docstatus": 1},
		fields=["parent", "idx", "type", "qty", "uom", "stock_qty", "stock_uom"],
		order_by="parent asc, idx asc",
	)
	bom_map = get_bom_map([row.parent for row in rows], company)

	data = []
	for row in rows:
		if bom := bom_map.get(row.parent):
			data.append(
				build_row(
					section=WHERE_USED_SECTION,
					reference_type=_("BOM Secondary Item"),
					document_type="BOM",
					document_name=row.parent,
					related_item=bom.item,
					matched_field="BOM Secondary Item.item_code",
					row_index=row.idx,
					quantity=row.qty,
					uom=row.uom,
					stock_quantity=row.stock_qty,
					stock_uom=row.stock_uom,
					company=bom.company,
					is_default=bom.is_default,
					is_active=bom.is_active,
					details=row.type,
				)
			)

	return data


def get_bom_output_rows(item, company=None):
	filters = {"item": item, "docstatus": 1}
	if company:
		filters["company"] = company

	rows = frappe.get_all(
		"BOM",
		filters=filters,
		fields=["name", "item", "company", "is_default", "is_active", "quantity", "uom"],
		order_by="is_default desc, name asc",
	)

	return [
		build_row(
			section=REFERENCES_SECTION,
			reference_type=_("BOM Output"),
			document_type="BOM",
			document_name=row.name,
			related_item=row.item,
			matched_field="BOM.item",
			quantity=row.quantity,
			uom=row.uom,
			company=row.company,
			is_default=row.is_default,
			is_active=row.is_active,
		)
		for row in rows
	]


def get_product_bundle_component_rows(item):
	rows = frappe.get_all(
		"Product Bundle Item",
		filters={"item_code": item, "parenttype": "Product Bundle", "docstatus": 0},
		fields=["parent", "idx", "qty", "uom"],
		order_by="parent asc, idx asc",
	)
	bundle_map = get_product_bundle_map([row.parent for row in rows])

	data = []
	for row in rows:
		if bundle := bundle_map.get(row.parent):
			data.append(
				build_row(
					section=WHERE_USED_SECTION,
					reference_type=_("Product Bundle Component"),
					document_type="Product Bundle",
					document_name=row.parent,
					related_item=bundle.new_item_code,
					matched_field="Product Bundle Item.item_code",
					row_index=row.idx,
					quantity=row.qty,
					uom=row.uom,
					is_active=0 if bundle.disabled else 1,
					disabled=bundle.disabled,
				)
			)

	return data


def get_product_bundle_parent_rows(item):
	rows = frappe.get_all(
		"Product Bundle",
		filters={"new_item_code": item, "disabled": 0, "docstatus": 0},
		fields=["name", "new_item_code", "disabled"],
		order_by="name asc",
	)

	return [
		build_row(
			section=REFERENCES_SECTION,
			reference_type=_("Product Bundle Parent"),
			document_type="Product Bundle",
			document_name=row.name,
			related_item=row.new_item_code,
			matched_field="Product Bundle.new_item_code",
			is_active=0 if row.disabled else 1,
			disabled=row.disabled,
		)
		for row in rows
	]


def get_subcontracting_bom_rows(item):
	data = []

	for row in frappe.get_all(
		"Subcontracting BOM",
		filters={"service_item": item},
		fields=[
			"name",
			"is_active",
			"finished_good",
			"service_item",
			"service_item_qty",
			"service_item_uom",
		],
		order_by="finished_good asc, name asc",
	):
		data.append(
			build_row(
				section=WHERE_USED_SECTION,
				reference_type=_("Subcontracting Service Item"),
				document_type="Subcontracting BOM",
				document_name=row.name,
				related_item=row.finished_good,
				matched_field="Subcontracting BOM.service_item",
				quantity=row.service_item_qty,
				uom=row.service_item_uom,
				is_active=row.is_active,
			)
		)

	for row in frappe.get_all(
		"Subcontracting BOM",
		filters={"finished_good": item},
		fields=[
			"name",
			"is_active",
			"finished_good",
			"finished_good_qty",
			"finished_good_uom",
		],
		order_by="name asc",
	):
		data.append(
			build_row(
				section=WHERE_USED_SECTION,
				reference_type=_("Subcontracting Finished Good"),
				document_type="Subcontracting BOM",
				document_name=row.name,
				related_item=row.finished_good,
				matched_field="Subcontracting BOM.finished_good",
				quantity=row.finished_good_qty,
				uom=row.finished_good_uom,
				is_active=row.is_active,
			)
		)

	return data


def get_variant_rows(item):
	rows = frappe.get_all(
		"Item",
		filters={"variant_of": item},
		fields=["name", "variant_of", "disabled"],
		order_by="name asc",
	)

	return [
		build_row(
			section=REFERENCES_SECTION,
			reference_type=_("Item Variant"),
			document_type="Item",
			document_name=row.name,
			related_item=row.name,
			matched_field="Item.variant_of",
			disabled=row.disabled,
		)
		for row in rows
	]


def get_item_alternative_rows(item):
	data = []

	for row in frappe.get_all(
		"Item Alternative",
		filters={"item_code": item},
		fields=["name", "item_code", "alternative_item_code"],
		order_by="alternative_item_code asc",
	):
		data.append(
			build_row(
				section=REFERENCES_SECTION,
				reference_type=_("Item Alternative"),
				document_type="Item Alternative",
				document_name=row.name,
				related_item=row.alternative_item_code,
				matched_field="Item Alternative.item_code",
			)
		)

	for row in frappe.get_all(
		"Item Alternative",
		filters={"alternative_item_code": item},
		fields=["name", "item_code", "alternative_item_code"],
		order_by="item_code asc",
	):
		data.append(
			build_row(
				section=REFERENCES_SECTION,
				reference_type=_("Alternative For Item"),
				document_type="Item Alternative",
				document_name=row.name,
				related_item=row.item_code,
				matched_field="Item Alternative.alternative_item_code",
			)
		)

	return data


def get_bom_map(bom_names, company=None):
	bom_names = get_unique_names(bom_names)
	if not bom_names:
		return {}

	filters = {"name": ["in", bom_names], "docstatus": 1}
	if company:
		filters["company"] = company

	return {
		row.name: row
		for row in frappe.get_all(
			"BOM",
			filters=filters,
			fields=["name", "item", "company", "is_default", "is_active"],
		)
	}


def get_product_bundle_map(bundle_names):
	bundle_names = get_unique_names(bundle_names)
	if not bundle_names:
		return {}

	return {
		row.name: row
		for row in frappe.get_all(
			"Product Bundle",
			filters={"name": ["in", bundle_names], "disabled": 0, "docstatus": 0},
			fields=["name", "new_item_code", "disabled"],
		)
	}


def build_row(**kwargs):
	return frappe._dict(kwargs)


def get_unique_names(names):
	unique_names = []
	seen = set()

	for name in names:
		if not name or name in seen:
			continue

		seen.add(name)
		unique_names.append(name)

	return unique_names
