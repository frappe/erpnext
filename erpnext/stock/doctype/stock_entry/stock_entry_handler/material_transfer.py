import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt

from .base import BaseStockEntry
from .manufacturing import _check_bom_component_qty, get_bom_items


class BaseMaterialTransferStockEntry(BaseStockEntry):
	def set_default_warehouse(self):
		for row in self.doc.items:
			if not row.t_warehouse and self.doc.to_warehouse:
				row.t_warehouse = self.doc.to_warehouse
			if not row.s_warehouse and self.doc.from_warehouse:
				row.s_warehouse = self.doc.from_warehouse

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.t_warehouse:
				frappe.throw(_("Target Warehouse is required for item {0}").format(row.item_code))
			if not row.s_warehouse:
				frappe.throw(_("Source Warehouse is required for item {0}").format(row.item_code))

	def validate_same_source_target_warehouse(self):
		"""
		Raises: frappe.ValidationError: If warehouses are same and no inventory dimensions differ
		"""

		if not frappe.get_single_value("Stock Settings", "validate_material_transfer_warehouses"):
			return

		from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

		inventory_dimensions = get_inventory_dimensions()
		for item in self.doc.items:
			if cstr(item.s_warehouse) == cstr(item.t_warehouse):
				if not inventory_dimensions:
					frappe.throw(
						_(
							"Row #{0}: Source and Target Warehouse cannot be the same for Material Transfer"
						).format(item.idx),
						title=_("Invalid Source and Target Warehouse"),
					)
				else:
					difference_found = False
					for dimension in inventory_dimensions:
						fieldname = (
							dimension.source_fieldname
							if dimension.source_fieldname.startswith("to_")
							else f"to_{dimension.source_fieldname}"
						)
						if (
							item.get(dimension.source_fieldname)
							and item.get(fieldname)
							and item.get(dimension.source_fieldname) != item.get(fieldname)
						):
							difference_found = True
							break
					if not difference_found:
						frappe.throw(
							_(
								"Row #{0}: Source, Target Warehouse and Inventory Dimensions cannot be the exact same for Material Transfer"
							).format(item.idx),
							title=_("Invalid Source and Target Warehouse"),
						)

	def update_transferred_qty(self):
		if not self.doc.outgoing_stock_entry:
			return

		stock_entries, child_list = self._collect_transferred_qtys()
		if not stock_entries:
			return

		self._bulk_update_transferred_qty(stock_entries, child_list)
		self._update_per_transferred_field()

	def _get_item_transferred_qty(self, item):
		sed = frappe.qb.DocType("Stock Entry Detail")
		result = (
			frappe.qb.from_(sed)
			.select(Sum(sed.transfer_qty).as_("qty"))
			.where(
				(sed.against_stock_entry == item.against_stock_entry)
				& (sed.ste_detail == item.ste_detail)
				& (sed.docstatus == 1)
			)
		).run(as_dict=True)
		return result[0].qty if result and result[0].qty else 0.0

	def _validate_item_transferred_qty(self, item, transferred_qty):
		if item.docstatus != 1:
			return

		transfer_qty = frappe.get_value("Stock Entry Detail", item.ste_detail, "transfer_qty")
		if transferred_qty > transfer_qty:
			frappe.throw(
				_("Row {0}: Transferred quantity cannot be greater than the requested quantity.").format(
					item.idx
				)
			)

	def _collect_transferred_qtys(self):
		stock_entries, child_list = {}, []
		for item in self.doc.items:
			if not (item.against_stock_entry and item.ste_detail):
				continue

			transferred_qty = self._get_item_transferred_qty(item)
			self._validate_item_transferred_qty(item, transferred_qty)
			child_list.append(item.ste_detail)
			stock_entries[(item.against_stock_entry, item.ste_detail)] = transferred_qty
		return stock_entries, child_list

	def _bulk_update_transferred_qty(self, stock_entries, child_list):
		sed = frappe.qb.DocType("Stock Entry Detail")
		case_expr = self._build_case_expr(sed, stock_entries)
		(
			frappe.qb.update(sed)
			.set(sed.transferred_qty, case_expr.else_(sed.transferred_qty))
			.where(sed.name.isin(child_list))
		).run()

	def _build_case_expr(self, sed, stock_entries):
		from pypika import Case

		case_expr = Case()
		for (parent, name), qty in stock_entries.items():
			case_expr = case_expr.when((sed.parent == parent) & (sed.name == name), qty)
		return case_expr

	def _update_per_transferred_field(self):
		self.doc._update_percent_field_in_targets(self._get_per_transferred_config(), update_modified=True)

	def _get_per_transferred_config(self):
		return {
			"source_dt": "Stock Entry Detail",
			"target_field": "transferred_qty",
			"target_ref_field": "transfer_qty",
			"target_dt": "Stock Entry Detail",
			"join_field": "ste_detail",
			"target_parent_dt": "Stock Entry",
			"target_parent_field": "per_transferred",
			"source_field": "transfer_qty",
			"percent_join_field": "against_stock_entry",
		}


class MaterialTransferStockEntry(BaseMaterialTransferStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_warehouse()
		self.validate_same_source_target_warehouse()

	def on_submit(self):
		self.update_transferred_qty()
		self.update_subcontract_order_supplied_items()

	def on_cancel(self):
		self.update_transferred_qty()
		self.update_subcontract_order_supplied_items()

	def update_subcontract_order_supplied_items(self):
		if not self.doc.get(self.doc.subcontract_data.order_field):
			return

		from .subcontracting import SendToSubcontractorStockEntry

		SendToSubcontractorStockEntry(self.doc).update_subcontract_order_supplied_items()


class MaterialTransferForManufactureStockEntry(BaseMaterialTransferStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_warehouse()
		self.validate_component_and_quantities()
		self.validate_same_source_target_warehouse()

	def validate_component_and_quantities(self):
		if not frappe.db.get_single_value("Manufacturing Settings", "validate_components_quantities_per_bom"):
			return

		if not self.doc.fg_completed_qty:
			return

		_check_bom_component_qty(self.doc, get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom))

	def add_items(self):
		item_dict = self.get_pending_raw_materials()

		for item in item_dict.values():
			item["s_warehouse"] = item.get("from_warehouse")
			if self.wo_doc and not item.get("t_warehouse"):
				item["t_warehouse"] = self.wo_doc.wip_warehouse

		for item_code in item_dict:
			self.doc.append("items", item_dict[item_code])

	def get_pending_raw_materials(self):
		"""Return pending raw material qty to transfer, capped at what's still needed."""
		item_dict = self.get_work_order_required_items()
		max_qty = flt(self.wo_doc.qty)
		allow_overproduction = self._is_overproduction_allowed(max_qty)

		for item, item_details in item_dict.items():
			item_dict[item]["qty"] = self._calculate_item_transfer_qty(
				item_details, allow_overproduction, max_qty
			)
			item_dict[item]["transfer_qty"] = flt(item_dict[item]["qty"]) * flt(
				item_dict[item].get("conversion_factor") or 1
			)

		item_dict = {k: v for k, v in item_dict.items() if v["qty"]}

		if not item_dict:
			frappe.msgprint(_("All items have already been transferred for this Work Order."))

		return item_dict

	def _is_overproduction_allowed(self, max_qty):
		overproduction_pct = flt(
			frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
		)
		extra_materials_pct = flt(
			frappe.db.get_single_value("Manufacturing Settings", "transfer_extra_materials_percentage")
		)
		to_transfer_qty = flt(self.wo_doc.material_transferred_for_manufacturing) + flt(
			self.doc.fg_completed_qty
		)
		limit_pct = extra_materials_pct or overproduction_pct
		transfer_limit_qty = max_qty + (max_qty * limit_pct / 100)
		return transfer_limit_qty >= to_transfer_qty

	def _calculate_item_transfer_qty(self, item_details, allow_overproduction, max_qty):
		pending_to_issue = flt(item_details.required_qty) - flt(item_details.transferred_qty)
		desire_to_transfer = flt(self.doc.fg_completed_qty) * flt(item_details.required_qty) / max_qty
		can_transfer = (
			desire_to_transfer <= pending_to_issue
			or (desire_to_transfer > 0 and self.backflush_based_on == "Material Transferred for Manufacture")
			or allow_overproduction
		)
		return _resolve_transfer_qty(desire_to_transfer, pending_to_issue, can_transfer)

	def get_work_order_required_items(self):
		"""Gets Work Order Required Items for Material Transfer for Manufacture."""
		work_order = self.wo_doc
		consider_job_card = work_order.transfer_material_against == "Job Card" and self.doc.get("job_card")
		job_card_items = self.get_job_card_item_codes() if consider_job_card else []
		wip_warehouse = self._resolve_wip_warehouse(work_order)
		extra_pct = flt(
			frappe.db.get_single_value("Manufacturing Settings", "transfer_extra_materials_percentage")
		)
		item_dict = frappe._dict()
		for d in work_order.get("required_items"):
			self._add_required_item(
				item_dict, d, consider_job_card, job_card_items, wip_warehouse, extra_pct, work_order
			)
		return item_dict

	def _resolve_wip_warehouse(self, work_order):
		if not frappe.db.get_value("Warehouse", work_order.wip_warehouse, "is_group"):
			return work_order.wip_warehouse
		return None

	def _add_required_item(
		self, item_dict, d, consider_job_card, job_card_items, wip_warehouse, extra_pct, work_order
	):
		if consider_job_card and d.item_code not in job_card_items:
			return
		additional_qty = extra_pct * flt(d.required_qty) / 100 if extra_pct else 0.0
		transfer_pending = (
			(flt(d.required_qty) + additional_qty) > flt(d.transferred_qty)
			if additional_qty
			else flt(d.required_qty) > flt(d.transferred_qty)
		)
		can_transfer = transfer_pending or self.backflush_based_on == "Material Transferred for Manufacture"
		if not can_transfer or not d.include_item_in_manufacturing:
			return
		self._build_required_item_row(item_dict, d, consider_job_card, wip_warehouse, work_order)

	def _build_required_item_row(self, item_dict, d, consider_job_card, wip_warehouse, work_order):
		item_row = d.as_dict()
		item_row["idx"] = len(item_dict) + 1
		if consider_job_card:
			item_row["job_card_item"] = self._get_job_card_item(d.item_code)
		if d.source_warehouse and not frappe.db.get_value("Warehouse", d.source_warehouse, "is_group"):
			item_row["from_warehouse"] = d.source_warehouse
		item_row["to_warehouse"] = wip_warehouse
		if item_row["allow_alternative_item"]:
			item_row["allow_alternative_item"] = work_order.allow_alternative_item
		item_dict.setdefault(d.item_code, item_row)

	def _get_job_card_item(self, item_code):
		return (
			frappe.db.get_value("Job Card Item", {"item_code": item_code, "parent": self.doc.get("job_card")})
			or None
		)

	def get_job_card_item_codes(self):
		if not self.doc.get("job_card"):
			return []

		return frappe.get_all(
			"Job Card Item", filters={"parent": self.doc.get("job_card")}, pluck="item_code", distinct=True
		)

	def on_submit(self):
		self.update_job_card_and_work_order()

	def on_cancel(self):
		self.update_job_card_and_work_order()

	def update_job_card_and_work_order(self):
		if self.doc.job_card:
			job_doc = frappe.get_doc("Job Card", self.doc.job_card)
			job_doc.set_transferred_qty(update_status=True)
			job_doc.set_transferred_qty_in_job_card_item(self.doc)

		if self.doc.work_order:
			self._validate_work_order()

			if self.doc.fg_completed_qty:
				if self.doc.docstatus == 1:
					self.wo_doc.add_additional_items(self.doc)
				else:
					self.wo_doc.remove_additional_items(self.doc)

				self.wo_doc.run_method("update_work_order_qty")

			self.wo_doc.run_method("update_status")
			if not self.wo_doc.operations:
				self.wo_doc.set_actual_dates()


class MaterialRequestStockEntry(BaseMaterialTransferStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_warehouse()
		self.validate_material_request()

	def get_material_request(self, item_row):
		material_request = item_row.material_request or None
		material_request_item = item_row.material_request_item or None

		if self.doc.outgoing_stock_entry:
			parent_se = frappe.get_value(
				"Stock Entry Detail",
				item_row.ste_detail,
				["material_request", "material_request_item"],
				as_dict=True,
			)
			if parent_se:
				material_request = parent_se.material_request
				material_request_item = parent_se.material_request_item

		return material_request, material_request_item

	def validate_material_request(self):
		for row in self.doc.items:
			material_request, material_request_item = self.get_material_request(row)
			if not material_request:
				return

			mreq_item = frappe.db.get_value(
				"Material Request Item",
				{"name": material_request_item, "parent": material_request},
				["item_code", "warehouse", "idx"],
				as_dict=True,
			)

			if mreq_item.item_code != row.item_code:
				frappe.throw(
					_("Item for row {0} does not match Material Request").format(row.idx),
					frappe.MappingMismatchError,
				)

	def on_submit(self):
		self.update_transferred_qty()
		if self.doc.add_to_transit:
			self.set_material_request_transfer_status("In Transit")

		if self.doc.outgoing_stock_entry:
			self.set_material_request_transfer_status("Completed")

	def on_cancel(self):
		self.update_transferred_qty()
		if self.doc.add_to_transit:
			self.set_material_request_transfer_status("Not Started")

		if self.doc.outgoing_stock_entry:
			self.set_material_request_transfer_status("In Transit")

	def set_material_request_transfer_status(self, status):
		material_requests = []
		parent_se = (
			frappe.get_value("Stock Entry", self.doc.outgoing_stock_entry, "add_to_transit")
			if self.doc.outgoing_stock_entry
			else None
		)
		for item in self.doc.items:
			mr = item.get("material_request")
			if mr not in material_requests and self.doc.outgoing_stock_entry and parent_se:
				mr = frappe.get_value("Stock Entry Detail", item.ste_detail, "material_request")
			if mr and mr not in material_requests:
				status = self._update_mr_transfer_status(mr, status, material_requests)

	def _update_mr_transfer_status(self, material_request, status, material_requests):
		material_requests.append(material_request)
		if status == "Completed":
			qty = get_transferred_qty(material_request)
			if qty.get("transfer_qty") > qty.get("transferred_qty"):
				status = "In Transit"
		frappe.db.set_value("Material Request", material_request, "transfer_status", status)
		return status


def _resolve_transfer_qty(desire_to_transfer, pending_to_issue, can_transfer):
	# "No need for transfer but qty still pending" can occur when transferring multiple RM in different Stock Entries
	if can_transfer:
		return desire_to_transfer if desire_to_transfer > 0 else pending_to_issue
	return pending_to_issue if pending_to_issue > 0 else 0


def get_transferred_qty(material_request):
	sed = frappe.qb.DocType("Stock Entry Detail")
	return (
		frappe.qb.from_(sed)
		.select(Sum(sed.transfer_qty).as_("transfer_qty"), Sum(sed.transferred_qty).as_("transferred_qty"))
		.where((sed.material_request == material_request) & (sed.docstatus == 1))
	).run(as_dict=True)[0]
