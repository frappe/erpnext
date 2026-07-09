import json
from collections import defaultdict

import frappe
from frappe import _, bold
from frappe.query_builder.functions import Max, Min, Sum
from frappe.utils import ceil, cint, flt, get_link_to_form

from erpnext.manufacturing.doctype.bom.bom import add_additional_cost
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.serial_batch_bundle import (
	SerialBatchCreation,
	get_batch_nos,
	get_batches_from_bundle,
	get_empty_batches_based_work_order,
	get_serial_nos_from_bundle,
)
from erpnext.stock.utils import get_combine_datetime

from .serial_batch import create_serial_and_batch_bundle
from .stock_entry_base import BaseStockEntry


class BaseManufactureStockEntry(BaseStockEntry):
	def set_default_warehouse(self):
		for row in self.doc.items:
			if (
				not row.s_warehouse
				and self.doc.from_warehouse
				and not row.is_finished_item
				and not row.is_legacy_scrap_item
				and not row.secondary_item_type
			):
				row.s_warehouse = self.doc.from_warehouse
				row.t_warehouse = None

			elif (
				not row.t_warehouse
				and self.doc.to_warehouse
				and (row.is_finished_item or row.is_legacy_scrap_item or row.secondary_item_type)
			):
				row.t_warehouse = self.doc.to_warehouse
				row.s_warehouse = None

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.s_warehouse and not row.t_warehouse:
				frappe.throw(_("Source or Target Warehouse is required for item {0}").format(row.item_code))

	def validate_raw_materials_exists(self):
		if frappe.db.get_single_value("Manufacturing Settings", "material_consumption"):
			return

		raw_materials = []
		for row in self.doc.items:
			if row.s_warehouse:
				raw_materials.append(row.item_code)

		if not raw_materials:
			frappe.throw(
				_(
					"At least one raw material item must be present in the stock entry for the type {0}"
				).format(bold(self.doc.purpose)),
				title=_("Raw Materials Missing"),
			)

	def get_item_dict(self, row):
		item_args = {}
		fields = [
			"item_code",
			"item_name",
			"item_group",
			"description",
			"uom",
			"stock_uom",
			"conversion_factor",
			"allow_alternative_item",
		]
		for field in fields:
			if row.get(field):
				item_args[field] = row.get(field)

		return item_args

	def add_secondary_items(self):
		secondary_items = get_secondary_items(self.doc.bom_no, self.doc.work_order)
		for row in secondary_items:
			item_args = self.get_item_dict(row)
			item_args["is_legacy_scrap_item"] = bool(row.get("is_legacy"))
			item_args["secondary_item_type"] = row.secondary_item_type
			item_args["bom_secondary_item"] = row.name

			if row.secondary_item_type == "Scrap" and self.wo_doc and self.wo_doc.get("scrap_warehouse"):
				item_args["t_warehouse"] = self.wo_doc.scrap_warehouse
			else:
				item_args["t_warehouse"] = self.doc.to_warehouse

			if not item_args.get("t_warehouse"):
				item_args["t_warehouse"] = frappe.get_cached_value(
					"BOM", self.doc.bom_no, "default_target_warehouse"
				)

			row.qty = row.qty * self.doc.fg_completed_qty
			if row.get("process_loss_per"):
				row.qty -= flt(
					row.qty * row.get("process_loss_per") / 100, self.doc.precision("fg_completed_qty")
				)

			item_args["qty"] = ceil_qty_if_uom_has_whole_number(row.qty, row.uom)
			item_args["transfer_qty"] = item_args["qty"]
			self.doc.append("items", item_args)

	def set_process_loss_qty(self):
		precision = self.doc.precision("process_loss_qty")
		if self.doc.work_order:
			data = frappe.get_all(
				"Work Order Operation",
				filters={"parent": self.doc.work_order},
				fields=[{"MAX": "process_loss_qty", "as": "process_loss_qty"}],
			)

			if data and data[0].process_loss_qty:
				process_loss_qty = data[0].process_loss_qty
				if flt(self.doc.process_loss_qty, precision) != flt(process_loss_qty, precision):
					self.doc.process_loss_qty = flt(process_loss_qty, precision)

					frappe.msgprint(
						_("The Process Loss Qty has been reset as per the Job Card's Process Loss Qty"),
						alert=True,
					)

		if not self.doc.process_loss_percentage and not self.doc.process_loss_qty:
			self.doc.process_loss_percentage = frappe.get_cached_value(
				"BOM", self.doc.bom_no, "process_loss_percentage"
			)

		if self.doc.process_loss_percentage and not self.doc.process_loss_qty:
			self.doc.process_loss_qty = flt(
				(flt(self.doc.fg_completed_qty) * flt(self.doc.process_loss_percentage)) / 100
			)
		elif self.doc.process_loss_qty and not self.doc.process_loss_percentage:
			self.doc.process_loss_percentage = flt(
				(flt(self.doc.process_loss_qty) / flt(self.doc.fg_completed_qty)) * 100
			)

	def add_finished_goods(self):
		item_details = get_production_item_details(self.doc.work_order, self.doc.bom_no)
		fg_item_qty = flt(self.doc.fg_completed_qty) - flt(self.doc.process_loss_qty)

		item_details.update(
			{
				"conversion_factor": 1,
				"uom": item_details.stock_uom,
				"qty": ceil_qty_if_uom_has_whole_number(fg_item_qty, item_details.stock_uom),
				"t_warehouse": self.doc.to_warehouse
				or frappe.get_cached_value("BOM", self.doc.bom_no, "default_target_warehouse"),
				"s_warehouse": None,
				"is_finished_item": 1,
			}
		)

		item_details["item_code"] = item_details["name"]
		del item_details["name"]

		item_details["transfer_qty"] = item_details["qty"]

		if self.wo_doc and cint(
			frappe.db.get_single_value(
				"Manufacturing Settings", "make_serial_no_batch_from_work_order", cache=True
			)
		):
			if self.wo_doc.has_serial_no:
				self.set_serial_nos_for_finished_good(item_details)
			elif self.wo_doc.has_batch_no:
				self.set_batchwise_finished_goods(item_details)
		else:
			self.doc.append("items", item_details)

	def set_serial_nos_for_finished_good(self, item_details, existing_row=None):
		serial_nos = self.get_available_serial_nos_for_fg(item_details.item_code)
		if not serial_nos:
			return

		row = frappe._dict({"serial_nos": serial_nos[0 : cint(item_details.qty)]})

		_id = create_serial_and_batch_bundle(
			self.doc,
			row,
			frappe._dict(
				{
					"item_code": item_details.item_code,
					"warehouse": item_details.t_warehouse,
				}
			),
		)

		if existing_row:
			existing_row.serial_and_batch_bundle = _id
			existing_row.use_serial_batch_fields = 0
		else:
			item_details.serial_and_batch_bundle = _id
			item_details.use_serial_batch_fields = 0
			self.doc.append("items", item_details)

	def get_available_serial_nos_for_fg(self, item_code) -> list[str]:
		return frappe.get_all(
			"Serial No",
			filters={
				"item_code": item_code,
				"warehouse": ("is", "not set"),
				"status": "Inactive",
				"work_order": self.wo_doc.name,
			},
			pluck="name",
			order_by="creation asc",
		)

	def set_batchwise_finished_goods(self, item_details, existing_row=None):
		batches = get_empty_batches_based_work_order(self.doc.work_order, self.wo_doc.production_item)

		if not batches:
			if not existing_row:
				self.doc.append("items", item_details)
		else:
			self.add_batchwise_finished_good(batches, item_details, existing_row=existing_row)

	def add_batchwise_finished_good(self, batches, item_details, existing_row=None):
		qty = flt(self.doc.fg_completed_qty)
		row = frappe._dict({"batches_to_be_consume": defaultdict(float)})
		self.update_batches_to_be_consume(batches, row, qty)
		if row.batches_to_be_consume:
			self._link_fg_bundle_and_append(item_details, row, existing_row=existing_row)

	def _link_fg_bundle_and_append(self, item_details, row, existing_row=None):
		_id = create_serial_and_batch_bundle(
			self.doc,
			row,
			frappe._dict(
				{"item_code": self.wo_doc.production_item, "warehouse": item_details.get("t_warehouse")}
			),
		)
		if existing_row:
			existing_row.serial_and_batch_bundle = _id
			existing_row.use_serial_batch_fields = 0
		else:
			item_details["serial_and_batch_bundle"] = _id
			item_details["use_serial_batch_fields"] = 0
			self.doc.append("items", item_details)

	def update_batches_to_be_consume(self, batches, row, qty):
		qty_to_be_consumed = qty
		for batch_no, batch_qty in sorted(batches.items(), key=lambda x: x[0]):
			if qty_to_be_consumed <= 0 or batch_qty <= 0:
				continue
			batch_qty = min(batch_qty, qty_to_be_consumed)
			self._consume_batch(row, batch_no, batch_qty)
			qty_to_be_consumed -= batch_qty

	def _consume_batch(self, row, batch_no, batch_qty):
		row.batches_to_be_consume[batch_no] += batch_qty
		if batch_no and row.serial_nos:
			serial_nos = self.get_serial_nos_based_on_transferred_batch(batch_no, row.serial_nos)
			for sn in serial_nos[: cint(batch_qty)]:
				row.serial_nos.remove(sn)
		if "batch_details" in row:
			row.batch_details[batch_no] -= batch_qty


class ManufactureStockEntry(BaseManufactureStockEntry):
	def before_validate(self):
		self.set_default_warehouse()
		self.set_job_card_data()

	def validate(self):
		self.validate_warehouse()
		self.validate_raw_materials_exists()
		self.validate_component_and_quantities()
		self.validate_finished_good_serial_batch_for_work_order()

	def validate_finished_good_serial_batch_for_work_order(self):
		if not (
			self.doc.work_order
			and self.wo_doc
			and self.wo_doc.track_semi_finished_goods != 1
			and cint(
				frappe.db.get_single_value(
					"Manufacturing Settings", "make_serial_no_batch_from_work_order", cache=True
				)
			)
			and (self.wo_doc.has_serial_no or self.wo_doc.has_batch_no)
		):
			return

		for row in self.doc.items:
			if not row.is_finished_item:
				continue

			if self.check_invalid_serial_batch_nos_for_finished_good_item(row):
				self.reset_serial_batch_on_fg_row(row)
				frappe.msgprint(
					_(
						"Row {0}: Serial/Batch has been reset to values linked with Work Order {1}"
						" because the previously selected serial/batch does not belong to this Work Order."
					).format(row.idx, frappe.bold(self.doc.work_order))
				)

	def check_invalid_serial_batch_nos_for_finished_good_item(self, row) -> bool:
		if self.wo_doc.has_serial_no:
			serial_nos = get_serial_nos(row.serial_no) if row.serial_no else []
			if not serial_nos and row.serial_and_batch_bundle:
				serial_nos = get_serial_nos_from_bundle(row.serial_and_batch_bundle)
			if serial_nos:
				valid_serial_nos = frappe.get_all(
					"Serial No",
					filters={"name": ("in", serial_nos), "work_order": self.doc.work_order},
					pluck="name",
				)
				return bool(set(serial_nos) - set(valid_serial_nos))
			else:
				return True

		if self.wo_doc.has_batch_no:
			batch_nos = [row.batch_no] if row.batch_no else []
			if not batch_nos and row.serial_and_batch_bundle:
				batch_nos = list(get_batches_from_bundle(row.serial_and_batch_bundle).keys())
			if batch_nos:
				valid_batch_nos = frappe.get_all(
					"Batch",
					filters={"name": ("in", batch_nos), "reference_name": self.doc.work_order},
					pluck="name",
				)
				return bool(set(batch_nos) - set(valid_batch_nos))
			else:
				return True

	def reset_serial_batch_on_fg_row(self, row):
		item_details = frappe._dict(
			{
				"item_code": row.item_code,
				"t_warehouse": row.t_warehouse,
				"qty": row.qty,
			}
		)

		row.serial_no = None
		row.batch_no = None
		row.serial_and_batch_bundle = None

		if self.wo_doc.has_serial_no:
			self.set_serial_nos_for_finished_good(item_details, existing_row=row)
		elif self.wo_doc.has_batch_no:
			self.set_batchwise_finished_goods(item_details, existing_row=row)

	def set_job_card_data(self):
		if self.doc.job_card and not self.doc.work_order:
			data = frappe.db.get_value(
				"Job Card",
				self.doc.job_card,
				["for_quantity", "work_order", "bom_no", "semi_fg_bom"],
				as_dict=1,
			)
			self.doc.fg_completed_qty = data.for_quantity
			self.doc.work_order = data.work_order
			self.doc.from_bom = 1
			self.doc.bom_no = data.semi_fg_bom or data.bom_no

	def validate_component_and_quantities(self):
		if not frappe.db.get_single_value("Manufacturing Settings", "validate_components_quantities_per_bom"):
			return

		if not self.doc.fg_completed_qty:
			return

		rm_items = [item for item in self.doc.items if item.s_warehouse]
		if not rm_items:
			return

		_check_bom_component_qty(self.doc, get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom))

	def validate_work_order(self):
		if not self.doc.work_order:
			frappe.throw(_("Work Order is mandatory"))

	def add_items(self):
		self.add_raw_materials()
		self.set_process_loss_qty()
		self.add_finished_goods()
		self.add_secondary_items()
		self.add_additional_cost()
		self.add_secondary_items_from_job_card()

	def add_raw_materials(self):
		material_consumption = frappe.db.get_single_value("Manufacturing Settings", "material_consumption")

		if material_consumption and self.raw_materials_already_consumed():
			return

		if not material_consumption:
			if self.backflush_based_on == "BOM" or self.wo_doc.skip_transfer:
				self.add_raw_materials_based_on_work_order()
			else:
				self.add_raw_materials_based_on_transfer()
		elif self.backflush_based_on == "BOM":
			self.add_unconsumed_raw_materials()
		else:
			self.add_raw_materials_based_on_transfer()

	def raw_materials_already_consumed(self) -> bool:
		if not self.doc.work_order:
			return False

		return bool(
			frappe.db.exists(
				"Stock Entry",
				{
					"work_order": self.doc.work_order,
					"purpose": "Material Consumption for Manufacture",
					"docstatus": 1,
				},
			)
		)

	def add_unconsumed_raw_materials(self):
		wo = self.wo_doc
		if not wo:
			return
		work_order_qty = flt(wo.material_transferred_for_manufacturing) or flt(wo.qty)
		wo_qty_to_produce = work_order_qty - flt(wo.produced_qty)
		for item in wo.get("required_items"):
			self._append_unconsumed_item(item, wo, wo_qty_to_produce)

	def _append_unconsumed_item(self, item, wo, wo_qty_to_produce):
		wo_item_qty = flt(item.transferred_qty) or flt(item.required_qty)
		wo_qty_unconsumed = wo_item_qty - flt(item.consumed_qty)
		bom_qty_per_unit = flt(item.required_qty) / flt(wo.qty)
		req_qty_each = min(wo_qty_unconsumed / (wo_qty_to_produce or 1), bom_qty_per_unit)
		qty = req_qty_each * flt(self.doc.fg_completed_qty)
		if qty <= 0:
			return
		item_args = self.get_item_dict(item)
		item_args.update(
			{
				"conversion_factor": 1,
				"s_warehouse": wo.wip_warehouse or item.source_warehouse,
				"uom": item.stock_uom,
				"qty": ceil_qty_if_uom_has_whole_number(qty, item.stock_uom),
			}
		)
		item_args["transfer_qty"] = item_args["qty"]
		self.doc.append("items", item_args)

	def add_raw_materials_based_on_work_order(self):
		bom_items = (
			self.wo_doc.get("required_items")
			if self.wo_doc
			else get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)
		)
		alternative_items = self.get_alternative_items(bom_items)
		for row in bom_items:
			self._append_wo_raw_material(row, alternative_items)

	def _append_wo_raw_material(self, row, alternative_items):
		item_args = self.get_item_dict(row)
		item_args.update(
			{
				"conversion_factor": 1,
				"item_group": row.get("item_group"),
				"s_warehouse": self._resolve_rm_warehouse(row),
				"uom": row.stock_uom,
			}
		)
		qty = (
			(row.required_qty / self.wo_doc.qty) * self.doc.fg_completed_qty
			if self.wo_doc
			else flt(row.qty) * self.doc.fg_completed_qty
		)
		item_args["qty"] = ceil_qty_if_uom_has_whole_number(qty, row.stock_uom)
		item_args["transfer_qty"] = item_args["qty"]
		if alt := alternative_items.get(row.item_code):
			self.set_alternative_item_details(item_args, alt)
		self.doc.append("items", item_args)

	def _resolve_rm_warehouse(self, row):
		if self.doc.from_warehouse:
			return self.doc.from_warehouse
		if self.wo_doc and self.wo_doc.from_wip_warehouse:
			return self.wo_doc.wip_warehouse
		if s_warehouse := frappe.get_cached_value("BOM", self.doc.bom_no, "default_source_warehouse"):
			return s_warehouse
		return row.get("source_warehouse")

	def get_alternative_items(self, bom_items):
		item_codes_in_bom = [row.item_code for row in bom_items]
		data = self._query_alternative_items(item_codes_in_bom)
		if not data:
			return frappe._dict()
		return self._index_alternative_items(data)

	def _query_alternative_items(self, item_codes_in_bom):
		doctype = frappe.qb.DocType("Stock Entry")
		child_doc = frappe.qb.DocType("Stock Entry Detail")
		query = (
			frappe.qb.from_(child_doc)
			.inner_join(doctype)
			.on(child_doc.parent == doctype.name)
			.select(
				child_doc.item_code,
				child_doc.uom,
				child_doc.stock_uom,
				child_doc.conversion_factor,
				child_doc.item_name,
				child_doc.item_group,
				child_doc.description,
				child_doc.original_item,
			)
			.where(
				(doctype.work_order == self.doc.work_order)
				& (doctype.purpose == "Material Transfer for Manufacture")
				& (doctype.docstatus == 1)
			)
		)
		if item_codes_in_bom:
			query = query.where(child_doc.original_item.isin(item_codes_in_bom))
		return query.run(as_dict=1)

	def _index_alternative_items(self, data):
		alternative_items = frappe._dict()
		for row in data:
			alternative_items[row.original_item] = row
			alternative_items[row.original_item].original_item = None
		return alternative_items

	def set_alternative_item_details(self, row, alternative_item_details):
		if self.doc.work_order and row.get("allow_alternative_item") is None:
			row["allow_alternative_item"] = self.wo_doc.allow_alternative_item

		if row["allow_alternative_item"]:
			original_item = row["item_code"]
			row.update(alternative_item_details)
			row["original_item"] = original_item

	def add_raw_materials_based_on_transfer(self):
		self.prepare_available_materials_based_on_transfer()
		pending_qty_to_mfg = flt(self.doc.fg_completed_qty)
		if self.doc.work_order:
			pending_qty_to_mfg = flt(self.wo_doc.material_transferred_for_manufacturing) - flt(
				self.wo_doc.produced_qty
			)
		if pending_qty_to_mfg <= 0 and not self.doc.get("is_return"):
			return
		for key in self.available_materials:
			self._append_transfer_based_rm(self.available_materials[key], pending_qty_to_mfg)

	def _append_transfer_based_rm(self, row, pending_qty_to_mfg):
		item_args = self.get_item_dict(row)
		is_return = self.doc.get("is_return")
		qty = row.qty if is_return else (flt(row.qty) * flt(self.doc.fg_completed_qty)) / pending_qty_to_mfg
		item_args["qty"] = ceil_qty_if_uom_has_whole_number(qty, row.uom)
		item_args["transfer_qty"] = item_args["qty"]
		if is_return:
			item_args["s_warehouse"], item_args["t_warehouse"] = row.s_warehouse, row.t_warehouse
		else:
			item_args["t_warehouse"], item_args["s_warehouse"] = None, row.warehouse
		if row.serial_nos or row.batches:
			self.assign_serial_batches_to_materials(item_args, row, qty)
		else:
			self.doc.append("items", item_args)

	def assign_serial_batches_to_materials(self, item_args, row, qty):
		if row.serial_nos:
			self._append_with_serial_nos(item_args, row, qty)
		elif len(row.batches) == 1:
			self._append_with_single_batch(item_args, row)
		elif row.batches:
			self.split_items_based_on_batches(qty, item_args, row)

	def _append_with_serial_nos(self, item_args, row, qty):
		if serial_nos := row.serial_nos[: cint(qty)]:
			item_args["serial_no"] = "\n".join(serial_nos)
		if not item_args.get("uom"):
			item_args["uom"] = row.stock_uom
		item_args["use_serial_batch_fields"] = 1
		self.doc.append("items", item_args)

	def _append_with_single_batch(self, item_args, row):
		item_args["batch_no"] = next(iter(row.batches.keys()))
		if not item_args.get("uom"):
			item_args["uom"] = row.stock_uom
		item_args["use_serial_batch_fields"] = 1
		self.doc.append("items", item_args)

	def split_items_based_on_batches(self, qty, item_args, row):
		for batch_no, batch_qty in row.batches.items():
			if qty <= 0:
				return
			qty = self._append_batch_split_item(item_args, row, batch_no, batch_qty, qty)

	def _append_batch_split_item(self, item_args, row, batch_no, batch_qty, qty):
		if batch_qty >= qty:
			item_args["qty"], qty = qty, 0
		else:
			item_args["qty"] = batch_qty
			qty -= batch_qty
		row.batches[batch_no] -= batch_qty
		if not item_args.get("uom"):
			item_args["uom"] = row.stock_uom
		item_args["batch_no"] = batch_no
		item_args["transfer_qty"] = item_args["qty"]
		item_args["use_serial_batch_fields"] = 1
		self.doc.append("items", item_args)
		return qty

	def prepare_available_materials_based_on_transfer(self):
		self.available_materials = frappe._dict()
		self._transfer_entries = self.get_transfer_entries()
		if not self._transfer_entries:
			return

		self.add_materials_from_transfer()
		self._consumption_entries = self.get_consumption_entries()
		if not self._consumption_entries:
			return

		self.remove_consumed_materials_from_available()

	def return_available_materials_in_source_wh(self):
		for row in self.doc.items:
			row.s_warehouse, row.t_warehouse = row.t_warehouse, row.s_warehouse

	def get_transfer_entries(self):
		stock_entry = frappe.qb.DocType("Stock Entry")
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

		return (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry.name == stock_entry_detail.parent)
			.select(stock_entry_detail.star)
			.where(
				(stock_entry.work_order == self.doc.work_order)
				& (stock_entry.purpose == "Material Transfer for Manufacture")
				& (stock_entry.docstatus == 1)
			)
			.orderby(stock_entry_detail.idx)
		).run(as_dict=1)

	def add_materials_from_transfer(self):
		for row in self._transfer_entries:
			row.warehouse = row.t_warehouse
			key = (row.item_code, row.warehouse)
			if key not in self.available_materials:
				self.available_materials[key] = frappe._dict(row)
			else:
				self.available_materials[key].qty += row.qty

			if row.serial_and_batch_bundle:
				self.available_materials[key].update(self.get_sabb_details(row.serial_and_batch_bundle))

	def get_consumption_entries(self):
		stock_entry = frappe.qb.DocType("Stock Entry")
		stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")

		return (
			frappe.qb.from_(stock_entry)
			.inner_join(stock_entry_detail)
			.on(stock_entry.name == stock_entry_detail.parent)
			.select(stock_entry_detail.star)
			.where(
				(stock_entry.work_order == self.doc.work_order)
				& (stock_entry_detail.s_warehouse.isnotnull())
				& (stock_entry.purpose == "Manufacture")
				& (stock_entry.docstatus == 1)
			)
			.orderby(stock_entry_detail.idx)
		).run(as_dict=1)

	def remove_consumed_materials_from_available(self):
		for row in self._consumption_entries:
			row.warehouse = row.s_warehouse
			key = (row.item_code, row.warehouse)
			self.available_materials[key].qty -= row.qty
			if row.serial_and_batch_bundle:
				self._deduct_consumed_serial_batch(key, row.serial_and_batch_bundle)

	def _deduct_consumed_serial_batch(self, key, sabb_name):
		_details = self.get_sabb_details(sabb_name)
		if _details.serial_nos:
			for sn in _details.serial_nos:
				self.available_materials[key].serial_nos.remove(sn)
		elif _details.batches:
			for batch_no, qty in _details.batches.items():
				# qty is negative, so add instead of subtract
				self.available_materials[key].batches[batch_no] += qty

	def add_additional_cost(self):
		if not self.wo_doc:
			return

		add_additional_cost(self.doc, self.wo_doc)

	def add_secondary_items_from_job_card(self):
		if not self.wo_doc:
			return

		secondary_items = self.get_secondary_items_from_job_card()
		for row in secondary_items:
			row.uom = row.uom or row.stock_uom
			row.qty = ceil_qty_if_uom_has_whole_number(row.stock_qty, row.stock_uom)
			row.transfer_qty = row.qty
			row.s_warehouse = None
			row.t_warehouse = row.warehouse or self.doc.to_warehouse
			row.is_legacy_scrap_item = row.is_legacy
			row.secondary_item_type = row.get("secondary_item_type")

			self.doc.append("items", row)

	def get_secondary_items_from_job_card(self):
		if not self.wo_doc.operations:
			return []
		secondary_items = get_secondary_items_from_job_card(self.doc.work_order, self.doc.job_card)
		pending_qty = self._get_pending_secondary_qty()
		used_secondary_items = self.get_used_secondary_items()
		self._adjust_secondary_item_qtys(secondary_items, used_secondary_items, pending_qty)
		return secondary_items

	def _get_pending_secondary_qty(self):
		if self.doc.job_card:
			return flt(self.doc.fg_completed_qty)
		return flt(self.get_completed_job_card_qty()) - flt(self.wo_doc.produced_qty)

	def _adjust_secondary_item_qtys(self, secondary_items, used_secondary_items, pending_qty):
		for row in secondary_items:
			row.stock_qty -= flt(used_secondary_items.get(row.item_code))
			row.stock_qty = row.stock_qty * flt(self.doc.fg_completed_qty) / flt(pending_qty)
			if used_secondary_items.get(row.item_code):
				used_secondary_items[row.item_code] -= row.stock_qty

	def get_used_secondary_items(self):
		data = self._query_used_secondary_items()
		used_secondary_items = defaultdict(float)
		for row in data:
			used_secondary_items[row.item_code] += row.qty
		return used_secondary_items

	def _query_used_secondary_items(self):
		se = frappe.qb.DocType("Stock Entry")
		sed = frappe.qb.DocType("Stock Entry Detail")
		return (
			frappe.qb.from_(se)
			.inner_join(sed)
			.on(sed.parent == se.name)
			.select(sed.item_code, sed.qty)
			.where(
				(se.work_order == self.doc.work_order)
				& ((sed.secondary_item_type.isnotnull()) | (sed.is_legacy_scrap_item == 1))
				& (se.docstatus == 1)
				& (se.purpose.isin(["Repack", "Manufacture"]))
			)
		).run(as_dict=1)

	def get_completed_job_card_qty(self):
		return flt(min([d.completed_qty for d in self.wo_doc.operations]))

	def get_sabb_details(self, sabb):
		sabb_entries = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": sabb, "docstatus": 1, "is_cancelled": 0},
			fields=["serial_no", "batch_no", "qty"],
			order_by="idx",
		)

		serial_nos = []
		batches = defaultdict(float)

		for row in sabb_entries:
			if row.serial_no:
				serial_nos.append(row.serial_no)
			else:
				batches[row.batch_no] += row.qty

		return frappe._dict({"serial_nos": serial_nos, "batches": batches})

	def on_submit(self):
		self.update_job_card_and_work_order()

	def on_cancel(self):
		self.update_job_card_and_work_order()

	def update_job_card_and_work_order(self):
		if self.doc.job_card:
			self._update_job_card_on_manufacture()
		if self.doc.work_order:
			self._update_work_order_on_manufacture()

	def _update_job_card_on_manufacture(self):
		job_doc = frappe.get_doc("Job Card", self.doc.job_card)
		job_doc.set_consumed_qty_in_job_card_item(self.doc)
		job_doc.set_manufactured_qty()
		job_doc.update_work_order()

	def _update_work_order_on_manufacture(self):
		self._validate_work_order()
		if self.doc.fg_completed_qty:
			self.wo_doc.run_method("update_work_order_qty")
			self.wo_doc.run_method("update_planned_qty")
		self.wo_doc.run_method("update_status")
		if not self.wo_doc.operations:
			self.wo_doc.set_actual_dates()


class RepackStockEntry(BaseManufactureStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_raw_materials_exists()
		self.validate_repack_entry()

	def validate_repack_entry(self):
		fg_items = {row.item_code: row for row in self.doc.items if row.is_finished_item}

		if len(fg_items) > 1 and not all(row.set_basic_rate_manually for row in fg_items.values()):
			frappe.throw(
				_(
					"When there are multiple finished goods ({0}) in a Repack stock entry, the basic rate for all finished goods must be set manually. To set rate manually, enable the checkbox 'Set Basic Rate Manually' in the respective finished good row."
				).format(", ".join(fg_items)),
				title=_("Set Basic Rate Manually"),
			)

	def add_items(self):
		self.add_raw_materials_based_on_bom()
		self.set_process_loss_qty()
		self.add_finished_goods()
		self.add_secondary_items()

	def add_raw_materials_based_on_bom(self):
		bom_items = get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)

		for row in bom_items:
			row.s_warehouse = self.doc.from_warehouse
			row.qty = row.qty * self.doc.fg_completed_qty
			row.transfer_qty = row.qty
			if not row.uom:
				row.uom = row.stock_uom

			self.doc.append("items", row)


class MaterialConsumptionForManufactureStockEntry(ManufactureStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_work_order()

	def add_items(self):
		if self.backflush_based_on == "BOM" or self.wo_doc.skip_transfer:
			self.add_raw_materials_based_on_work_order()
		else:
			self.add_raw_materials_based_on_transfer()


def get_production_item_details(work_order=None, bom_no=None):
	production_item = (
		frappe.get_cached_value("Work Order", work_order, "production_item")
		if work_order
		else frappe.get_cached_value("BOM", bom_no, "item")
	)
	return frappe.get_cached_value(
		"Item",
		production_item,
		["item_name", "item_group", "description", "stock_uom", "name"],
		as_dict=1,
	)


def _check_bom_component_qty(doc, bom_items):
	"""Validate that stock entry items match BOM quantities."""
	precision = frappe.get_precision("Stock Entry Detail", "qty")
	for row in bom_items:
		row.qty = row.qty * doc.fg_completed_qty
		matched_item = next(
			(
				item
				for item in doc.items
				if item.s_warehouse
				and (item.item_code == row.item_code or item.original_item == row.item_code)
			),
			None,
		)
		if matched_item:
			if flt(row.qty, precision) != flt(matched_item.qty, precision):
				frappe.throw(
					_(
						"For the item {0}, the consumed quantity should be {1} according to the BOM {2}."
					).format(
						bold(row.item_code),
						flt(row.qty),
						get_link_to_form("BOM", doc.bom_no),
					),
					title=_("Incorrect Component Quantity"),
				)
		else:
			frappe.throw(
				_("According to the BOM {0}, the Item '{1}' is missing in the stock entry.").format(
					get_link_to_form("BOM", doc.bom_no), bold(row.item_code)
				),
				title=_("Missing Item"),
			)


def get_bom_items(bom_no, use_multi_level_bom=None, qty=None, fetch_secondary_items=False):
	if use_multi_level_bom is None:
		use_multi_level_bom = frappe.get_cached_value("BOM", bom_no, "use_multi_level_bom")
	qty = qty or 1

	if fetch_secondary_items:
		table_name = "BOM Secondary Item"
	else:
		table_name = "BOM Explosion Item" if use_multi_level_bom else "BOM Item"

	items = _run_bom_items_query(bom_no, table_name, qty)
	return _deduplicate_bom_items(items)


def _run_bom_items_query(bom_no, table_name, qty):
	bom_doc = frappe.qb.DocType("BOM")
	doctype = frappe.qb.DocType(table_name)
	query = (
		frappe.qb.from_(doctype)
		.inner_join(bom_doc)
		.on(doctype.parent == bom_doc.name)
		.select(
			doctype.item_code,
			doctype.item_name,
			doctype.stock_uom,
			doctype.description,
			(doctype.stock_qty / bom_doc.quantity.as_("qty") * qty).as_("qty"),
			doctype.rate.as_("basic_rate"),
		)
		.where((bom_doc.name == bom_no) & (bom_doc.docstatus == 1))
		.orderby(doctype.idx)
	)
	return _add_bom_table_specific_fields(query, doctype, table_name).run(as_dict=1)


def _add_bom_table_specific_fields(query, doctype, table_name):
	if table_name == "BOM Secondary Item":
		return query.select(
			doctype.name,
			doctype.cost_allocation_per,
			doctype.uom,
			doctype.process_loss_per,
			doctype.secondary_item_type,
			doctype.is_legacy,
			doctype.conversion_factor,
		)
	if table_name == "BOM Item":
		return query.select(
			doctype.allow_alternative_item, doctype.uom, doctype.conversion_factor, doctype.bom_no
		)
	return query


def _deduplicate_bom_items(items):
	item_dict = {}
	for item in items:
		if item.item_code in item_dict:
			item_dict[item.item_code].qty += item.qty
		else:
			item_dict[item.item_code] = item
	return list(item_dict.values())


def get_secondary_items(bom_no, work_order=None):
	if (
		frappe.db.get_single_value(
			"Manufacturing Settings", "set_op_cost_and_secondary_items_from_sub_assemblies"
		)
		and work_order
		and frappe.get_cached_value("Work Order", work_order, "use_multi_level_bom")
	):
		return get_secondary_items_from_sub_assemblies(bom_no)
	else:
		return get_bom_items(bom_no, fetch_secondary_items=True)


def get_secondary_items_from_sub_assemblies(bom_no):
	items = []
	bom_items = get_bom_items(bom_no)
	for row in bom_items:
		if not row.bom_no:
			continue

		items.extend(get_bom_items(row.bom_no, qty=row.qty, fetch_secondary_items=True))
		items.extend(get_secondary_items_from_sub_assemblies(row.bom_no))

	return items


def get_secondary_items_from_job_card(work_order, jc_name=None):
	job_card = frappe.qb.DocType("Job Card")
	job_card_secondary_item = frappe.qb.DocType("Job Card Secondary Item")

	secondary_items = (
		frappe.qb.from_(job_card)
		.select(
			Sum(job_card_secondary_item.stock_qty).as_("stock_qty"),
			job_card_secondary_item.item_code,
			# non-grouped columns are item attributes / the secondary-item BOM link, constant per
			# grouped (item_code, secondary_item_type) -> Max() keeps the GROUP BY valid on postgres
			# while returning the value MySQL picked arbitrarily.
			Max(job_card_secondary_item.item_name).as_("item_name"),
			Max(job_card_secondary_item.description).as_("description"),
			Max(job_card_secondary_item.stock_uom).as_("stock_uom"),
			job_card_secondary_item.secondary_item_type,
			Max(job_card_secondary_item.bom_secondary_item).as_("bom_secondary_item"),
		)
		.join(job_card_secondary_item)
		.on(job_card_secondary_item.parent == job_card.name)
		.where(
			(job_card_secondary_item.item_code.isnotnull())
			& (job_card.work_order == work_order)
			& (job_card.docstatus == 1)
		)
		.groupby(job_card_secondary_item.item_code, job_card_secondary_item.secondary_item_type)
		.orderby(Min(job_card_secondary_item.idx))
	)

	if jc_name:
		secondary_items = secondary_items.where(job_card.name == jc_name)

	return secondary_items.run(as_dict=1)


def get_previous_operation_output_sn_batch(work_order, item_code, warehouse):
	"""Serial nos / batches that an earlier operation produced for ``item_code`` (a
	semi-finished good) and are still available in ``warehouse`` -- i.e. produced by a
	prior operation's Manufacture entry minus whatever later entries already pulled out
	of that warehouse. Returns an empty result for ordinary raw materials."""
	result = frappe._dict(serial_nos=[], batches=defaultdict(float))
	if not (work_order and item_code and warehouse):
		return result

	# Only items that are the output (finished_good) of some operation qualify.
	if not frappe.db.exists("Work Order Operation", {"parent": work_order, "finished_good": item_code}):
		return result

	item_details = frappe.get_cached_value("Item", item_code, ["has_serial_no", "has_batch_no"], as_dict=1)
	if not item_details or not (item_details.has_serial_no or item_details.has_batch_no):
		return result

	produced = _get_operation_sn_batch(work_order, item_code, warehouse, produced=True)
	consumed = _get_operation_sn_batch(work_order, item_code, warehouse, produced=False)

	for serial_no in produced.serial_nos:
		if serial_no not in consumed.serial_nos:
			result.serial_nos.append(serial_no)

	for batch_no, qty in produced.batches.items():
		available = flt(qty) - flt(consumed.batches.get(batch_no))
		if available > 0:
			result.batches[batch_no] = available

	return result


def _get_operation_sn_batch(work_order, item_code, warehouse, produced=True):
	bundles = _get_operation_bundles(work_order, item_code, warehouse, produced)
	result = frappe._dict(serial_nos=[], batches=defaultdict(float))
	if not bundles:
		return result

	sbe = frappe.qb.DocType("Serial and Batch Entry")
	entries = (
		frappe.qb.from_(sbe)
		.select(sbe.serial_no, sbe.batch_no, sbe.qty)
		.where((sbe.parent.isin(bundles)) & (sbe.is_cancelled == 0))
		.orderby(sbe.parent)
		.orderby(sbe.idx)
	).run(as_dict=True)

	for row in entries:
		if row.serial_no:
			result.serial_nos.append(row.serial_no)
		if row.batch_no:
			result.batches[row.batch_no] += abs(flt(row.qty))

	return result


def _get_operation_bundles(work_order, item_code, warehouse, produced):
	se = frappe.qb.DocType("Stock Entry")
	sed = frappe.qb.DocType("Stock Entry Detail")
	warehouse_field = sed.t_warehouse if produced else sed.s_warehouse

	query = (
		frappe.qb.from_(se)
		.inner_join(sed)
		.on(sed.parent == se.name)
		.select(sed.serial_and_batch_bundle)
		.where(
			(se.work_order == work_order)
			& (se.docstatus == 1)
			& (sed.item_code == item_code)
			& (warehouse_field == warehouse)
			& (sed.serial_and_batch_bundle.isnotnull())
		)
	)
	if produced:
		query = query.where((se.purpose == "Manufacture") & (sed.is_finished_item == 1))

	return [row[0] for row in query.run()]


def _cap_pool_to_qty(pool, qty):
	"""Trim the available serial/batch pool to at most ``qty`` (fill what's available)."""
	serial_nos, batches = [], frappe._dict()
	if pool.serial_nos:
		serial_nos = pool.serial_nos[: cint(qty)]
	elif pool.batches:
		remaining = flt(qty)
		for batch_no, batch_qty in pool.batches.items():
			if remaining <= 0:
				break
			use = min(flt(batch_qty), remaining)
			batches[batch_no] = use
			remaining -= use
	return serial_nos, batches


def set_previous_operation_serial_batch(parent_doc, row):
	"""Auto-pull serial nos / batches produced by a previous operation onto a
	consumption / transfer-out ``row`` of a Stock Entry, filling what is available and
	leaving any shortfall blank for the user. No-op for ordinary raw materials or when
	the row already carries serial/batch."""
	warehouse = row.get("s_warehouse")
	qty = flt(row.get("qty")) * flt(row.get("conversion_factor") or 1)

	if not parent_doc.get("work_order") or not warehouse or qty <= 0:
		return
	if row.get("serial_and_batch_bundle") or row.get("serial_no") or row.get("batch_no"):
		return

	pool = get_previous_operation_output_sn_batch(parent_doc.work_order, row.item_code, warehouse)
	serial_nos, batches = _cap_pool_to_qty(pool, qty)
	if not serial_nos and not batches:
		return

	bundle = SerialBatchCreation(
		{
			"item_code": row.item_code,
			"warehouse": warehouse,
			"posting_datetime": get_combine_datetime(parent_doc.posting_date, parent_doc.posting_time),
			"voucher_type": "Stock Entry",
			"company": parent_doc.company,
			"type_of_transaction": "Outward",
			"qty": flt(qty),
			"serial_nos": serial_nos,
			"batches": batches,
			"do_not_submit": True,
		}
	).make_serial_and_batch_bundle()

	if bundle and bundle.get("name"):
		row.serial_and_batch_bundle = bundle.name
		row.use_serial_batch_fields = 0


def ceil_qty_if_uom_has_whole_number(qty, stock_uom):
	if cint(frappe.get_cached_value("UOM", stock_uom, "must_be_whole_number")):
		qty = ceil(qty)

	return qty


@frappe.whitelist()
def move_sample_to_retention_warehouse(company: str, items: str | list):
	items = frappe.parse_json(items)

	retention_warehouse = frappe.get_single_value("Stock Settings", "sample_retention_warehouse")
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.company = company
	stock_entry.purpose = "Material Transfer"
	stock_entry.set_stock_entry_type()

	for item in items:
		if item.get("sample_quantity") and item.get("serial_and_batch_bundle"):
			_process_sample_item(stock_entry, item, retention_warehouse)

	if stock_entry.get("items"):
		return stock_entry.as_dict()


def _process_sample_item(stock_entry, item, retention_warehouse):
	warehouse = item.get("t_warehouse") or item.get("warehouse")
	sabb = _duplicate_sample_bundle(item, warehouse)
	total_qty, sabe_list = _collect_sample_batches(sabb, item, warehouse)
	if total_qty:
		_append_sample_entry(stock_entry, sabb, item, warehouse, retention_warehouse, total_qty, sabe_list)


def _duplicate_sample_bundle(item, warehouse):
	return SerialBatchCreation(
		{
			"type_of_transaction": "Outward",
			"serial_and_batch_bundle": item.get("serial_and_batch_bundle"),
			"item_code": item.get("item_code"),
			"warehouse": warehouse,
			"do_not_save": True,
		}
	).duplicate_package()


def _collect_sample_batches(sabb, item, warehouse):
	batches = get_batch_nos(item.get("serial_and_batch_bundle"))
	sabe_list, total_qty = [], 0
	for batch_no in batches.keys():
		qty, entries = _process_sample_batch(sabb, item, warehouse, batch_no)
		total_qty += qty
		sabe_list.extend(entries)
	return total_qty, sabe_list


def _process_sample_batch(sabb, item, warehouse, batch_no):
	sample_quantity = validate_sample_quantity(
		item.get("item_code"),
		item.get("sample_quantity"),
		item.get("transfer_qty") or item.get("qty"),
		batch_no,
	)
	sabe = next(entry for entry in sabb.entries if entry.batch_no == batch_no)
	if not sample_quantity:
		sabb.entries.remove(sabe)
		return 0, []
	return _apply_sample_quantity(sabb, sabe, warehouse, batch_no, sample_quantity)


def _apply_sample_quantity(sabb, sabe, warehouse, batch_no, sample_quantity):
	if sabb.has_serial_no:
		entries = [
			e
			for e in sabb.entries
			if e.batch_no == batch_no
			and frappe.db.exists("Serial No", {"name": e.serial_no, "warehouse": warehouse})
		][: int(sample_quantity)]
		return len(entries), entries
	sabe.qty = sample_quantity
	return sample_quantity, []


def _append_sample_entry(stock_entry, sabb, item, warehouse, retention_warehouse, total_qty, sabe_list):
	if sabe_list:
		sabb.entries = sabe_list
	sabb.save()
	stock_entry.append(
		"items",
		{
			"item_code": item.get("item_code"),
			"s_warehouse": warehouse,
			"t_warehouse": retention_warehouse,
			"qty": total_qty,
			"basic_rate": item.get("valuation_rate"),
			"uom": item.get("uom"),
			"stock_uom": item.get("stock_uom"),
			"conversion_factor": item.get("conversion_factor") or 1.0,
			"serial_and_batch_bundle": sabb.name,
		},
	)


@frappe.whitelist()
def validate_sample_quantity(item_code: str, sample_quantity: int, qty: float, batch_no: str | None = None):
	from erpnext.stock.doctype.batch.batch import get_batch_qty

	if cint(qty) < cint(sample_quantity):
		frappe.throw(
			_("Sample quantity {0} cannot be more than received quantity {1}").format(sample_quantity, qty)
		)
	return _adjust_sample_quantity(item_code, sample_quantity, batch_no, get_batch_qty)


def _adjust_sample_quantity(item_code, sample_quantity, batch_no, get_batch_qty):
	retention_warehouse = frappe.get_single_value("Stock Settings", "sample_retention_warehouse")
	retainted_qty = get_batch_qty(batch_no, retention_warehouse, item_code) if batch_no else 0
	max_retain_qty = frappe.get_value("Item", item_code, "sample_quantity")
	if retainted_qty >= max_retain_qty:
		_warn_max_retained(retainted_qty, batch_no, item_code)
		return 0
	return _cap_sample_quantity(sample_quantity, max_retain_qty, retainted_qty, batch_no, item_code)


def _warn_max_retained(retainted_qty, batch_no, item_code):
	frappe.msgprint(
		_("Maximum Samples - {0} have already been retained for Batch {1} and Item {2} in Batch {3}.").format(
			retainted_qty, batch_no, item_code, batch_no
		),
		alert=True,
	)


def _cap_sample_quantity(sample_quantity, max_retain_qty, retainted_qty, batch_no, item_code):
	qty_diff = max_retain_qty - retainted_qty
	if cint(sample_quantity) > cint(qty_diff):
		frappe.msgprint(
			_("Maximum Samples - {0} can be retained for Batch {1} and Item {2}.").format(
				max_retain_qty, batch_no, item_code
			),
			alert=True,
		)
		return qty_diff
	return sample_quantity
