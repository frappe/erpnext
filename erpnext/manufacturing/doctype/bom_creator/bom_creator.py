# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate

BOM_FIELDS = [
	"company",
	"rm_cost_as_per",
	"project",
	"currency",
	"conversion_rate",
	"buying_price_list",
]


class BOMCreator(Document):
	def before_save(self):
		self.set_conversion_factor()
		self.set_reference_id()
		self.set_is_expandable()
		self.set_rate_for_items()

	def set_conversion_factor(self):
		for row in self.items:
			row.conversion_factor = 1.0

	def before_submit(self):
		self.validate_fields()

	def set_reference_id(self):
		parent_reference = {row.idx: row.name for row in self.items}

		for row in self.items:
			if row.fg_reference_id:
				continue

			if row.parent_row_no:
				row.fg_reference_id = parent_reference.get(row.parent_row_no)

	@frappe.whitelist()
	def add_boms(self):
		self.submit()

	def set_rate_for_items(self):
		if self.rm_cost_as_per == "Manual":
			return

		self.set_rate_for_raw_materials()
		self.set_rate_for_sub_assemblies()

	def set_rate_for_raw_materials(self):
		for row in self.items:
			if row.is_expandable:
				continue

			row.rate = get_bom_item_rate(
				{
					"company": self.company,
					"item_code": row.item_code,
					"bom_no": "",
					"qty": row.qty,
					"uom": row.uom,
					"stock_uom": row.stock_uom,
					"conversion_factor": row.conversion_factor,
					"sourced_by_supplier": row.sourced_by_supplier,
				},
				self,
			)

			row.amount = flt(row.rate) * flt(row.qty)

	def set_rate_for_sub_assemblies(self):
		sub_assemblies = frappe._dict({})
		for row in self.items:
			if row.fg_reference_id == self.name:
				continue

			sub_assemblies.setdefault((row.fg_reference_id), []).append(flt(row.amount))

		self.raw_material_cost = 0
		for row in self.items:
			if row.name in sub_assemblies:
				row.amount = sum(sub_assemblies.get(row.name))
				row.rate = flt(row.amount) / (flt(row.qty) * flt(row.conversion_factor))

			if row.fg_reference_id == self.name:
				self.raw_material_cost += flt(row.amount)

	def set_is_expandable(self):
		fg_items = [row.fg_item for row in self.items]
		for row in self.items:
			row.is_expandable = 0
			if row.item_code in fg_items:
				row.is_expandable = 1

	def validate_fields(self):
		fields = {
			"items": "Items",
		}

		for field, label in fields.items():
			if not self.get(field):
				frappe.throw(_("Please set {0} in BOM Creator {1}").format(label, self.name))

	def on_submit(self):
		self.create_boms()

	def create_boms(self):
		"""
		Sample data structure of production_item_wise_rm
		production_item_wise_rm = {
		        (fg_item_code, name): {
		                "items": [],
		                "bom_no": "",
		                "fg_item_data": {}
		        }
		}
		"""

		production_item_wise_rm = OrderedDict({})
		production_item_wise_rm.setdefault(
			(self.item_code, self.name), frappe._dict({"items": [], "bom_no": "", "fg_item_data": self})
		)

		for row in self.items:
			if row.is_expandable:
				if (row.item_code, row.name) not in production_item_wise_rm:
					production_item_wise_rm.setdefault(
						(row.item_code, row.name), frappe._dict({"items": [], "bom_no": "", "fg_item_data": row})
					)

			production_item_wise_rm[(row.fg_item, row.fg_reference_id)]["items"].append(row)

		reverse_tree = OrderedDict(reversed(list(production_item_wise_rm.items())))

		for d in reverse_tree:
			fg_item_data = production_item_wise_rm.get(d).fg_item_data
			self.create_bom(fg_item_data, production_item_wise_rm)

		frappe.msgprint(_("BOMs created successfully"))

	def create_bom(self, row, production_item_wise_rm):
		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": row.item_code,
				"bom_type": "Production",
				"quantity": row.qty,
				"allow_alternative_item": 1,
				"bom_creator": self.name,
				"rm_cost_as_per": "Manual",
			}
		)

		for field in BOM_FIELDS:
			if self.get(field):
				bom.set(field, self.get(field))

		for item in production_item_wise_rm[(row.item_code, row.name)]["items"]:
			bom_no = ""
			if (item.item_code, item.name) in production_item_wise_rm:
				bom_no = production_item_wise_rm.get((item.item_code, item.name)).bom_no
				item.do_not_explode = 0

			bom.append(
				"items",
				{
					"item_code": item.item_code,
					"qty": item.qty,
					"uom": item.uom,
					"rate": item.rate,
					"conversion_factor": item.conversion_factor,
					"stock_qty": item.stock_qty,
					"stock_uom": item.stock_uom,
					"do_not_explode": item.do_not_explode,
					"bom_no": bom_no,
					"allow_alternative_item": 1,
					"allow_scrap_items": 1,
					"include_item_in_manufacturing": 1,
				},
			)

		bom.save(ignore_permissions=True)
		bom.submit()

		production_item_wise_rm[(row.item_code, row.name)].bom_no = bom.name

	@frappe.whitelist()
	def get_default_bom(self, item_code) -> str:
		return frappe.get_cached_value("Item", item_code, "default_bom")


@frappe.whitelist()
def get_children(doctype=None, parent=None, **kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	fields = [
		"item_code as value",
		"is_expandable as expandable",
		"parent as parent_id",
		"qty",
		"idx",
		"'BOM Creator Item' as doctype",
		"name",
		"uom",
		"rate",
		"amount",
	]

	query_filters = {
		"fg_item": parent,
		"parent": kwargs.parent_id,
	}

	if kwargs.name:
		query_filters["name"] = kwargs.name

	return frappe.get_all("BOM Creator Item", fields=fields, filters=query_filters, order_by="idx")


@frappe.whitelist()
def add_item(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	doc = frappe.get_doc("BOM Creator", kwargs.parent)
	item_info = get_item_details(kwargs.item_code)
	kwargs.update(
		{
			"uom": item_info.stock_uom,
			"stock_uom": item_info.stock_uom,
			"conversion_factor": 1,
		}
	)

	doc.append("items", kwargs)
	doc.save()


@frappe.whitelist()
def add_sub_assembly(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	doc = frappe.get_doc("BOM Creator", kwargs.parent)
	bom_item = frappe.parse_json(kwargs.bom_item)

	name = kwargs.fg_reference_id
	parent_row_no = ""
	if not kwargs.convert_to_sub_assembly:
		item_info = get_item_details(bom_item.item_code)
		item_row = doc.append(
			"items",
			{
				"item_code": bom_item.item_code,
				"qty": bom_item.qty,
				"uom": item_info.stock_uom,
				"fg_item": kwargs.fg_item,
				"conversion_factor": 1,
				"fg_reference_id": name,
				"stock_qty": bom_item.qty,
				"fg_reference_id": name,
				"do_not_explode": 1,
				"stock_uom": item_info.stock_uom,
			},
		)

		parent_row_no = item_row.idx
		name = ""

	for row in bom_item.get("items"):
		row = frappe._dict(row)
		item_info = get_item_details(row.item_code)
		doc.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"fg_item": bom_item.item_code,
				"uom": item_info.stock_uom,
				"fg_reference_id": name,
				"parent_row_no": parent_row_no,
				"conversion_factor": 1,
				"do_not_explode": 1,
				"stock_qty": row.qty,
				"stock_uom": item_info.stock_uom,
			},
		)

	doc.save()
	return doc


def get_item_details(item_code):
	return frappe.get_cached_value(
		"Item", item_code, ["item_name", "description", "image", "stock_uom", "default_bom"], as_dict=1
	)


@frappe.whitelist()
def delete_node(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	items = get_children(parent=kwargs.fg_item, parent_id=kwargs.parent)
	if kwargs.docname:
		frappe.delete_doc("BOM Creator Item", kwargs.docname)

	for item in items:
		frappe.delete_doc("BOM Creator Item", item.name)
		if item.expandable:
			delete_node(fg_item=item.value, parent=item.parent_id)


@frappe.whitelist()
def edit_qty(doctype, docname, qty):
	frappe.db.set_value(doctype, docname, "qty", qty)
