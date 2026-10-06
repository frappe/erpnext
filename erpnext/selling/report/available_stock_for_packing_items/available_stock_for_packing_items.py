# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions
from frappe.query_builder.functions import Sum
from frappe.utils import floor, flt


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns()
	iwq_map = get_item_warehouse_quantity_map()
	item_map = get_item_details(list(iwq_map.keys()))
	data = []
	for sbom, warehouse in iwq_map.items():
		total = 0
		total_qty = 0

		for wh, item_qty in warehouse.items():
			total += 1
			if item_map.get(sbom):
				row = [
					sbom,
					item_map.get(sbom).item_name,
					item_map.get(sbom).description,
					item_map.get(sbom).stock_uom,
					wh,
				]
				available_qty = item_qty
				total_qty += flt(available_qty)
				row += [available_qty]

				if available_qty:
					data.append(row)
					if total == len(warehouse):
						row = ["", "", "Total", "", "", total_qty]
						data.append(row)
	return columns, data


def get_columns():
	columns = [
		"Item Code:Link/Item:100",
		"Item Name::100",
		"Description::120",
		"UOM:Link/UOM:80",
		"Warehouse:Link/Warehouse:100",
		"Quantity::100",
	]

	return columns


def get_item_details(item_codes):
	if not item_codes:
		return {}
	item_map = {}
	for item in frappe.get_all(
		"Item",
		filters={"name": ["in", item_codes]},
		fields=["name", "item_name", "description", "stock_uom"],
	):
		item_map.setdefault(item.name, item)
	return item_map


def get_item_warehouse_quantity_map():
	pb = frappe.qb.DocType("Product Bundle")
	pbi = frappe.qb.DocType("Product Bundle Item")
	bundle_components = (
		frappe.qb.from_(pbi)
		.inner_join(pb)
		.on(pbi.parent == pb.name)
		.select(pb.new_item_code.as_("parent"), pbi.item_code, Sum(pbi.qty).as_("qty"))
		.where(pb.disabled == 0)
		.groupby(pb.new_item_code, pbi.item_code)
		.run(as_dict=True)
	)

	if not bundle_components:
		return {}

	component_items = list({c.item_code for c in bundle_components})

	bin_projected = {
		(b.item_code, b.warehouse): flt(b.projected_qty) for b in get_component_bins(component_items)
	}

	bin_warehouses = {wh for (_, wh) in bin_projected}

	# packable bundles per (bundle, warehouse) = MIN over components of projected_qty / qty per bundle
	packable_qty = {}
	for component in bundle_components:
		if not component.qty:
			continue
		for warehouse in bin_warehouses:
			qty = bin_projected.get((component.item_code, warehouse), 0) / flt(component.qty)
			key = (component.parent, warehouse)
			packable_qty[key] = min(packable_qty[key], qty) if key in packable_qty else qty

	sbom_map = {}
	for (parent, warehouse), qty in packable_qty.items():
		# round off float-division noise, then floor to whole, non-negative bundles
		bundles = max(0, floor(flt(qty, 9)))
		if bundles:
			sbom_map.setdefault(parent, {})[warehouse] = bundles

	return sbom_map


def get_component_bins(component_items):
	bin_table = frappe.qb.DocType("Bin")
	query = (
		frappe.qb.from_(bin_table)
		.select(bin_table.item_code, bin_table.warehouse, bin_table.projected_qty)
		.where(bin_table.item_code.isin(component_items))
	)

	if warehouses := get_user_permitted_warehouses():
		query = query.where(bin_table.warehouse.isin(warehouses))

	return query.run(as_dict=True)


def get_user_permitted_warehouses():
	# Warehouse user permissions that apply to Bin; an empty set means no restriction, matching how
	# Frappe itself scopes link fields by User Permission (applicable_for)
	warehouse_permissions = get_user_permissions(frappe.session.user).get("Warehouse") or []
	return get_allowed_docs_for_doctype(warehouse_permissions, "Bin")
