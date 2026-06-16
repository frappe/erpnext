# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import functools
import re
from collections import deque

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder import Field
from frappe.query_builder.functions import Count, IfNull, Sum
from frappe.utils import cint, cstr, flt, get_link_to_form, parse_json
from frappe.website.website_generator import WebsiteGenerator

import erpnext
from erpnext.setup.utils import get_exchange_rate
from erpnext.stock.doctype.item.item import get_item_details
from erpnext.stock.get_item_details import ItemDetailsCtx, get_conversion_factor, get_price_list_rate

form_grid_templates = {"items": "templates/form_grid/item_grid.html"}


# Backward-compatible re-exports: these were moved to mapper.py / services/.
# Re-importing here preserves whitelist dotted-paths and external imports.
from erpnext.manufacturing.doctype.bom.mapper import (
	get_bom_diff,
	get_children,
	item_query,
	make_variant_bom,
)
from erpnext.manufacturing.doctype.bom.services.costing import (
	BOMCostingService,
)
from erpnext.manufacturing.doctype.bom.services.exploded_items import (
	BOMExplodedItemsService,
)
from erpnext.manufacturing.doctype.bom.services.operations_cost import (
	add_additional_cost,
	add_non_stock_items_cost,
	add_operating_cost_component_wise,
	add_operations_cost,
	get_component_account,
	get_op_cost_from_sub_assemblies,
	get_secondary_items_from_sub_assemblies,
)


class BOMRecursionError(frappe.ValidationError):
	pass


class BOMTree:
	"""Full tree representation of a BOM"""

	# specifying the attributes to save resources
	# ref: https://docs.python.org/3/reference/datamodel.html#slots
	__slots__ = ["name", "child_items", "is_bom", "item_code", "qty", "exploded_qty", "bom_qty"]

	def __init__(self, name: str, is_bom: bool = True, exploded_qty: float = 1.0, qty: float = 1) -> None:
		self.name = name  # name of node, BOM number if is_bom else item_code
		self.child_items: list["BOMTree"] = []  # list of child items
		self.is_bom = is_bom  # true if the node is a BOM and not a leaf item
		self.item_code: str = None  # item_code associated with node
		self.qty = qty  # required unit quantity to make one unit of parent item.
		self.exploded_qty = exploded_qty  # total exploded qty required for making root of tree.
		if not self.is_bom:
			self.item_code = self.name
		else:
			self.__create_tree()

	def __create_tree(self):
		bom = frappe.get_cached_doc("BOM", self.name)
		self.item_code = bom.item
		self.bom_qty = bom.quantity

		for item in bom.get("items", []):
			qty = item.stock_qty / bom.quantity  # quantity per unit
			exploded_qty = self.exploded_qty * qty
			if item.bom_no:
				child = BOMTree(item.bom_no, exploded_qty=exploded_qty, qty=qty)
				self.child_items.append(child)
			else:
				self.child_items.append(
					BOMTree(item.item_code, is_bom=False, exploded_qty=exploded_qty, qty=qty)
				)

	def level_order_traversal(self) -> list["BOMTree"]:
		"""Get level order traversal of tree.
		E.g. for following tree the traversal will return list of nodes in order from top to bottom.
		BOM:
		        - SubAssy1
		                - item1
		                - item2
		        - SubAssy2
		                - item3
		        - item4

		returns = [SubAssy1, item1, item2, SubAssy2, item3, item4]
		"""
		traversal = []
		q = deque()
		q.append(self)

		while q:
			node = q.popleft()

			for child in node.child_items:
				traversal.append(child)
				q.append(child)

		return traversal

	def __str__(self) -> str:
		return (
			f"{self.item_code}{' - ' + self.name if self.is_bom else ''} qty(per unit): {self.qty}"
			f" exploded_qty: {self.exploded_qty}"
		)

	def __repr__(self, level: int = 0) -> str:
		rep = "┃  " * (level - 1) + "┣━ " * (level > 0) + str(self) + "\n"
		for child in self.child_items:
			rep += child.__repr__(level=level + 1)
		return rep


class BOM(WebsiteGenerator):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.bom_explosion_item.bom_explosion_item import BOMExplosionItem
		from erpnext.manufacturing.doctype.bom_item.bom_item import BOMItem
		from erpnext.manufacturing.doctype.bom_operation.bom_operation import BOMOperation
		from erpnext.manufacturing.doctype.bom_secondary_item.bom_secondary_item import BOMSecondaryItem

		allow_alternative_item: DF.Check
		amended_from: DF.Link | None
		backflush_based_on: DF.Literal["", "BOM", "Material Transferred for Manufacture"]
		base_operating_cost: DF.Currency
		base_raw_material_cost: DF.Currency
		base_secondary_items_cost: DF.Currency
		base_total_cost: DF.Currency
		bom_creator: DF.Link | None
		bom_creator_item: DF.Data | None
		buying_price_list: DF.Link | None
		company: DF.Link
		conversion_rate: DF.Float
		cost_allocation: DF.Currency
		cost_allocation_per: DF.Percent
		currency: DF.Link
		default_source_warehouse: DF.Link | None
		default_target_warehouse: DF.Link | None
		description: DF.SmallText | None
		exploded_items: DF.Table[BOMExplosionItem]
		fg_based_operating_cost: DF.Check
		has_variants: DF.Check
		image: DF.AttachImage | None
		inspection_required: DF.Check
		is_active: DF.Check
		is_default: DF.Check
		is_phantom_bom: DF.Check
		item: DF.Link
		item_name: DF.Data | None
		items: DF.Table[BOMItem]
		operating_cost: DF.Currency
		operating_cost_per_bom_quantity: DF.Currency
		operations: DF.Table[BOMOperation]
		plc_conversion_rate: DF.Float
		price_list_currency: DF.Link | None
		process_loss_percentage: DF.Percent
		process_loss_qty: DF.Float
		project: DF.Link | None
		quality_inspection_template: DF.Link | None
		quantity: DF.Float
		raw_material_cost: DF.Currency
		rm_cost_as_per: DF.Literal["Valuation Rate", "Last Purchase Rate", "Price List"]
		route: DF.SmallText | None
		routing: DF.Link | None
		secondary_items: DF.Table[BOMSecondaryItem]
		secondary_items_cost: DF.Currency
		set_rate_of_sub_assembly_item_based_on_bom: DF.Check
		show_in_website: DF.Check
		show_items: DF.Check
		show_operations: DF.Check
		thumbnail: DF.Data | None
		total_cost: DF.Currency
		track_semi_finished_goods: DF.Check
		transfer_material_against: DF.Literal["", "Work Order", "Job Card"]
		uom: DF.Link | None
		web_long_description: DF.TextEditor | None
		website_image: DF.AttachImage | None
		with_operations: DF.Check
	# end: auto-generated types

	website = frappe._dict(
		# page_title_field = "item_name",
		condition_field="show_in_website",
		template="templates/generators/bom.html",
	)

	def autoname(self):
		# ignore amended documents while calculating current index
		search_key = f"{self.doctype}-{self.item}%"
		existing_boms = frappe.get_all(
			"BOM", filters={"name": search_key, "amended_from": ["is", "not set"]}, pluck="name"
		)

		index = self.get_index_for_bom(existing_boms)
		name = self._build_bom_name(index)

		if frappe.db.exists("BOM", name):
			existing_boms = frappe.get_all(
				"BOM", filters={"name": ("like", search_key), "amended_from": ["is", "not set"]}, pluck="name"
			)

			index = self.get_index_for_bom(existing_boms)
			name = f"{self.doctype}-{self.item}-{'%.3i' % index}"

		self.name = name

	def _build_bom_name(self, index):
		prefix = self.doctype
		suffix = "%.3i" % index  # convert index to string (1 -> "001")
		bom_name = f"{prefix}-{self.item}-{suffix}"

		if len(bom_name) <= 140:
			return bom_name

		# since max characters for name is 140, remove enough characters from the
		# item name to fit the prefix, suffix and the separators
		truncated_length = 140 - (len(prefix) + len(suffix) + 2)
		truncated_item_name = self.item[:truncated_length]
		# if a partial word is found after truncate, remove the extra characters
		truncated_item_name = truncated_item_name.rsplit(" ", 1)[0]
		return f"{prefix}-{truncated_item_name}-{suffix}"

	def get_index_for_bom(self, existing_boms):
		index = 1
		if existing_boms:
			index = self.get_next_version_index(existing_boms)

		return index

	def onload(self):
		super().onload()

		self.set_onload_for_multi_level_bom()

	def set_onload_for_multi_level_bom(self):
		use_multi_level_bom = frappe.db.get_value(
			"Property Setter",
			{"field_name": "use_multi_level_bom", "doc_type": "Work Order", "property": "default"},
			"value",
		)

		if use_multi_level_bom is None:
			use_multi_level_bom = 1

		self.set_onload("use_multi_level_bom", cint(use_multi_level_bom))

	@staticmethod
	def get_next_version_index(existing_boms: list[str]) -> int:
		# split by "/" and "-"
		delimiters = ["/", "-"]
		pattern = "|".join(map(re.escape, delimiters))
		bom_parts = [re.split(pattern, bom_name) for bom_name in existing_boms]

		# filter out BOMs that do not follow the following formats: BOM/ITEM/001, BOM-ITEM-001
		valid_bom_parts = list(filter(lambda x: len(x) > 1 and x[-1], bom_parts))

		# extract the current index from the BOM parts
		if valid_bom_parts:
			# handle cancelled and submitted documents
			indexes = [cint(part[-1]) for part in valid_bom_parts]
			index = max(indexes) + 1
		else:
			index = 1

		return index

	def before_validate(self):
		for item in self.items:
			if not item.conversion_factor:
				item.conversion_factor = (
					frappe.get_value(
						"UOM Conversion Detail",
						{"parent": item.item_code, "uom": item.uom},
						"conversion_factor",
					)
					or 1
				)

	def validate(self):
		self.route = frappe.scrub(self.name).replace("_", "-")

		if not self.company:
			frappe.throw(_("Please select a Company first."), title=_("Mandatory"))

		self._validate_setup()
		self._validate_materials_and_cost()
		self._validate_uoms_and_goods()

		if self.docstatus == 1:
			self.validate_raw_materials_of_operation()

	def _validate_setup(self):
		self.clear_operations()
		self.clear_inspection()
		self.validate_main_item()
		self.validate_currency()
		self.set_materials_based_on_operation_bom()
		self.set_conversion_rate()
		self.set_plc_conversion_rate()
		self.validate_uom_is_interger()

	def _validate_materials_and_cost(self):
		self.set_bom_material_details()
		self.set_secondary_items_details()
		self.validate_materials()
		self.validate_transfer_against()
		self.set_routing_operations()
		self.validate_operations()
		self.calculate_cost()
		self.update_exploded_items(save=False)
		self.update_stock_qty()
		self.update_cost(update_parent=False, from_child_bom=True, update_hour_rate=False, save=False)

	def _validate_uoms_and_goods(self):
		self.set_process_loss_qty()
		self.validate_uoms()
		self.set_default_uom()
		self.validate_semi_finished_goods()
		self.validate_secondary_items()
		self.set_fg_cost_allocation()
		self.validate_total_cost_allocation()

	def validate_semi_finished_goods(self):
		if not self.track_semi_finished_goods or not self.operations:
			return

		fg_items = []
		for row in self.operations:
			if not row.is_final_finished_good:
				continue

			fg_items.append(row.finished_good)

		if not fg_items:
			frappe.throw(
				_(
					"Since you have enabled 'Track Semi Finished Goods', at least one operation must have 'Is Final Finished Good' checked. For that set the FG / Semi FG Item as {0} against an operation."
				).format(bold(self.item)),
			)

		if fg_items and len(fg_items) > 1:
			frappe.throw(
				_(
					"Only one operation can have 'Is Final Finished Good' checked when 'Track Semi Finished Goods' is enabled."
				),
			)

	def validate_secondary_items(self):
		for item in self.secondary_items:
			if not item.is_legacy and item.item_code == self.item:
				frappe.throw(
					_(
						"Row #{0}: Finished Good Item {1} cannot be added in the Secondary Items table."
					).format(item.idx, get_link_to_form("Item", item.item_code))
				)

			if not item.qty:
				frappe.throw(
					_("Row #{0}: Quantity should be greater than 0 for {1} Item {2}").format(
						item.idx, item.secondary_item_type, get_link_to_form("Item", item.item_code)
					)
				)

			if item.process_loss_per >= 100:
				frappe.throw(
					_("Row #{0}: Process Loss Percentage should be less than 100% for {1} Item {2}").format(
						item.idx, item.secondary_item_type, get_link_to_form("Item", item.item_code)
					)
				)

	def validate_raw_materials_of_operation(self):
		if not self.track_semi_finished_goods or not self.operations:
			return

		operation_idx_with_no_rm = {}
		for row in self.operations:
			if row.bom_no:
				continue

			operation_idx_with_no_rm[row.idx] = row

		for row in self.items:
			if row.operation_row_id and row.operation_row_id in operation_idx_with_no_rm:
				del operation_idx_with_no_rm[row.operation_row_id]

		for idx, row in operation_idx_with_no_rm.items():
			frappe.throw(
				_("For operation {0} at row {1}, please add raw materials or set a BOM against it.").format(
					bold(row.operation), idx
				),
			)

	def set_default_uom(self):
		if not self.get("items"):
			return

		item_wise_uom = frappe._dict(
			frappe.get_all(
				"Item",
				filters={"name": ("in", [item.item_code for item in self.items])},
				fields=["name", "stock_uom"],
				as_list=1,
			)
		)

		for row in self.get("items"):
			if row.stock_uom != item_wise_uom.get(row.item_code):
				row.stock_uom = item_wise_uom.get(row.item_code)

	def get_context(self, context):
		context.parents = [{"name": "boms", "title": _("All BOMs")}]

	def on_update(self):
		frappe.cache().hdel("bom_children", self.name)
		self.check_recursion()

	def on_submit(self):
		self.manage_default_bom()
		self.update_bom_creator_status()

	def on_cancel(self):
		self.db_set("is_active", 0)
		self.db_set("is_default", 0)

		# check if used in any other bom
		self.validate_bom_links()
		self.manage_default_bom()
		self.update_bom_creator_status()

	def update_bom_creator_status(self):
		if not self.bom_creator:
			return

		if self.bom_creator_item:
			frappe.db.set_value(
				"BOM Creator Item",
				self.bom_creator_item,
				"bom_created",
				1 if self.docstatus == 1 else 0,
				update_modified=False,
			)

		doc = frappe.get_doc("BOM Creator", self.bom_creator)
		doc.set_status(save=True)

	def set_fg_cost_allocation(self):
		total_secondary_items_per = 0
		for item in self.secondary_items:
			total_secondary_items_per += item.cost_allocation_per

		if self.cost_allocation_per == 100 and total_secondary_items_per:
			self.cost_allocation_per -= total_secondary_items_per

		self.cost_allocation = self.raw_material_cost * (self.cost_allocation_per / 100)

	def validate_total_cost_allocation(self):
		total_cost_allocation_per = self.cost_allocation_per
		for item in self.secondary_items:
			total_cost_allocation_per += item.cost_allocation_per

		if total_cost_allocation_per != 100:
			frappe.throw(_("Cost allocation between finished goods and secondary items should equal 100%"))

	def on_update_after_submit(self):
		self.validate_bom_links()
		self.manage_default_bom()

	def get_item_det(self, item_code):
		item = get_item_details(item_code)

		if not item:
			frappe.throw(_("Item: {0} does not exist in the system").format(item_code))

		return item

	@frappe.whitelist()
	def get_routing(self):
		if not self.routing:
			return

		self.set("operations", [])
		for row in frappe.get_all(
			"BOM Operation",
			fields=self._get_routing_fields(),
			filters={"parenttype": "Routing", "parent": self.routing},
			order_by="sequence_id, idx",
		):
			child = self.append("operations", row)
			child.hour_rate = flt(row.hour_rate / self.conversion_rate, child.precision("hour_rate"))

	@staticmethod
	def _get_routing_fields():
		return [
			"sequence_id",
			"operation",
			"workstation",
			"workstation_type",
			"description",
			"time_in_mins",
			"batch_size",
			"operating_cost",
			"idx",
			"hour_rate",
			"set_cost_based_on_bom_qty",
			"fixed_time",
		]

	def set_bom_material_details(self):
		for item in self.get("items"):
			self.validate_bom_currency(item)

			if item.do_not_explode:
				item.bom_no = ""

			ret = self.get_bom_material_detail(
				{
					"company": self.company,
					"item_code": item.item_code,
					"item_name": item.item_name,
					"bom_no": item.bom_no,
					"stock_qty": item.stock_qty,
					"include_item_in_manufacturing": item.include_item_in_manufacturing,
					"qty": item.qty,
					"uom": item.uom,
					"stock_uom": item.stock_uom,
					"conversion_factor": item.conversion_factor,
					"sourced_by_supplier": item.sourced_by_supplier,
					"do_not_explode": item.do_not_explode,
					"fetch_rate": True,
				}
			)

			for r in ret:
				if not item.get(r):
					item.set(r, ret[r])

	def set_secondary_items_details(self):
		for item in self.get("secondary_items"):
			args = {
				"item_code": item.item_code,
				"company": self.company,
				"uom": item.uom,
				"fetch_rate": False,
			}
			ret = self.get_bom_material_detail(args)
			for key, value in ret.items():
				if item.get(key) is None:
					item.set(key, value)

	@frappe.whitelist()
	def get_bom_material_detail(self, args: dict | str | None = None):
		"""Get raw material details like uom, desc and rate"""
		args = self._normalize_material_args(args)
		item = self.get_item_det(args["item_code"])

		args["bom_no"] = args.get("bom_no") or item and cstr(item["default_bom"]) or ""
		args["transfer_for_manufacture"] = (
			cstr(args.get("include_item_in_manufacturing", ""))
			or item
			and item.include_item_in_manufacturing
			or 0
		)
		args.update(item)

		rate = self.get_rm_rate(args) if args.get("fetch_rate") else 0
		return self._build_rm_detail(args, item, rate)

	@staticmethod
	def _normalize_material_args(kwargs):
		if not kwargs:
			kwargs = frappe.form_dict.get("args")

		if isinstance(kwargs, str):
			import json

			kwargs = json.loads(kwargs)

		return kwargs

	def _build_rm_detail(self, args, item, rate):
		ret_item = {
			"item_name": item and args["item_name"] or "",
			"description": item and args["description"] or "",
			"image": item and args["image"] or "",
			"stock_uom": item and args["stock_uom"] or "",
			"uom": args["uom"] if args.get("uom") else item and args["stock_uom"] or "",
			"conversion_factor": args["conversion_factor"] if args.get("conversion_factor") else 1,
			"bom_no": args["bom_no"],
			"is_phantom_item": frappe.get_value("BOM", args["bom_no"], "is_phantom_bom")
			if args["bom_no"]
			else 0,
			"rate": rate,
			"qty": args.get("qty") or args.get("stock_qty") or 1,
			"stock_qty": args.get("stock_qty") or args.get("qty") or 1,
			"base_rate": flt(rate) * (flt(self.conversion_rate) or 1),
			"include_item_in_manufacturing": cint(args.get("transfer_for_manufacture")),
			"sourced_by_supplier": args.get("sourced_by_supplier", 0),
		}

		if ret_item["is_phantom_item"]:
			ret_item["do_not_explode"] = 0

		if args.get("do_not_explode"):
			ret_item["bom_no"] = ""

		return ret_item

	def manage_default_bom(self):
		"""Uncheck others if current one is selected as default or
		check the current one as default if it the only bom for the selected item,
		update default bom in item master
		"""
		if self.is_default and self.is_active:
			self._set_as_default_bom()
		elif (
			not frappe.db.exists(dict(doctype="BOM", docstatus=1, item=self.item, is_default=1))
			and self.is_active
		):
			self.db_set("is_default", 1)
			frappe.db.set_value("Item", self.item, "default_bom", self.name)
		else:
			self._unset_default_bom()

	def _set_as_default_bom(self):
		from frappe.model.utils import set_default

		set_default(self, "item")
		item = frappe.get_doc("Item", self.item)
		if item.default_bom != self.name:
			frappe.db.set_value("Item", self.item, "default_bom", self.name)

	def _unset_default_bom(self):
		self.db_set("is_default", 0)
		item = frappe.get_doc("Item", self.item)
		if item.default_bom == self.name:
			frappe.db.set_value("Item", self.item, "default_bom", None)

	def clear_operations(self):
		if not self.with_operations:
			self.set("operations", [])

		if not self.with_operations and self.track_semi_finished_goods:
			self.track_semi_finished_goods = 0

	def clear_inspection(self):
		if not self.inspection_required:
			self.quality_inspection_template = None

	def validate_main_item(self):
		"""Validate main FG item"""
		item = self.get_item_det(self.item)
		if not item:
			frappe.throw(_("Item {0} does not exist in the system or has expired").format(self.item))
		else:
			ret = frappe.db.get_value("Item", self.item, ["description", "stock_uom", "item_name"])
			self.description = ret[0]
			self.uom = ret[1]
			self.item_name = ret[2]

		if not self.quantity:
			frappe.throw(_("Quantity should be greater than 0"))

	def validate_currency(self):
		if self.rm_cost_as_per == "Price List":
			price_list_currency = frappe.db.get_value("Price List", self.buying_price_list, "currency")
			if price_list_currency not in (self.currency, self.company_currency()):
				frappe.throw(
					_("Currency of the price list {0} must be {1} or {2}").format(
						self.buying_price_list, self.currency, self.company_currency()
					)
				)

	def update_stock_qty(self):
		for m in self.get("items") + self.get("secondary_items"):
			if not m.conversion_factor:
				m.conversion_factor = flt(get_conversion_factor(m.item_code, m.uom)["conversion_factor"])
			if m.uom and m.qty:
				m.stock_qty = flt(m.conversion_factor) * flt(m.qty)
			if not m.uom and m.stock_uom:
				m.uom = m.stock_uom
				m.qty = m.stock_qty

	def validate_uom_is_interger(self):
		from erpnext.utilities.transaction_base import validate_uom_is_integer

		validate_uom_is_integer(self, "uom", "qty", "BOM Item")
		validate_uom_is_integer(self, "stock_uom", "stock_qty", "BOM Item")

	def set_conversion_rate(self):
		if self.currency == self.company_currency():
			self.conversion_rate = 1
		elif self.conversion_rate == 1 or flt(self.conversion_rate) <= 0:
			self.conversion_rate = get_exchange_rate(
				self.currency, self.company_currency(), args="for_buying"
			)

	def set_plc_conversion_rate(self):
		if self.rm_cost_as_per in ["Valuation Rate", "Last Purchase Rate"]:
			self.plc_conversion_rate = 1
		elif not self.plc_conversion_rate and self.price_list_currency:
			self.plc_conversion_rate = get_exchange_rate(
				self.price_list_currency, self.company_currency(), args="for_buying"
			)

	def validate_materials(self):
		"""Validate raw material entries"""

		if not self.get("items"):
			frappe.throw(_("Raw Materials cannot be blank."))

		check_list = []
		items = []
		for m in self.get("items"):
			if m.bom_no:
				validate_bom_no(m.item_code, m.bom_no)
			if flt(m.qty) <= 0:
				frappe.throw(_("Quantity required for Item {0} in row {1}").format(m.item_code, m.idx))
			check_list.append(m)
			items.append(m.item_code)

		if fixed_asset_items := frappe.db.get_all(
			"Item", filters={"item_code": ("in", items), "is_fixed_asset": 1}, pluck="name"
		):
			frappe.throw(
				_("Fixed Asset item {0} cannot be used in BOMs.").format(
					", ".join(get_link_to_form("Item", item) for item in fixed_asset_items)
				)
			)

	def check_recursion(self, bom_list=None):
		"""Check whether recursion occurs in any bom"""
		bom_list = self.traverse_tree()
		child_items = frappe.get_all(
			"BOM Item",
			fields=["bom_no", "item_code"],
			filters={"parent": ("in", bom_list), "parenttype": "BOM"},
		)

		for item in child_items:
			self._check_item_recursion(item)

		if self.name in {d.bom_no for d in self.items}:
			self._throw_recursion_error(self.name)

	def _check_item_recursion(self, item):
		if self.name == item.bom_no:
			self._throw_recursion_error(self.name)
		if self.item == item.item_code and item.bom_no:
			# Same item but with different BOM should not be allowed.
			# Same item can appear recursively once as long as it doesn't have BOM.
			self._throw_recursion_error(item.bom_no, self.item)

	def _throw_recursion_error(self, bom_name, production_item=None):
		msg = _("BOM recursion: {1} cannot be parent or child of {0}").format(self.name, bom_name)
		if production_item and bom_name != self.name:
			msg += "<br><br>"
			msg += _(
				"Note: If you want to use the finished good {0} as a raw material, then enable the 'Do Not Explode' checkbox in the Items table against the same raw material."
			).format(bold(production_item))

		frappe.throw(
			msg,
			exc=BOMRecursionError,
		)

	def set_materials_based_on_operation_bom(self):
		if not self.track_semi_finished_goods:
			return

		for row in self.get("operations"):
			if row.bom_no and row.finished_good:
				self.add_materials_from_bom(row.finished_good, row.bom_no, row.idx, qty=row.finished_good_qty)

	@frappe.whitelist()
	def add_raw_materials(self, operation_row_id: int, items: str | list):
		if isinstance(items, str):
			items = parse_json(items)

		for row in items:
			self._add_raw_material_row(operation_row_id, row)

		self.save()

	def _add_raw_material_row(self, operation_row_id, row):
		row = parse_json(row)

		row.update(get_item_details(row.get("item_code")))
		row.operation_row_id = operation_row_id

		item_row = self.get_item_data(row.name) if row.name else None

		if item_row:
			item_row.update(
				{
					"item_code": row.get("item_code"),
					"qty": row.get("qty"),
				}
			)
		else:
			row.idx = None
			row.name = None
			row.do_not_explode = 1
			row.is_sub_assembly_item = self.is_sub_assembly_item(row.item_code)

			self.append("items", row)

	def is_sub_assembly_item(self, item_code):
		if not self.operations:
			return False

		for row in self.operations:
			if row.finished_good == item_code:
				return True

		return False

	def get_item_data(self, name):
		for row in self.items:
			if row.item_code == name:
				return row

	@frappe.whitelist()
	def add_materials_from_bom(
		self, finished_good: str, bom_no: str, operation_row_id: int, qty: float | None = None
	):
		if not frappe.db.exists("BOM", {"item": finished_good, "name": bom_no, "docstatus": 1}):
			frappe.throw(_("BOM {0} not found for the item {1}").format(bom_no, finished_good))

		if self.items and not self.items[0].item_code:
			self.set("items", [])

		if not qty:
			qty = 1

		for row in self.items:
			if row.operation_row_id == operation_row_id:
				return

		bom_items = get_bom_items(bom_no, self.company, qty=qty, fetch_exploded=0)
		for row in bom_items:
			self._append_bom_material_row(row, operation_row_id)

	def _append_bom_material_row(self, row, operation_row_id):
		row.uom = row.stock_uom
		row.operation_row_id = operation_row_id
		row.idx = None
		row.do_not_explode = 1
		row.is_sub_assembly_item = self.is_sub_assembly_item(row.item_code)

		self.append("items", row)

	def traverse_tree(self, bom_list=None):
		count = 0
		if not bom_list:
			bom_list = []

		if self.name not in bom_list:
			bom_list.append(self.name)

		while count < len(bom_list):
			for child_bom in _get_bom_children(bom_list[count]):
				if child_bom not in bom_list:
					bom_list.append(child_bom)
			count += 1
		bom_list.reverse()
		return bom_list

	def company_currency(self):
		return erpnext.get_company_currency(self.company)

	def validate_bom_links(self):
		if not self.is_active:
			bom_item = frappe.qb.DocType("BOM Item")
			bom = frappe.qb.DocType("BOM")
			act_pbom = (
				frappe.qb.from_(bom_item)
				.join(bom)
				.on(bom.name == bom_item.parent)
				.select(bom_item.parent)
				.distinct()
				.where(
					(bom_item.bom_no == self.name)
					& (bom_item.docstatus == 1)
					& (bom_item.parenttype == "BOM")
					& (bom.docstatus == 1)
					& (bom.is_active == 1)
				)
			).run()

			if act_pbom and act_pbom[0][0]:
				frappe.throw(_("Cannot deactivate or cancel BOM as it is linked with other BOMs"))

	def validate_transfer_against(self):
		if not self.with_operations:
			self.transfer_material_against = "Work Order"
		if not self.transfer_material_against and not self.track_semi_finished_goods and not self.is_new():
			frappe.throw(
				_("Setting {0} is required").format(_(self.meta.get_label("transfer_material_against"))),
				title=_("Missing value"),
			)

	def set_routing_operations(self):
		if self.routing and self.with_operations and not self.operations:
			self.get_routing()

	def validate_operations(self):
		if self.with_operations and not self.get("operations") and self.docstatus == 1:
			frappe.throw(_("Operations cannot be left blank"))

		if self.with_operations:
			for d in self.operations:
				self._validate_operation_row(d)

	def _validate_operation_row(self, d):
		if not d.description:
			d.description = frappe.db.get_value("Operation", d.operation, "description")
		if not d.batch_size or d.batch_size <= 0:
			d.batch_size = 1

		if not d.workstation and not d.workstation_type:
			frappe.throw(
				_("Row {0}: Workstation or Workstation Type is mandatory for an operation {1}").format(
					d.idx, d.operation
				)
			)
		if not d.time_in_mins or d.time_in_mins <= 0:
			frappe.throw(
				_("Row {0}: Operation time should be greater than 0 for operation {1}").format(
					d.idx, d.operation
				)
			)

	def get_tree_representation(self) -> BOMTree:
		"""Get a complete tree representation preserving order of child items."""
		return BOMTree(self.name)

	def set_process_loss_qty(self):
		if self.process_loss_percentage:
			self.process_loss_qty = flt(self.quantity) * flt(self.process_loss_percentage) / 100

		for item in self.secondary_items:
			item.process_loss_qty = flt(
				item.stock_qty * (item.process_loss_per / 100), self.precision("quantity")
			)

	def validate_uoms(self):
		self.validate_uom(self.item, self.uom, self.process_loss_percentage, self.process_loss_qty)
		for item in self.secondary_items:
			self.validate_uom(item.item_code, item.stock_uom, item.process_loss_per, item.process_loss_qty)

	def validate_uom(self, item_code, uom, process_loss_per, process_loss_qty):
		must_be_whole_number = frappe.get_value("UOM", uom, "must_be_whole_number")

		if process_loss_per and process_loss_per > 100:
			frappe.throw(_("Process Loss Percentage cannot be greater than 100"))

		if process_loss_qty and must_be_whole_number and process_loss_qty % 1 != 0:
			msg = f"Item: {frappe.bold(item_code)} with Stock UOM: {frappe.bold(uom)} can't have fractional process loss qty as UOM {frappe.bold(uom)} is a whole Number."
			frappe.throw(msg, title=_("Invalid Process Loss Configuration"))

	def has_scrap_items(self):
		return any(
			d.get("secondary_item_type") == "Scrap" or d.get("is_legacy") for d in self.get("secondary_items")
		)

	def validate_bom_currency(self, item):
		return BOMCostingService(self).validate_bom_currency(item)

	def get_rm_rate(self, arg, notify=True):
		return BOMCostingService(self).get_rm_rate(arg, notify)

	@frappe.whitelist()
	def update_cost(
		self,
		update_parent: bool = True,
		from_child_bom: bool = False,
		update_hour_rate: bool = True,
		save: bool = True,
	):
		return BOMCostingService(self).update_cost(
			update_parent=update_parent,
			from_child_bom=from_child_bom,
			update_hour_rate=update_hour_rate,
			save=save,
		)

	def update_parent_cost(self):
		return BOMCostingService(self).update_parent_cost()

	def get_bom_unitcost(self, bom_no):
		return BOMCostingService(self).get_bom_unitcost(bom_no)

	def calculate_cost(self, save_updates=False, update_hour_rate=False):
		return BOMCostingService(self).calculate_cost(save_updates, update_hour_rate)

	def calculate_op_cost(self, update_hour_rate=False):
		return BOMCostingService(self).calculate_op_cost(update_hour_rate)

	def update_rate_and_time(self, row, update_hour_rate=False):
		return BOMCostingService(self).update_rate_and_time(row, update_hour_rate)

	def calculate_rm_cost(self, save=False):
		return BOMCostingService(self).calculate_rm_cost(save)

	def calculate_secondary_items_costs(self, save=False):
		return BOMCostingService(self).calculate_secondary_items_costs(save)

	def calculate_exploded_cost(self):
		return BOMCostingService(self).calculate_exploded_cost()

	def get_rm_rate_map(self):
		return BOMCostingService(self).get_rm_rate_map()

	def update_exploded_items(self, save=True):
		return BOMExplodedItemsService(self).update_exploded_items(save)

	def get_exploded_items(self):
		return BOMExplodedItemsService(self).get_exploded_items()

	def add_to_cur_exploded_items(self, args):
		return BOMExplodedItemsService(self).add_to_cur_exploded_items(args)

	def get_child_exploded_items(self, bom_no, stock_qty, operation=None):
		return BOMExplodedItemsService(self).get_child_exploded_items(bom_no, stock_qty, operation)

	def add_exploded_items(self, save=True):
		return BOMExplodedItemsService(self).add_exploded_items(save)


def _get_bom_children(bom_no):
	children = frappe.cache().hget("bom_children", bom_no)
	if children is None:
		bom_item = frappe.qb.DocType("BOM Item")
		children = (
			frappe.qb.from_(bom_item)
			.select(bom_item.bom_no)
			.where((bom_item.parent == bom_no) & (bom_item.bom_no != "") & (bom_item.parenttype == "BOM"))
		).run(pluck=True)
		frappe.cache().hset("bom_children", bom_no, children)
	return children


def get_bom_item_rate(args, bom_doc):
	if bom_doc.rm_cost_as_per == "Valuation Rate":
		rate = get_valuation_rate(args) * (args.get("conversion_factor") or 1)
	elif bom_doc.rm_cost_as_per == "Last Purchase Rate":
		rate = (
			flt(args.get("last_purchase_rate"))
			or flt(frappe.db.get_value("Item", args["item_code"], "last_purchase_rate"))
		) * (args.get("conversion_factor") or 1)
	elif bom_doc.rm_cost_as_per == "Price List":
		rate = _get_price_list_item_rate(args, bom_doc)

	return flt(rate)


def _get_price_list_item_rate(args, bom_doc):
	if not bom_doc.buying_price_list:
		frappe.throw(_("Please select Price List"))

	ctx = ItemDetailsCtx(
		{
			"doctype": "BOM",
			"price_list": bom_doc.buying_price_list,
			"qty": args.get("qty") or 1,
			"uom": args.get("uom") or args.get("stock_uom"),
			"stock_uom": args.get("stock_uom"),
			"transaction_type": "buying",
			"company": bom_doc.company,
			"currency": bom_doc.currency,
			"conversion_rate": 1,  # Passed conversion rate as 1 purposefully, as conversion rate is applied at the end of the function
			"conversion_factor": args.get("conversion_factor") or 1,
			"plc_conversion_rate": 1,
			"ignore_party": True,
			"ignore_conversion_rate": True,
		}
	)
	item_doc = frappe.get_cached_doc("Item", args.get("item_code"))
	price_list_data = get_price_list_rate(ctx, item_doc)
	return price_list_data.price_list_rate


def get_valuation_rate(data):
	"""
	1) Get average valuation rate from all warehouses
	2) If no value, get last valuation rate from SLE
	3) If no value, get valuation rate from Item
	"""
	item_code, company = data.get("item_code"), data.get("company")

	valuation_rate = _get_avg_valuation_rate_from_bins(item_code, company, data)

	if (valuation_rate is not None) and valuation_rate <= 0:
		# Explicit null value check. If None, Bins don't exist, neither does SLE
		valuation_rate = _get_last_valuation_rate_from_sle(item_code)

	if not valuation_rate:
		valuation_rate = frappe.db.get_value("Item", item_code, "valuation_rate")

	return flt(valuation_rate)


def _get_avg_valuation_rate_from_bins(item_code, company, data):
	from pypika import Case

	bin_table = frappe.qb.DocType("Bin")
	wh_table = frappe.qb.DocType("Warehouse")
	item_valuation = (
		frappe.qb.from_(bin_table)
		.join(wh_table)
		.on(bin_table.warehouse == wh_table.name)
		.select(
			Case()
			.when(
				Count(bin_table.name) > 0, IfNull(Sum(bin_table.stock_value) / Sum(bin_table.actual_qty), 0.0)
			)
			.else_(None)
			.as_("valuation_rate")
		)
		.where((bin_table.item_code == item_code) & (wh_table.company == company))
	)

	if data.get("set_rate_based_on_warehouse") and data.get("warehouse"):
		item_valuation = item_valuation.where(bin_table.warehouse == data.get("warehouse"))

	return item_valuation.run(as_dict=True)[0].get("valuation_rate")


def _get_last_valuation_rate_from_sle(item_code):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	last_val_rate = (
		frappe.qb.from_(sle)
		.select(sle.valuation_rate)
		.where((sle.item_code == item_code) & (sle.valuation_rate > 0) & (sle.is_cancelled == 0))
		.orderby(sle.posting_datetime, order=frappe.qb.desc)
		.orderby(sle.creation, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=True)

	return flt(last_val_rate[0].get("valuation_rate")) if last_val_rate else 0


def get_list_context(context):
	context.title = _("Bill of Materials")
	# context.introduction = _('Boms')


def get_bom_items_as_dict(
	bom,
	company,
	qty=1,
	fetch_exploded=1,
	fetch_secondary_items=0,
	include_non_stock_items=False,
	fetch_qty_in_stock_uom=True,
):
	item_dict = {}
	opts = frappe._dict(
		qty=qty,
		fetch_exploded=fetch_exploded,
		fetch_secondary_items=fetch_secondary_items,
		include_non_stock_items=include_non_stock_items,
		fetch_qty_in_stock_uom=fetch_qty_in_stock_uom,
	)

	items = _query_bom_items(bom, company, opts)

	for item in items:
		_add_bom_item_to_dict(item_dict, item, company, opts)

	_set_default_accounts_for_items(item_dict, company)

	return item_dict


def _query_bom_items(bom, company, opts):
	track_semi_finished_goods = frappe.get_cached_value("BOM", bom, "track_semi_finished_goods")
	if track_semi_finished_goods or opts.fetch_secondary_items:
		opts.fetch_exploded = 0

	# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
	t = _get_bom_item_tables(opts)
	query = _build_base_bom_items_query(bom, company, opts.qty, t)
	query, group_by = _add_bom_item_columns(query, t, bom, opts, track_semi_finished_goods)
	return query.groupby(*group_by).orderby(Field("idx")).run(as_dict=True)


def _get_bom_item_tables(opts):
	if cint(opts.fetch_exploded):
		bom_item = frappe.qb.DocType("BOM Explosion Item")
		qty_field_col = bom_item.stock_qty
	elif opts.fetch_secondary_items:
		bom_item = frappe.qb.DocType("BOM Secondary Item")
		qty_field_col = bom_item.stock_qty
	else:
		bom_item = frappe.qb.DocType("BOM Item")
		qty_field_col = bom_item.stock_qty if opts.fetch_qty_in_stock_uom else bom_item.qty

	return frappe._dict(
		bom_item=bom_item,
		qty_field_col=qty_field_col,
		bom_doc=frappe.qb.DocType("BOM"),
		item_doc=frappe.qb.DocType("Item"),
		item_default=frappe.qb.DocType("Item Default"),
	)


def _build_base_bom_items_query(bom, company, qty, t):
	return (
		frappe.qb.from_(t.bom_item)
		.join(t.bom_doc)
		.on(t.bom_item.parent == t.bom_doc.name)
		.join(t.item_doc)
		.on(t.item_doc.name == t.bom_item.item_code)
		.left_join(t.item_default)
		.on((t.item_default.parent == t.item_doc.name) & (t.item_default.company == company))
		.select(
			t.bom_item.item_code,
			t.bom_item.idx,
			t.item_doc.item_name,
			(Sum(t.qty_field_col / IfNull(t.bom_doc.quantity, 1)) * qty).as_("qty"),
			t.item_doc.image,
			t.bom_doc.project,
			t.item_doc.stock_uom,
			t.item_doc.item_group,
			t.item_doc.allow_alternative_item,
			t.item_default.default_warehouse,
			t.item_default.expense_account.as_("expense_account"),
			t.item_default.buying_cost_center.as_("cost_center"),
		)
		.where((t.bom_item.docstatus < 2) & (t.bom_doc.name == bom))
	)


def _add_bom_item_columns(query, t, bom, opts, track_semi_finished_goods):
	is_stock_item = cint(not opts.include_non_stock_items)
	stock_item_condition = t.item_doc.is_stock_item.isin([1, is_stock_item])
	amount_col = (Sum(t.bom_item.stock_qty / IfNull(t.bom_doc.quantity, 1)) * t.bom_item.rate * opts.qty).as_(
		"amount"
	)

	if cint(opts.fetch_exploded):
		return _add_exploded_item_columns(query, t, bom, amount_col, stock_item_condition)
	if opts.fetch_secondary_items:
		return _add_secondary_item_columns(query, t, stock_item_condition)
	return _add_normal_item_columns(query, t, amount_col, stock_item_condition, track_semi_finished_goods)


def _add_exploded_item_columns(query, t, bom, amount_col, stock_item_condition):
	bom_item_table = frappe.qb.DocType("BOM Item")
	idx_subquery = (
		frappe.qb.from_(bom_item_table)
		.select(bom_item_table.idx)
		.where((bom_item_table.item_code == t.bom_item.item_code) & (bom_item_table.parent == bom))
		.limit(1)
	)

	query = query.select(
		t.bom_item.source_warehouse,
		t.bom_item.operation,
		t.bom_item.include_item_in_manufacturing,
		t.bom_item.description,
		t.bom_item.rate,
		t.bom_item.sourced_by_supplier,
		amount_col,
		idx_subquery.as_("idx"),
	).where(stock_item_condition)

	return query, [t.bom_item.item_code, t.item_doc.stock_uom, t.bom_item.operation]


def _add_secondary_item_columns(query, t, stock_item_condition):
	query = query.select(
		t.item_doc.description,
		t.bom_item.cost_allocation_per,
		t.bom_item.process_loss_per,
		t.bom_item.secondary_item_type,
		t.bom_item.name,
		t.bom_item.is_legacy,
	).where(stock_item_condition)

	return query, [t.bom_item.item_code]


def _add_normal_item_columns(query, t, amount_col, stock_item_condition, track_semi_finished_goods):
	query = query.select(
		t.bom_item.rate,
		t.bom_item.uom,
		t.bom_item.conversion_factor,
		t.bom_item.source_warehouse,
		t.bom_item.operation,
		t.bom_item.include_item_in_manufacturing,
		t.bom_item.sourced_by_supplier,
		amount_col,
		t.bom_item.description,
		t.bom_item.base_rate.as_("rate"),
		t.bom_item.operation_row_id,
		t.bom_item.is_phantom_item,
		t.bom_item.bom_no,
	).where(stock_item_condition | (t.bom_item.is_phantom_item == 1))

	if track_semi_finished_goods:
		group_by = [t.bom_item.item_code, t.bom_item.operation_row_id, t.item_doc.stock_uom]
	else:
		group_by = [t.bom_item.item_code, t.item_doc.stock_uom, t.bom_item.operation]

	return query, group_by


def _add_bom_item_to_dict(item_dict, item, company, opts):
	key = item.item_code
	if item.operation_row_id:
		key = (item.item_code, item.operation_row_id)

	if item.operation:
		key = (item.item_code, item.operation)

	if item.get("is_phantom_item"):
		_merge_phantom_bom_items(item_dict, item, company, opts)
	elif key in item_dict:
		item_dict[key]["qty"] += flt(item.qty)
	else:
		item_dict[key] = item


def _merge_phantom_bom_items(item_dict, item, company, opts):
	data = get_bom_items_as_dict(
		item.get("bom_no"),
		company,
		qty=item.get("qty"),
		fetch_exploded=opts.fetch_exploded,
		fetch_secondary_items=opts.fetch_secondary_items,
		include_non_stock_items=opts.include_non_stock_items,
		fetch_qty_in_stock_uom=opts.fetch_qty_in_stock_uom,
	)

	for k, v in data.items():
		if item_dict.get(k):
			item_dict[k]["qty"] += flt(v.qty)
		else:
			item_dict[k] = v


def _set_default_accounts_for_items(item_dict, company):
	for item, item_details in item_dict.items():
		for d in [
			["Account", "expense_account", "stock_adjustment_account"],
			["Cost Center", "cost_center", "cost_center"],
			["Warehouse", "default_warehouse", ""],
		]:
			company_in_record = frappe.db.get_value(d[0], item_details.get(d[1]), "company")
			if not item_details.get(d[1]) or (company_in_record and company != company_in_record):
				item_dict[item][d[1]] = frappe.get_cached_value("Company", company, d[2]) if d[2] else None


@frappe.whitelist()
def get_bom_items(bom: str, company: str, qty: float = 1, fetch_exploded: int = 1):
	items = get_bom_items_as_dict(bom, company, qty, fetch_exploded, include_non_stock_items=True).values()
	items = list(items)
	items.sort(key=functools.cmp_to_key(lambda a, b: a.item_code > b.item_code and 1 or -1))
	return items


def validate_bom_no(item, bom_no):
	"""Validate BOM No of sub-contracted items"""
	bom = frappe.get_doc("BOM", bom_no)
	if not bom.is_active:
		frappe.throw(_("BOM {0} must be active").format(bom_no))
	if bom.docstatus != 1:
		if not frappe.in_test:
			frappe.throw(_("BOM {0} must be submitted").format(bom_no))
	if item and not _bom_contains_item(bom, item):
		frappe.throw(_("BOM {0} does not belong to Item {1}").format(bom_no, item))


def _bom_contains_item(bom, item):
	item = item.lower()
	for d in bom.items:
		if d.item_code.lower() == item:
			return True
	for d in bom.secondary_items:
		if d.item_code.lower() == item:
			return True

	return (
		bom.item.lower() == item
		or bom.item.lower() == cstr(frappe.db.get_value("Item", item, "variant_of")).lower()
	)


def get_backflush_based_on(bom_no=None):
	backflush_based_on = None
	if bom_no:
		backflush_based_on = frappe.db.get_value("BOM", bom_no, "backflush_based_on")

	if not backflush_based_on:
		backflush_based_on = frappe.db.get_single_value(
			"Manufacturing Settings", "backflush_raw_materials_based_on"
		)

	return backflush_based_on
