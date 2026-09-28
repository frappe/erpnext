from collections import defaultdict

import frappe
from frappe.utils import create_batch


def execute():
	frappe.reload_doc("manufacturing", "doctype", "material_request_plan_item")

	if not frappe.db.has_column("Material Request Plan Item", "main_item_code"):
		return

	for production_plans in create_batch(get_production_plans(), 500):
		MainItemCodeBackfill(production_plans).run()


def get_production_plans():
	return frappe.get_all(
		"Material Request Plan Item",
		filters={"main_item_code": ("is", "not set")},
		pluck="parent",
		distinct=True,
		order_by="parent",
	)


class MainItemCodeBackfill:
	def __init__(self, production_plans):
		self.rows = frappe.get_all(
			"Material Request Plan Item",
			filters={"parent": ("in", production_plans), "main_item_code": ("is", "not set")},
			fields=["name", "parent", "item_code", "sales_order"],
		)
		self.sub_assemblies = get_rows_by_parent(
			"Production Plan Sub Assembly Item",
			production_plans,
			["parent", "production_item", "parent_item_code", "bom_no", "sales_order"],
			"modified desc, idx asc",
		)
		self.plan_items = get_rows_by_parent(
			"Production Plan Item",
			production_plans,
			["parent", "bom_no", "sales_order"],
			"modified asc, idx asc",
		)

		boms = self.get_boms()
		self.bom_items = get_bom_items(boms, list({row.item_code for row in self.rows}))
		self.bom_main_items = dict(
			frappe.get_all("BOM", filters={"name": ("in", boms)}, fields=["name", "item"], as_list=True)
		)

	def run(self):
		updates = {}
		for row in self.rows:
			if main_item_code := self.get_main_item_code(row):
				updates[row.name] = {"main_item_code": main_item_code}

		frappe.db.bulk_update("Material Request Plan Item", updates, update_modified=False)

	def get_boms(self):
		plan_rows = (*self.sub_assemblies.values(), *self.plan_items.values())
		return list({d.bom_no for rows in plan_rows for d in rows if d.bom_no})

	def get_main_item_code(self, row):
		sub_assemblies = self.get_plan_rows(self.sub_assemblies, row)
		return (
			next((d.parent_item_code for d in sub_assemblies if d.production_item == row.item_code), None)
			or self.get_bom_main_item(sub_assemblies, row.item_code)
			or self.get_bom_main_item(self.get_plan_rows(self.plan_items, row), row.item_code)
		)

	def get_bom_main_item(self, plan_rows, item_code):
		return next(
			(self.bom_main_items.get(d.bom_no) for d in plan_rows if (d.bom_no, item_code) in self.bom_items),
			None,
		)

	def get_plan_rows(self, rows_by_parent, row):
		return [
			d
			for d in rows_by_parent.get(row.parent, [])
			if not row.sales_order or d.sales_order == row.sales_order
		]


def get_rows_by_parent(doctype, production_plans, fields, order_by):
	rows_by_parent = defaultdict(list)
	rows = frappe.get_all(
		doctype, filters={"parent": ("in", production_plans)}, fields=fields, order_by=order_by
	)
	for row in rows:
		rows_by_parent[row.parent].append(row)

	return rows_by_parent


def get_bom_items(boms, item_codes):
	filters = {"parent": ("in", boms), "item_code": ("in", item_codes)}
	return {
		(d.parent, d.item_code)
		for doctype in ("BOM Item", "BOM Explosion Item")
		for d in frappe.get_all(doctype, filters=filters, fields=["parent", "item_code"])
	}
