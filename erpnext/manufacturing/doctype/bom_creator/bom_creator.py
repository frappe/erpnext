# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from collections import OrderedDict, defaultdict

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, sbool
from pypika.terms import ValueWrapper

import erpnext
from erpnext.manufacturing.doctype.bom.bom import get_bom_item_rate
from erpnext.setup.utils import get_exchange_rate

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
	"operation",
	"is_phantom_item",
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
		is_phantom: DF.Check
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
		routing: DF.Link | None
		set_rate_based_on_warehouse: DF.Check
		status: DF.Literal["Draft", "Submitted", "In Progress", "Completed", "Failed", "Cancelled"]
		uom: DF.Link | None
	# end: auto-generated types

	def before_save(self):
		self.set_status()

	def validate(self):
		self.set_exchange_rates()
		self.set_conversion_factor()
		self.set_reference_id()
		self.set_is_expandable()
		self.validate_finished_good()
		self.validate_items()
		self.validate_parent_items()
		self.validate_duplicate_item()
		self.validate_no_cycles()
		self.set_rate_for_items()

	def validate_parent_items(self):
		rows = {row.name: row for row in self.items}
		for row in self.items:
			parent = rows.get(row.fg_reference_id)
			if parent and parent.item_code != row.fg_item:
				frappe.throw(
					_("Row #{0}: Parent Row No points to item {1}, not {2}").format(
						row.idx, bold(parent.item_code), bold(row.fg_item)
					)
				)

	def validate_duplicate_item(self):
		# If same items added multiple times under same parent, raise error
		item_map = {}
		for row in self.items:
			if not row.fg_reference_id:
				continue

			key = (row.item_code, row.fg_reference_id)
			if key in item_map:
				frappe.throw(
					_(
						"Item {0} added multiple times under the same parent item {1} at rows {2} and {3}"
					).format(bold(row.item_code), bold(row.fg_item), item_map[key], row.idx),
					title=_("Duplicate Item Under Same Parent"),
				)
			else:
				item_map[key] = row.idx

	def validate_finished_good(self):
		is_stock_item = frappe.get_cached_value("Item", self.item_code, "is_stock_item")
		if is_stock_item and self.is_phantom:
			frappe.throw(_("Phantom BOM cannot be created for stock item {0}.").format(self.item_code))
		elif not is_stock_item and not self.is_phantom:
			frappe.throw(
				_("Non-phantom BOM cannot be created for non-stock item {0}.").format(self.item_code)
			)

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

		if not frappe.db.exists("BOM", {"bom_creator": self.name, "item": self.item_code, "docstatus": 1}):
			has_completed = False

		if has_completed:
			self.status = "Completed"

	def on_cancel(self):
		self.set_status(True)

	def before_submit(self):
		self.validate_fields()
		self.validate_operations_have_routing()
		self.set_status()

	def set_reference_id(self):
		rows_by_name = {row.name: row for row in self.items}
		rows_by_idx = {row.idx: row for row in self.items}
		edited_rows = self.get_rows_with_edited_parent()

		for row in self.items:
			parent = rows_by_name.get(row.fg_reference_id)
			if parent and parent.name != row.name and row.name not in edited_rows:
				row.parent_row_no = str(parent.idx)
				continue

			if row.fg_reference_id == self.name:
				row.parent_row_no = ""
				continue

			parent = rows_by_idx.get(cint(row.parent_row_no)) if row.parent_row_no else None
			if parent and parent.name != row.name:
				row.fg_reference_id = parent.name
			elif row.fg_item == self.item_code:
				row.fg_reference_id = self.name
				row.parent_row_no = ""

	@frappe.whitelist()
	def add_boms(self):
		self.submit()

	def set_rate_for_items(self):
		children = defaultdict(list)
		for row in self.items:
			children[row.fg_reference_id].append(row)

		self.raw_material_cost = self.get_raw_material_cost(self.name, children, set())

	def get_raw_material_cost(self, parent_id, children, visited):
		visited.add(parent_id)
		amount = 0
		for row in children.get(parent_id, []):
			if not row.is_expandable or row.name in visited:
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
						"set_rate_based_on_warehouse": self.set_rate_based_on_warehouse,
						"warehouse": self.default_warehouse,
					},
					self,
				)
				row.rate = self.convert_to_bom_currency(row.rate)
			else:
				row.rate = flt(
					self.get_raw_material_cost(row.name, children, visited)
					/ flt(row.qty or 1)
					* row.conversion_factor
				)

			row.amount = flt(row.rate) * flt(row.qty)
			amount += flt(row.amount)

		return amount

	def convert_to_bom_currency(self, rate):
		if self.rm_cost_as_per == "Price List":
			rate = flt(rate) * flt(self.plc_conversion_rate or 1)

		return flt(rate) / flt(self.conversion_rate or 1)

	def get_rows_with_edited_parent(self):
		before = self.get_doc_before_save()
		if not before:
			return set()

		old_parent_row_no = {row.name: cstr(row.parent_row_no) for row in before.items}
		return {
			row.name
			for row in self.items
			if row.name in old_parent_row_no and cstr(row.parent_row_no) != old_parent_row_no[row.name]
		}

	def set_exchange_rates(self):
		company_currency = erpnext.get_company_currency(self.company)
		if self.currency == company_currency:
			self.conversion_rate = 1
		elif flt(self.conversion_rate) in (0, 1) or (
			not self.is_new() and self.has_value_changed("currency")
		):
			self.conversion_rate = get_exchange_rate(self.currency, company_currency, args="for_buying")

		if self.rm_cost_as_per != "Price List" or not self.buying_price_list:
			self.plc_conversion_rate = 1
			return

		self.price_list_currency = frappe.get_cached_value("Price List", self.buying_price_list, "currency")
		if self.price_list_currency == company_currency:
			self.plc_conversion_rate = 1
		elif flt(self.plc_conversion_rate) in (0, 1) or (
			not self.is_new() and self.has_value_changed("price_list_currency")
		):
			self.plc_conversion_rate = get_exchange_rate(
				self.price_list_currency, company_currency, args="for_buying"
			)

	def set_is_expandable(self):
		parent_ids = {row.fg_reference_id for row in self.items}
		for row in self.items:
			row.is_expandable = 1 if row.name in parent_ids else 0

	def validate_no_cycles(self):
		rows = {row.name: row for row in self.items}
		for row in self.items:
			ancestor_items = set()
			parent = rows.get(row.fg_reference_id)
			while parent and parent.item_code not in ancestor_items:
				ancestor_items.add(parent.item_code)
				parent = rows.get(parent.fg_reference_id)

			if row.item_code == self.item_code or row.item_code in ancestor_items:
				frappe.throw(
					_("Row #{0}: Item {1} cannot be used inside its own sub-assembly").format(
						row.idx, bold(row.item_code)
					)
				)

	def set_conversion_factor(self):
		item_codes = list({row.item_code for row in self.items if not row.conversion_factor})
		uom_factors = {}
		if item_codes:
			uom_factors = {
				(row.parent, row.uom): row.conversion_factor
				for row in frappe.get_all(
					"UOM Conversion Detail",
					filters={"parent": ("in", item_codes), "parenttype": "Item"},
					fields=["parent", "uom", "conversion_factor"],
				)
			}

		for row in self.items:
			if not row.conversion_factor:
				row.conversion_factor = flt(uom_factors.get((row.item_code, row.uom))) or 1.0
			row.stock_qty = flt(row.qty) * flt(row.conversion_factor)

	def validate_fields(self):
		fields = {
			"items": "Items",
		}

		for field, label in fields.items():
			if not self.get(field):
				frappe.throw(_("Please set {0} in BOM Creator {1}").format(_(label), self.name))

	def validate_operations_have_routing(self):
		if self.is_phantom or self.routing:
			return

		for row in self.items:
			if row.operation:
				frappe.throw(
					_(
						"Row #{0}: Item {1} has Operation {2}. Set a Routing to create BOMs with operations."
					).format(row.idx, bold(row.item_code), bold(row.operation)),
					title=_("Routing Required"),
				)

	def on_submit(self):
		self.enqueue_bom_creation()

	@frappe.whitelist()
	def enqueue_create_boms(self):
		self.check_permission("submit")
		self.enqueue_bom_creation()

	def enqueue_bom_creation(self):
		frappe.enqueue_doc(
			"BOM Creator", self.name, "create_boms", queue="short", timeout=600, enqueue_after_commit=True
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

		self.db_set({"status": "In Progress", "error_log": None})

		try:
			production_item_wise_rm = self.get_production_item_wise_rm()
			reverse_tree = OrderedDict(reversed(list(production_item_wise_rm.items())))
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

	def get_production_item_wise_rm(self):
		production_item_wise_rm = OrderedDict({})
		production_item_wise_rm.setdefault(
			(self.item_code, self.name), frappe._dict({"items": [], "bom_no": "", "fg_item_data": self})
		)

		for row in self.items:
			if row.is_expandable and (row.item_code, row.name) not in production_item_wise_rm:
				production_item_wise_rm.setdefault(
					(row.item_code, row.name),
					frappe._dict({"items": [], "bom_no": "", "fg_item_data": row}),
				)

			if not row.fg_reference_id and production_item_wise_rm.get((row.fg_item, row.fg_reference_id)):
				frappe.throw(_("Please set Parent Row No for item {0}").format(row.fg_item))

			key = (row.fg_item, row.fg_reference_id)
			production_item_wise_rm.setdefault(
				key, frappe._dict({"items": [], "bom_no": "", "fg_item_data": row})
			)
			production_item_wise_rm[key]["items"].append(row)

		return production_item_wise_rm

	def create_bom(self, row, production_item_wise_rm):
		bom_creator_item = row.name if row.name != self.name else ""
		existing_bom = frappe.db.get_value(
			"BOM",
			{
				"bom_creator": self.name,
				"item": row.item_code,
				"bom_creator_item": bom_creator_item,
				"docstatus": 1,
			},
		)
		if existing_bom:
			production_item_wise_rm[(row.item_code, row.name)].bom_no = existing_bom
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
				"is_phantom_bom": row.get("is_phantom_item"),
			}
		)

		if row.item_code == self.item_code:
			bom.is_phantom_bom = self.is_phantom
			if not self.is_phantom and (self.routing or self.has_operations()):
				bom.routing = self.routing
				bom.with_operations = 1
				bom.transfer_material_against = "Work Order"

		for field in BOM_FIELDS:
			if self.get(field):
				bom.set(field, self.get(field))

		if self.set_rate_based_on_warehouse and self.default_warehouse:
			bom.default_source_warehouse = self.default_warehouse

		for item in production_item_wise_rm[(row.item_code, row.name)]["items"]:
			bom_no = "" if item.do_not_explode else item.bom_no
			do_not_explode = item.do_not_explode
			if (item.item_code, item.name) in production_item_wise_rm:
				bom_no = production_item_wise_rm.get((item.item_code, item.name)).bom_no
				do_not_explode = 0

			item_args = {}
			for field in BOM_ITEM_FIELDS:
				item_args[field] = item.get(field)

			item_args.update(
				{
					"bom_no": bom_no,
					"do_not_explode": do_not_explode,
					"allow_alternative_item": 1,
					"include_item_in_manufacturing": 1,
				}
			)

			bom.append("items", item_args)

		bom.save(ignore_permissions=True)
		bom.submit()

		production_item_wise_rm[(row.item_code, row.name)].bom_no = bom.name

	@frappe.whitelist()
	def edit_bom_creator(self, docname: str, data: str | dict):
		if docname != self.name and not frappe.db.exists(
			"BOM Creator Item", {"parent": self.name, "name": docname}
		):
			frappe.throw(_("BOM Creator Item with name {0} does not exist").format(docname))

		if isinstance(data, str):
			data = frappe.parse_json(data)

		updated = False
		if docname == self.name:
			if data.get("qty") and flt(data.get("qty")) != flt(self.qty):
				self.qty = flt(data.get("qty"))
				updated = True

		for row in self.items:
			if row.name == docname:
				for key, value in data.items():
					if key in BOM_ITEM_FIELDS and row.get(key) != value:
						if key == "uom":
							row.conversion_factor = 0
						row.set(key, value)
						updated = True
				break

		if updated:
			self.set_rate_for_items()
			self.save()

		frappe.msgprint(_("Updated successfully"), alert=True)

		return self

	def has_operations(self):
		for row in self.items:
			if row.operation:
				return True

		return False

	@frappe.whitelist()
	def get_default_bom(self, item_code) -> str:
		return frappe.get_cached_value("Item", item_code, "default_bom")

	@frappe.whitelist()
	def add_item(self, **kwargs):
		if isinstance(kwargs, str):
			kwargs = frappe.parse_json(kwargs)

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		item_info = get_item_details(kwargs.item_code)

		parent_row_no = ""
		if kwargs.fg_reference_id and self.name != kwargs.fg_reference_id:
			parent_row_no = get_parent_row_no(self, kwargs.fg_reference_id)

		kwargs.update(
			{
				"uom": item_info.stock_uom,
				"stock_uom": item_info.stock_uom,
				"conversion_factor": 1,
			}
		)

		if parent_row_no:
			kwargs.update({"parent_row_no": parent_row_no})

		self.append("items", kwargs)
		self.save()

		return self

	@frappe.whitelist()
	def add_sub_assembly(self, **kwargs):
		if isinstance(kwargs, str):
			kwargs = frappe.parse_json(kwargs)

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		bom_item = frappe.parse_json(kwargs.bom_item)

		name = kwargs.fg_reference_id
		parent_row_no = ""

		if not kwargs.convert_to_sub_assembly:
			item_info = get_item_details(bom_item.item_code)
			parent_row_no = get_parent_row_no(self, kwargs.fg_reference_id)

			item_row = self.append(
				"items",
				{
					"item_code": bom_item.item_code,
					"qty": bom_item.qty,
					"uom": item_info.stock_uom,
					"fg_item": kwargs.fg_item,
					"conversion_factor": 1,
					"parent_row_no": parent_row_no,
					"fg_reference_id": name,
					"stock_qty": bom_item.qty,
					"do_not_explode": 1,
					"is_expandable": 1,
					"stock_uom": item_info.stock_uom,
					"operation": bom_item.operation,
					"is_phantom_item": sbool(kwargs.phantom),
				},
			)

			parent_row_no = item_row.idx
			name = ""
		else:
			if sbool(kwargs.phantom):
				parent_row = next(item for item in self.items if item.name == kwargs.fg_reference_id)
				parent_row.is_phantom_item = 1
			parent_row_no = get_parent_row_no(self, kwargs.fg_reference_id)

		for row in bom_item.get("items"):
			row = frappe._dict(row)
			item_info = get_item_details(row.item_code)
			self.append(
				"items",
				{
					"item_code": row.item_code,
					"qty": row.qty,
					"operation": row.operation,
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

		self.save()

		return self

	@frappe.whitelist()
	def delete_node(self, **kwargs):
		if isinstance(kwargs, str):
			kwargs = frappe.parse_json(kwargs)

		if isinstance(kwargs, dict):
			kwargs = frappe._dict(kwargs)

		updated = False
		if kwargs.docname:
			row = next((row for row in self.items if row.name == kwargs.docname), None)
			if not row:
				frappe.throw(_("BOM Creator Item with name {0} does not exist").format(kwargs.docname))

			self.remove(row)
			updated = True

		if self.remove_child_nodes(kwargs.docname or self.name):
			updated = True

		if updated:
			self.set_rate_for_items()
			self.save()

			return self

		return frappe._dict()

	def remove_child_nodes(self, fg_reference_id: str):
		removed = False
		for row in [row for row in self.items if row.fg_reference_id == fg_reference_id]:
			self.remove(row)
			removed = True
			self.remove_child_nodes(row.name)

		return removed


@frappe.whitelist()
def get_children(doctype: str | None = None, parent: str | None = None, **kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	if not kwargs.parent_id:
		return []

	frappe.has_permission("BOM Creator", "read", doc=kwargs.parent_id, throw=True)

	fields = [
		"name as value",
		"item_name as title",
		"is_expandable as expandable",
		"parent as parent_id",
		"qty",
		"idx",
		ValueWrapper("BOM Creator Item").as_("doctype"),
		"name",
		"item_code",
		"uom",
		"rate",
		"amount",
		"operation",
		"is_subcontracted",
	]

	query_filters = {
		"fg_reference_id": parent,
		"parent": kwargs.parent_id,
	}

	if kwargs.name:
		query_filters["name"] = kwargs.name

	return frappe.get_all("BOM Creator Item", fields=fields, filters=query_filters, order_by="idx")


def get_item_details(item_code):
	return frappe.get_cached_value(
		"Item", item_code, ["item_name", "description", "image", "stock_uom", "default_bom"], as_dict=1
	)


def get_parent_row_no(doc, name):
	for row in doc.items:
		if row.name == name:
			return row.idx

	if name == doc.name:
		return None

	frappe.msgprint(_("Parent Row No not found for {0}").format(name), alert=True)

	return None
