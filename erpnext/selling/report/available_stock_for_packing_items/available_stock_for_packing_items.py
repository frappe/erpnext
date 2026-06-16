# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.utils import flt


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
	# only the bundle items actually shown in the report need detail lookup, not the whole catalogue
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
	# Components of every active product bundle: (bundle item code, component item, qty per bundle)
	pb = frappe.qb.DocType("Product Bundle")
	pbi = frappe.qb.DocType("Product Bundle Item")
	bundle_components = (
		frappe.qb.from_(pbi)
		.inner_join(pb)
		.on(pbi.parent == pb.name)
		.select(pb.new_item_code.as_("parent"), pbi.item_code, pbi.qty)
		.where((pb.is_active == 1) & (pb.docstatus == 1))
		.run(as_dict=True)
	)

	if not bundle_components:
		return {}

	component_items = list({c.item_code for c in bundle_components})

	bin_projected = {
		(b.item_code, b.warehouse): flt(b.projected_qty)
		for b in frappe.get_all(
			"Bin",
			filters={"item_code": ["in", component_items]},
			fields=["item_code", "warehouse", "projected_qty"],
		)
	}

	# Only warehouses that hold at least one component can yield a non-zero packable qty; a warehouse
	# missing any component yields MIN()=0 and is dropped below, so scanning every warehouse in the
	# system is wasted work. Scope the loop to warehouses present in the Bin result.
	bin_warehouses = {wh for (_, wh) in bin_projected}

	# For each (bundle, warehouse) the number of complete bundles that can be packed is the
	# MIN over components of (component projected_qty in that warehouse / component qty per bundle).
	# A component with no Bin in a warehouse contributes 0 (the original UNION ALL/NOT EXISTS branch).
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
		if qty != 0:  # HAVING MIN(qty) != 0
			sbom_map.setdefault(parent, {})[warehouse] = qty

	return sbom_map
