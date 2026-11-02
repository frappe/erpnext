from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.manufacturing.doctype.production_plan.services.planning_queries import get_uom_conversion_factor


class PlantFloorPlanning:
	def __init__(self, doc):
		self.doc = doc

	def validate(self):
		plant_floors = {}
		for row in self.doc.po_items:
			if not row.is_plant_floor_item:
				continue

			if row.plant_floor not in plant_floors:
				plant_floors[row.plant_floor] = self.get_valid_plant_floor(row.plant_floor)

			plant_floor = plant_floors[row.plant_floor]
			self.validate_production_item(row, plant_floor)
			row.warehouse = plant_floor.fg_warehouse

	def get_valid_plant_floor(self, name):
		plant_floor = frappe.get_doc("Plant Floor", name)
		if plant_floor.company and plant_floor.company != self.doc.company:
			frappe.throw(
				_("Plant Floor {0} belongs to company {1}, not {2}").format(
					frappe.bold(name), frappe.bold(plant_floor.company), frappe.bold(self.doc.company)
				)
			)

		if errors := plant_floor.setup_errors:
			frappe.throw(errors, title=_("Finish the setup of Plant Floor {0}").format(name), as_list=True)

		return plant_floor

	@staticmethod
	def validate_production_item(row, plant_floor):
		if plant_floor.production_item != row.item_code:
			frappe.throw(
				_("Row #{0}: Plant Floor {1} makes {2}, not {3}").format(
					row.idx,
					frappe.bold(plant_floor.name),
					frappe.bold(plant_floor.production_item),
					frappe.bold(row.item_code),
				)
			)


def get_plant_floor_materials(doc, data, planned_qty):
	plant_floor = frappe.get_doc("Plant Floor", data.get("plant_floor"))
	batch_plan = plant_floor.get_batch_plan(flt(planned_qty))

	quantities = defaultdict(float)
	for row in batch_plan.get_materials() + batch_plan.get_packing_materials():
		quantities[row.item_code] += flt(row.qty)

	materials = get_material_details(list(quantities), doc.get("company"), doc.get("include_non_stock_items"))
	for material in materials:
		material.qty = quantities[material.item_code]
		material.source_warehouse = plant_floor.warehouse
		material.main_bom_item = plant_floor.production_item
		if not material.conversion_factor and material.purchase_uom:
			material.conversion_factor = get_uom_conversion_factor(material.item_code, material.purchase_uom)

	return {material.item_code: material for material in materials}


def get_material_details(item_codes, company, include_non_stock_items):
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	item_uom = frappe.qb.DocType("UOM Conversion Detail")
	query = (
		frappe.qb.from_(item)
		.left_join(item_default)
		.on((item_default.parent == item.name) & (item_default.company == company))
		.left_join(item_uom)
		.on((item_uom.parent == item.name) & (item_uom.uom == item.purchase_uom))
		.select(
			item.name.as_("item_code"),
			item.item_name,
			item.description,
			item.stock_uom,
			item.purchase_uom,
			item.min_order_qty,
			item.safety_stock,
			item.default_material_request_type,
			item.is_sub_contracted_item.as_("is_sub_contracted"),
			item_default.default_warehouse,
			item_uom.conversion_factor,
		)
		.where(item.name.isin(item_codes))
	)
	if not include_non_stock_items:
		query = query.where(item.is_stock_item == 1)

	return query.run(as_dict=True)
