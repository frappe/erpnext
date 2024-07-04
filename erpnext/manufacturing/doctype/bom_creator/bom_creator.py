# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate

BOM_FIELDS = [
	"company",
	"rm_cost_as_per",
	"project",
	"currency",
	"conversion_rate",
	"buying_price_list",
]

BOM_ITEM_FIELDS = [
	"item_code",
	"qty",
	"uom",
	"rate",
	"stock_qty",
	"stock_uom",
	"conversion_factor",
	"do_not_explode",
]


class BOMCreator(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.bom_creator_item.bom_creator_item import BOMCreatorItem

		amended_from: DF.Link | None
		buying_price_list: DF.Link | None
		company: DF.Link
		conversion_rate: DF.Float
		currency: DF.Link
		default_warehouse: DF.Link | None
		error_log: DF.Text | None
		item_code: DF.Link
		item_group: DF.Link | None
		item_name: DF.Data | None
		items: DF.Table[BOMCreatorItem]
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link | None
		project: DF.Link | None
		qty: DF.Float
		raw_material_cost: DF.Currency
		remarks: DF.TextEditor | None
		rm_cost_as_per: DF.Literal["Valuation Rate", "Last Purchase Rate", "Price List"]
		set_rate_based_on_warehouse: DF.Check
		status: DF.Literal["Draft", "Submitted", "In Progress", "Completed", "Failed", "Cancelled"]
		uom: DF.Link | None
	# end: auto-generated types

	def before_save(self):
		self.set_status()
		self.set_is_expandable()
		self.set_conversion_factor()
		self.set_reference_id()
		self.set_rate_for_items()

	def validate(self):
		self.validate_items()

	def validate_items(self):
		for row in self.items:
			if row.is_expandable and row.item_code == self.item_code:
				frappe.throw(_("Item {0} cannot be added as a sub-assembly of itself").format(row.item_code))

			if not row.parent_row_no and row.fg_item and row.fg_item != self.item_code:
				frappe.throw(
					_("At row {0}: set Parent Row No for item {1}").format(row.idx, row.item_code),
					title=_("Set Parent Row No in Items Table"),
				)

			elif row.parent_row_no and row.fg_item == self.item_code:
				frappe.throw(
					_("At row {0}: Parent Row No cannot be set for item {1}").format(row.idx, row.item_code),
					title=_("Remove Parent Row No in Items Table"),
				)

	def set_status(self, save=False):
		self.status = {
			0: "Draft",
			1: "Submitted",
			2: "Cancelled",
		}[self.docstatus]

		self.set_status_completed()
		if save:
			self.db_set("status", self.status)

	def set_status_completed(self):
		if self.docstatus != 1:
			return

		has_completed = True
		for row in self.items:
			if row.is_expandable and not row.bom_created:
				has_completed = False
				break

		if not frappe.get_cached_value("BOM", {"bom_creator": self.name, "item": self.item_code}, "name"):
			has_completed = False

		if has_completed:
			self.status = "Completed"

	def on_cancel(self):
		self.set_status(True)

	def set_conversion_factor(self):
		for row in self.items:
			row.conversion_factor = 1.0

	def before_submit(self):
		self.validate_fields()
		self.set_status()

	def set_reference_id(self):
		parent_reference = {row.idx: row.name for row in self.items}

		for row in self.items:
			ref_id = ""

			if row.parent_row_no:
				ref_id = parent_reference.get(cint(row.parent_row_no))

			# Check whether the reference id of the FG Item has correct or not
			if row.fg_reference_id and row.fg_reference_id == ref_id:
				continue

			if row.parent_row_no:
				row.fg_reference_id = ref_id
			elif row.fg_item == self.item_code:
				row.fg_reference_id = self.name

	@frappe.whitelist()
	def add_boms(self):
		self.submit()

	def set_rate_for_items(self):
		amount = self.get_raw_material_cost()
		self.raw_material_cost = amount

	def get_raw_material_cost(self, fg_item=None, amount=0):
		if not fg_item:
			fg_item = self.item_code

		for row in self.items:
			if row.fg_item != fg_item:
				continue

			if not row.is_expandable:
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

			else:
				row.amount = 0.0
				row.amount = self.get_raw_material_cost(row.item_code, row.amount)
				row.rate = flt(row.amount) / (flt(row.qty) * flt(row.conversion_factor))

			amount += flt(row.amount)

		return amount

	def set_is_expandable(self):
		fg_items = [row.fg_item for row in self.items if row.fg_item != self.item_code]
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
		self.enqueue_create_boms()

	@frappe.whitelist()
	def enqueue_create_boms(self):
		frappe.enqueue(
			self.create_boms,
			queue="short",
			timeout=600,
			is_async=True,
		)

		frappe.msgprint(
			_("BOMs creation has been enqueued, kindly check the status after some time"), alert=True
		)

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

		self.db_set("status", "In Progress")
		production_item_wise_rm = OrderedDict({})
		production_item_wise_rm.setdefault(
			(self.item_code, self.name), frappe._dict({"items": [], "bom_no": "", "fg_item_data": self})
		)

		for row in self.items:
			if row.is_expandable:
				if (row.item_code, row.name) not in production_item_wise_rm:
					production_item_wise_rm.setdefault(
						(row.item_code, row.name),
						frappe._dict({"items": [], "bom_no": "", "fg_item_data": row}),
					)

			if not row.fg_reference_id and production_item_wise_rm.get((row.fg_item, row.fg_reference_id)):
				frappe.throw(_("Please set Parent Row No for item {0}").format(row.fg_item))

			production_item_wise_rm[(row.fg_item, row.fg_reference_id)]["items"].append(row)

		reverse_tree = OrderedDict(reversed(list(production_item_wise_rm.items())))

		try:
			for d in reverse_tree:
				fg_item_data = production_item_wise_rm.get(d).fg_item_data
				self.create_bom(fg_item_data, production_item_wise_rm)

			frappe.msgprint(_("BOMs created successfully"))
		except Exception:
			traceback = frappe.get_traceback(with_context=True)
			self.db_set(
				{
					"status": "Failed",
					"error_log": traceback,
				}
			)

			frappe.msgprint(_("BOMs creation failed"))

	def create_bom(self, row, production_item_wise_rm):
		bom_creator_item = row.name if row.name != self.name else ""
		if frappe.db.exists(
			"BOM",
			{
				"bom_creator": self.name,
				"item": row.item_code,
				"bom_creator_item": bom_creator_item,
				"docstatus": 1,
			},
		):
			return

		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": row.item_code,
				"bom_type": "Production",
				"quantity": row.qty,
				"allow_alternative_item": 1,
				"bom_creator": self.name,
				"bom_creator_item": bom_creator_item,
			}
		)

		for field in BOM_FIELDS:
			if self.get(field):
				bom.set(field, self.get(field))

		for item in production_item_wise_rm[(row.item_code, row.name)]["items"]:
			bom_no = ""
			item.do_not_explode = 1
			if (item.item_code, item.name) in production_item_wise_rm:
				bom_no = production_item_wise_rm.get((item.item_code, item.name)).bom_no
				item.do_not_explode = 0

			item_args = {}
			for field in BOM_ITEM_FIELDS:
				item_args[field] = item.get(field)

			item_args.update(
				{
					"bom_no": bom_no,
					"allow_alternative_item": 1,
					"allow_scrap_items": 1,
					"include_item_in_manufacturing": 1,
				}
			)

			bom.append("items", item_args)

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

	return doc


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
				"do_not_explode": 1,
				"is_expandable": 1,
				"stock_uom": item_info.stock_uom,
			},
		)

		parent_row_no = item_row.idx
		name = ""
	else:
		parent_row_no = [row.idx for row in doc.items if row.name == kwargs.fg_reference_id]
		if parent_row_no:
			parent_row_no = parent_row_no[0]

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

	doc = frappe.get_doc("BOM Creator", kwargs.parent)
	doc.set_rate_for_items()
	doc.save()

	return doc


@frappe.whitelist()
def edit_qty(doctype, docname, qty, parent):
	frappe.db.set_value(doctype, docname, "qty", qty)
	doc = frappe.get_doc("BOM Creator", parent)
	doc.set_rate_for_items()
	doc.save()

	return doc
