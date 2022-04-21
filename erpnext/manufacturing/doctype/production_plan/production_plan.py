# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import copy
import json

import frappe
from frappe import _, msgprint
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	ceil,
	cint,
	comma_and,
	flt,
	get_link_to_form,
	getdate,
	now_datetime,
	nowdate,
)
from frappe.utils.csvutils import build_csv_response

from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no
from erpnext.manufacturing.doctype.work_order.work_order import get_item_details
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults


class ProductionPlan(Document):
	def validate(self):
		self.set_pending_qty_in_row_without_reference()
		self.calculate_total_planned_qty()
		self.set_status()
		self._rename_temporary_references()

	def set_pending_qty_in_row_without_reference(self):
		"Set Pending Qty in independent rows (not from SO or MR)."
		if self.docstatus > 0:  # set only to initialise value before submit
			return

		for item in self.po_items:
			if not item.get("sales_order") or not item.get("material_request"):
				item.pending_qty = item.planned_qty

	def calculate_total_planned_qty(self):
		self.total_planned_qty = 0
		for d in self.po_items:
			self.total_planned_qty += flt(d.planned_qty)

	def validate_data(self):
		for d in self.get("po_items"):
			if not d.bom_no:
				frappe.throw(_("Please select BOM for Item in Row {0}").format(d.idx))
			else:
				validate_bom_no(d.item_code, d.bom_no)

			if not flt(d.planned_qty):
				frappe.throw(_("Please enter Planned Qty for Item {0} at row {1}").format(d.item_code, d.idx))

	def _rename_temporary_references(self):
		"""po_items and sub_assembly_items items are both constructed client side without saving.

		Attempt to fix linkages by using temporary names to map final row names.
		"""
		new_name_map = {d.temporary_name: d.name for d in self.po_items if d.temporary_name}
		actual_names = {d.name for d in self.po_items}

		for sub_assy in self.sub_assembly_items:
			if sub_assy.production_plan_item not in actual_names:
				sub_assy.production_plan_item = new_name_map.get(sub_assy.production_plan_item)

	@frappe.whitelist()
	def get_open_sales_orders(self):
		"""Pull sales orders  which are pending to deliver based on criteria selected"""
		open_so = get_sales_orders(self)

		if open_so:
			self.add_so_in_table(open_so)
		else:
			frappe.msgprint(_("Sales orders are not available for production"))

	def add_so_in_table(self, open_so):
		"""Add sales orders in the table"""
		self.set("sales_orders", [])

		for data in open_so:
			self.append(
				"sales_orders",
				{
					"sales_order": data.name,
					"sales_order_date": data.transaction_date,
					"customer": data.customer,
					"grand_total": data.base_grand_total,
				},
			)

	@frappe.whitelist()
	def get_pending_material_requests(self):
		"""Pull Material Requests that are pending based on criteria selected"""
		mr_filter = item_filter = ""
		if self.from_date:
			mr_filter += " and mr.transaction_date >= %(from_date)s"
		if self.to_date:
			mr_filter += " and mr.transaction_date <= %(to_date)s"
		if self.warehouse:
			mr_filter += " and mr_item.warehouse = %(warehouse)s"

		if self.item_code:
			item_filter += " and mr_item.item_code = %(item)s"

		pending_mr = frappe.db.sql(
			"""
			select distinct mr.name, mr.transaction_date
			from `tabMaterial Request` mr, `tabMaterial Request Item` mr_item
			where mr_item.parent = mr.name
				and mr.material_request_type = "Manufacture"
				and mr.docstatus = 1 and mr.status != "Stopped" and mr.company = %(company)s
				and mr_item.qty > ifnull(mr_item.ordered_qty,0) {0} {1}
				and (exists (select name from `tabBOM` bom where bom.item=mr_item.item_code
					and bom.is_active = 1))
			""".format(
				mr_filter, item_filter
			),
			{
				"from_date": self.from_date,
				"to_date": self.to_date,
				"warehouse": self.warehouse,
				"item": self.item_code,
				"company": self.company,
			},
			as_dict=1,
		)

		self.add_mr_in_table(pending_mr)

	def add_mr_in_table(self, pending_mr):
		"""Add Material Requests in the table"""
		self.set("material_requests", [])

		for data in pending_mr:
			self.append(
				"material_requests",
				{"material_request": data.name, "material_request_date": data.transaction_date},
			)

	@frappe.whitelist()
	def get_items(self):
		self.set("po_items", [])
		if self.get_items_from == "Sales Order":
			self.get_so_items()

		elif self.get_items_from == "Material Request":
			self.get_mr_items()

	def get_so_mr_list(self, field, table):
		"""Returns a list of Sales Orders or Material Requests from the respective tables"""
		so_mr_list = [d.get(field) for d in self.get(table) if d.get(field)]
		return so_mr_list

	def get_bom_item(self):
		"""Check if Item or if its Template has a BOM."""
		bom_item = None
		has_bom = frappe.db.exists({"doctype": "BOM", "item": self.item_code, "docstatus": 1})
		if not has_bom:
			template_item = frappe.db.get_value("Item", self.item_code, ["variant_of"])
			bom_item = (
				"bom.item = {0}".format(frappe.db.escape(template_item)) if template_item else bom_item
			)
		return bom_item

	def get_so_items(self):
		# Check for empty table or empty rows
		if not self.get("sales_orders") or not self.get_so_mr_list("sales_order", "sales_orders"):
			frappe.throw(_("Please fill the Sales Orders table"), title=_("Sales Orders Required"))

		so_list = self.get_so_mr_list("sales_order", "sales_orders")

		item_condition = ""
		bom_item = "bom.item = so_item.item_code"
		if self.item_code and frappe.db.exists("Item", self.item_code):
			bom_item = self.get_bom_item() or bom_item
			item_condition = " and so_item.item_code = {0}".format(frappe.db.escape(self.item_code))

		items = frappe.db.sql(
			"""
			select
				distinct parent, item_code, warehouse,
				(qty - work_order_qty) * conversion_factor as pending_qty,
				description, name
			from
				`tabSales Order Item` so_item
			where
				parent in (%s) and docstatus = 1 and qty > work_order_qty
				and exists (select name from `tabBOM` bom where %s
				and bom.is_active = 1) %s"""
			% (", ".join(["%s"] * len(so_list)), bom_item, item_condition),
			tuple(so_list),
			as_dict=1,
		)

		if self.item_code:
			item_condition = " and so_item.item_code = {0}".format(frappe.db.escape(self.item_code))

		packed_items = frappe.db.sql(
			"""select distinct pi.parent, pi.item_code, pi.warehouse as warehouse,
			(((so_item.qty - so_item.work_order_qty) * pi.qty) / so_item.qty)
				as pending_qty, pi.parent_item, pi.description, so_item.name
			from `tabSales Order Item` so_item, `tabPacked Item` pi
			where so_item.parent = pi.parent and so_item.docstatus = 1
			and pi.parent_item = so_item.item_code
			and so_item.parent in (%s) and so_item.qty > so_item.work_order_qty
			and exists (select name from `tabBOM` bom where bom.item=pi.item_code
					and bom.is_active = 1) %s"""
			% (", ".join(["%s"] * len(so_list)), item_condition),
			tuple(so_list),
			as_dict=1,
		)

		self.add_items(items + packed_items)
		self.calculate_total_planned_qty()

	def get_mr_items(self):
		# Check for empty table or empty rows
		if not self.get("material_requests") or not self.get_so_mr_list(
			"material_request", "material_requests"
		):
			frappe.throw(
				_("Please fill the Material Requests table"), title=_("Material Requests Required")
			)

		mr_list = self.get_so_mr_list("material_request", "material_requests")

		item_condition = ""
		if self.item_code:
			item_condition = " and mr_item.item_code ={0}".format(frappe.db.escape(self.item_code))

		items = frappe.db.sql(
			"""select distinct parent, name, item_code, warehouse, description,
			(qty - ordered_qty) * conversion_factor as pending_qty
			from `tabMaterial Request Item` mr_item
			where parent in (%s) and docstatus = 1 and qty > ordered_qty
			and exists (select name from `tabBOM` bom where bom.item=mr_item.item_code
				and bom.is_active = 1) %s"""
			% (", ".join(["%s"] * len(mr_list)), item_condition),
			tuple(mr_list),
			as_dict=1,
		)

		self.add_items(items)
		self.calculate_total_planned_qty()

	def add_items(self, items):
		refs = {}
		for data in items:
			item_details = get_item_details(data.item_code)
			if self.combine_items:
				if item_details.bom_no in refs:
					refs[item_details.bom_no]["so_details"].append(
						{"sales_order": data.parent, "sales_order_item": data.name, "qty": data.pending_qty}
					)
					refs[item_details.bom_no]["qty"] += data.pending_qty
					continue

				else:
					refs[item_details.bom_no] = {
						"qty": data.pending_qty,
						"po_item_ref": data.name,
						"so_details": [],
					}
					refs[item_details.bom_no]["so_details"].append(
						{"sales_order": data.parent, "sales_order_item": data.name, "qty": data.pending_qty}
					)

			pi = self.append(
				"po_items",
				{
					"warehouse": data.warehouse,
					"item_code": data.item_code,
					"description": data.description or item_details.description,
					"stock_uom": item_details and item_details.stock_uom or "",
					"bom_no": item_details and item_details.bom_no or "",
					"planned_qty": data.pending_qty,
					"pending_qty": data.pending_qty,
					"planned_start_date": now_datetime(),
					"product_bundle_item": data.parent_item,
				},
			)
			pi._set_defaults()

			if self.get_items_from == "Sales Order":
				pi.sales_order = data.parent
				pi.sales_order_item = data.name
				pi.description = data.description

			elif self.get_items_from == "Material Request":
				pi.material_request = data.parent
				pi.material_request_item = data.name
				pi.description = data.description

		if refs:
			for po_item in self.po_items:
				po_item.planned_qty = refs[po_item.bom_no]["qty"]
				po_item.pending_qty = refs[po_item.bom_no]["qty"]
				po_item.sales_order = ""
			self.add_pp_ref(refs)

	def add_pp_ref(self, refs):
		for bom_no in refs:
			for so_detail in refs[bom_no]["so_details"]:
				self.append(
					"prod_plan_references",
					{
						"item_reference": refs[bom_no]["po_item_ref"],
						"sales_order": so_detail["sales_order"],
						"sales_order_item": so_detail["sales_order_item"],
						"qty": so_detail["qty"],
					},
				)

	def calculate_total_produced_qty(self):
		self.total_produced_qty = 0
		for d in self.po_items:
			self.total_produced_qty += flt(d.produced_qty)

		self.db_set("total_produced_qty", self.total_produced_qty, update_modified=False)

	def update_produced_pending_qty(self, produced_qty, production_plan_item):
		for data in self.po_items:
			if data.name == production_plan_item:
				data.produced_qty = produced_qty
				data.pending_qty = flt(data.planned_qty - produced_qty)
				data.db_update()

		self.calculate_total_produced_qty()
		self.set_status()
		self.db_set("status", self.status)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.delete_draft_work_order()

	def delete_draft_work_order(self):
		for d in frappe.get_all(
			"Work Order", fields=["name"], filters={"docstatus": 0, "production_plan": ("=", self.name)}
		):
			frappe.delete_doc("Work Order", d.name)

	@frappe.whitelist()
	def set_status(self, close=None):
		self.status = {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(self.docstatus)

		if close:
			self.db_set("status", "Closed")
			return

		if self.total_produced_qty > 0:
			self.status = "In Process"
			if self.all_items_completed():
				self.status = "Completed"

		if self.status != "Completed":
			self.update_ordered_status()
			self.update_requested_status()

		if close is not None:
			self.db_set("status", self.status)

	def update_ordered_status(self):
		update_status = False
		for d in self.po_items:
			if d.planned_qty == d.ordered_qty:
				update_status = True

		if update_status and self.status != "Completed":
			self.status = "In Process"

	def update_requested_status(self):
		if not self.mr_items:
			return

		update_status = True
		for d in self.mr_items:
			if d.quantity != d.requested_qty:
				update_status = False

		if update_status:
			self.status = "Material Requested"

	def get_production_items(self):
		item_dict = {}

		for d in self.po_items:
			item_details = {
				"production_item": d.item_code,
				"use_multi_level_bom": d.include_exploded_items,
				"sales_order": d.sales_order,
				"sales_order_item": d.sales_order_item,
				"material_request": d.material_request,
				"material_request_item": d.material_request_item,
				"bom_no": d.bom_no,
				"description": d.description,
				"stock_uom": d.stock_uom,
				"company": self.company,
				"fg_warehouse": d.warehouse,
				"production_plan": self.name,
				"production_plan_item": d.name,
				"product_bundle_item": d.product_bundle_item,
				"planned_start_date": d.planned_start_date,
				"project": self.project,
			}

			if not item_details["project"] and d.sales_order:
				item_details["project"] = frappe.get_cached_value("Sales Order", d.sales_order, "project")

			if self.get_items_from == "Material Request":
				item_details.update({"qty": d.planned_qty})
				item_dict[(d.item_code, d.material_request_item, d.warehouse)] = item_details
			else:
				item_details.update(
					{
						"qty": flt(item_dict.get((d.item_code, d.sales_order, d.warehouse), {}).get("qty"))
						+ (flt(d.planned_qty) - flt(d.ordered_qty))
					}
				)
				item_dict[(d.item_code, d.sales_order, d.warehouse)] = item_details

		return item_dict

	@frappe.whitelist()
	def make_work_order(self):
		from erpnext.manufacturing.doctype.work_order.work_order import get_default_warehouse

		wo_list, po_list = [], []
		subcontracted_po = {}
		default_warehouses = get_default_warehouse()

		self.make_work_order_for_finished_goods(wo_list, default_warehouses)
		self.make_work_order_for_subassembly_items(wo_list, subcontracted_po, default_warehouses)
		self.make_subcontracted_purchase_order(subcontracted_po, po_list)
		self.show_list_created_message("Work Order", wo_list)
		self.show_list_created_message("Purchase Order", po_list)

	def make_work_order_for_finished_goods(self, wo_list, default_warehouses):
		items_data = self.get_production_items()

		for key, item in items_data.items():
			if self.sub_assembly_items:
				item["use_multi_level_bom"] = 0

			set_default_warehouses(item, default_warehouses)
			work_order = self.create_work_order(item)
			if work_order:
				wo_list.append(work_order)

	def make_work_order_for_subassembly_items(self, wo_list, subcontracted_po, default_warehouses):
		for row in self.sub_assembly_items:
			if row.type_of_manufacturing == "Subcontract":
				subcontracted_po.setdefault(row.supplier, []).append(row)
				continue

			work_order_data = {
				"wip_warehouse": default_warehouses.get("wip_warehouse"),
				"fg_warehouse": default_warehouses.get("fg_warehouse"),
				"company": self.get("company"),
			}

			self.prepare_data_for_sub_assembly_items(row, work_order_data)
			work_order = self.create_work_order(work_order_data)
			if work_order:
				wo_list.append(work_order)

	def prepare_data_for_sub_assembly_items(self, row, wo_data):
		for field in [
			"production_item",
			"item_name",
			"qty",
			"fg_warehouse",
			"description",
			"bom_no",
			"stock_uom",
			"bom_level",
			"production_plan_item",
			"schedule_date",
		]:
			if row.get(field):
				wo_data[field] = row.get(field)

		wo_data.update(
			{
				"use_multi_level_bom": 0,
				"production_plan": self.name,
				"production_plan_sub_assembly_item": row.name,
			}
		)

	def make_subcontracted_purchase_order(self, subcontracted_po, purchase_orders):
		if not subcontracted_po:
			return

		for supplier, po_list in subcontracted_po.items():
			po = frappe.new_doc("Purchase Order")
			po.company = self.company
			po.supplier = supplier
			po.schedule_date = getdate(po_list[0].schedule_date) if po_list[0].schedule_date else nowdate()
			po.is_subcontracted = 1
			for row in po_list:
				po_data = {
					"item_code": row.production_item,
					"warehouse": row.fg_warehouse,
					"production_plan_sub_assembly_item": row.name,
					"bom": row.bom_no,
					"production_plan": self.name,
				}

				for field in [
					"schedule_date",
					"qty",
					"uom",
					"stock_uom",
					"item_name",
					"description",
					"production_plan_item",
				]:
					po_data[field] = row.get(field)

				po.append("items", po_data)

			po.set_missing_values()
			po.flags.ignore_mandatory = True
			po.flags.ignore_validate = True
			po.insert()
			purchase_orders.append(po.name)

	def show_list_created_message(self, doctype, doc_list=None):
		if not doc_list:
			return

		frappe.flags.mute_messages = False
		if doc_list:
			doc_list = [get_link_to_form(doctype, p) for p in doc_list]
			msgprint(_("{0} created").format(comma_and(doc_list)))

	def create_work_order(self, item):
		from erpnext.manufacturing.doctype.work_order.work_order import OverProductionError

		wo = frappe.new_doc("Work Order")
		wo.update(item)
		wo.planned_start_date = item.get("planned_start_date") or item.get("schedule_date")

		if item.get("warehouse"):
			wo.fg_warehouse = item.get("warehouse")

		wo.set_work_order_operations()
		wo.set_required_items()

		try:
			wo.flags.ignore_mandatory = True
			wo.flags.ignore_validate = True
			wo.insert()
			return wo.name
		except OverProductionError:
			pass

	@frappe.whitelist()
	def make_material_request(self):
		"""Create Material Requests grouped by Sales Order and Material Request Type"""
		material_request_list = []
		material_request_map = {}

		for item in self.mr_items:
			item_doc = frappe.get_cached_doc("Item", item.item_code)

			material_request_type = item.material_request_type or item_doc.default_material_request_type

			# key for Sales Order:Material Request Type:Customer
			key = "{}:{}:{}".format(item.sales_order, material_request_type, item_doc.customer or "")
			schedule_date = add_days(nowdate(), cint(item_doc.lead_time_days))

			if not key in material_request_map:
				# make a new MR for the combination
				material_request_map[key] = frappe.new_doc("Material Request")
				material_request = material_request_map[key]
				material_request.update(
					{
						"transaction_date": nowdate(),
						"status": "Draft",
						"company": self.company,
						"material_request_type": material_request_type,
						"customer": item_doc.customer or "",
					}
				)
				material_request_list.append(material_request)
			else:
				material_request = material_request_map[key]

			# add item
			material_request.append(
				"items",
				{
					"item_code": item.item_code,
					"from_warehouse": item.from_warehouse,
					"qty": item.quantity,
					"schedule_date": schedule_date,
					"warehouse": item.warehouse,
					"sales_order": item.sales_order,
					"production_plan": self.name,
					"material_request_plan_item": item.name,
					"project": frappe.db.get_value("Sales Order", item.sales_order, "project")
					if item.sales_order
					else None,
				},
			)

		for material_request in material_request_list:
			# submit
			material_request.flags.ignore_permissions = 1
			material_request.run_method("set_missing_values")

			if self.get("submit_material_request"):
				material_request.submit()
			else:
				material_request.save()

		frappe.flags.mute_messages = False

		if material_request_list:
			material_request_list = [
				"""<a href="/app/Form/Material Request/{0}">{1}</a>""".format(m.name, m.name)
				for m in material_request_list
			]
			msgprint(_("{0} created").format(comma_and(material_request_list)))
		else:
			msgprint(_("No material request created"))

	@frappe.whitelist()
	def get_sub_assembly_items(self, manufacturing_type=None):
		"Fetch sub assembly items and optionally combine them."
		self.sub_assembly_items = []
		sub_assembly_items_store = []  # temporary store to process all subassembly items

		for row in self.po_items:
			bom_data = []
			get_sub_assembly_items(row.bom_no, bom_data, row.planned_qty)
			self.set_sub_assembly_items_based_on_level(row, bom_data, manufacturing_type)
			sub_assembly_items_store.extend(bom_data)

		if self.combine_sub_items:
			# Combine subassembly items
			sub_assembly_items_store = self.combine_subassembly_items(sub_assembly_items_store)

		sub_assembly_items_store.sort(key=lambda d: d.bom_level, reverse=True)  # sort by bom level

		for idx, row in enumerate(sub_assembly_items_store):
			row.idx = idx + 1
			self.append("sub_assembly_items", row)

	def set_sub_assembly_items_based_on_level(self, row, bom_data, manufacturing_type=None):
		"Modify bom_data, set additional details."
		for data in bom_data:
			data.qty = data.stock_qty
			data.production_plan_item = row.name
			data.fg_warehouse = row.warehouse
			data.schedule_date = row.planned_start_date
			data.type_of_manufacturing = manufacturing_type or (
				"Subcontract" if data.is_sub_contracted_item else "In House"
			)

	def combine_subassembly_items(self, sub_assembly_items_store):
		"Aggregate if same: Item, Warehouse, Inhouse/Outhouse Manu.g, BOM No."
		key_wise_data = {}
		for row in sub_assembly_items_store:
			key = (
				row.get("production_item"),
				row.get("fg_warehouse"),
				row.get("bom_no"),
				row.get("type_of_manufacturing"),
			)
			if key not in key_wise_data:
				# intialise (item, wh, bom no, man.g type) wise dict
				key_wise_data[key] = row
				continue

			existing_row = key_wise_data[key]
			if existing_row:
				# if row with same (item, wh, bom no, man.g type) key, merge
				existing_row.qty += flt(row.qty)
				existing_row.stock_qty += flt(row.stock_qty)
				existing_row.bom_level = max(existing_row.bom_level, row.bom_level)
				continue
			else:
				# add row with key
				key_wise_data[key] = row

		sub_assembly_items_store = [
			key_wise_data[key] for key in key_wise_data
		]  # unpack into single level list
		return sub_assembly_items_store

	def all_items_completed(self):
		all_items_produced = all(
			flt(d.planned_qty) - flt(d.produced_qty) < 0.000001 for d in self.po_items
		)
		if not all_items_produced:
			return False

		wo_status = frappe.get_all(
			"Work Order",
			filters={
				"production_plan": self.name,
				"status": ("not in", ["Closed", "Stopped"]),
				"docstatus": ("<", 2),
			},
			fields="status",
			pluck="status",
		)
		all_work_orders_completed = all(s == "Completed" for s in wo_status)
		return all_work_orders_completed


@frappe.whitelist()
def download_raw_materials(doc, warehouses=None):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	item_list = [
		[
			"Item Code",
			"Item Name",
			"Description",
			"Stock UOM",
			"Warehouse",
			"Required Qty as per BOM",
			"Projected Qty",
			"Available Qty In Hand",
			"Ordered Qty",
			"Planned Qty",
			"Reserved Qty for Production",
			"Safety Stock",
			"Required Qty",
		]
	]

	doc.warehouse = None
	frappe.flags.show_qty_in_stock_uom = 1
	items = get_items_for_material_requests(
		doc, warehouses=warehouses, get_parent_warehouse_data=True
	)

	for d in items:
		item_list.append(
			[
				d.get("item_code"),
				d.get("item_name"),
				d.get("description"),
				d.get("stock_uom"),
				d.get("warehouse"),
				d.get("required_bom_qty"),
				d.get("projected_qty"),
				d.get("actual_qty"),
				d.get("ordered_qty"),
				d.get("planned_qty"),
				d.get("reserved_qty_for_production"),
				d.get("safety_stock"),
				d.get("quantity"),
			]
		)

		if not doc.get("for_warehouse"):
			row = {"item_code": d.get("item_code")}
			for bin_dict in get_bin_details(row, doc.company, all_warehouse=True):
				if d.get("warehouse") == bin_dict.get("warehouse"):
					continue

				item_list.append(
					[
						"",
						"",
						"",
						bin_dict.get("warehouse"),
						"",
						bin_dict.get("projected_qty", 0),
						bin_dict.get("actual_qty", 0),
						bin_dict.get("ordered_qty", 0),
						bin_dict.get("reserved_qty_for_production", 0),
					]
				)

	build_csv_response(item_list, doc.name)


def get_exploded_items(item_details, company, bom_no, include_non_stock_items, planned_qty=1):
	for d in frappe.db.sql(
		"""select bei.item_code, item.default_bom as bom,
			ifnull(sum(bei.stock_qty/ifnull(bom.quantity, 1)), 0)*%s as qty, item.item_name,
			bei.description, bei.stock_uom, item.min_order_qty, bei.source_warehouse,
			item.default_material_request_type, item.min_order_qty, item_default.default_warehouse,
			item.purchase_uom, item_uom.conversion_factor, item.safety_stock
		from
			`tabBOM Explosion Item` bei
			JOIN `tabBOM` bom ON bom.name = bei.parent
			JOIN `tabItem` item ON item.name = bei.item_code
			LEFT JOIN `tabItem Default` item_default
				ON item_default.parent = item.name and item_default.company=%s
			LEFT JOIN `tabUOM Conversion Detail` item_uom
				ON item.name = item_uom.parent and item_uom.uom = item.purchase_uom
		where
			bei.docstatus < 2
			and bom.name=%s and item.is_stock_item in (1, {0})
		group by bei.item_code, bei.stock_uom""".format(
			0 if include_non_stock_items else 1
		),
		(planned_qty, company, bom_no),
		as_dict=1,
	):
		if not d.conversion_factor and d.purchase_uom:
			d.conversion_factor = get_uom_conversion_factor(d.item_code, d.purchase_uom)
		item_details.setdefault(d.get("item_code"), d)

	return item_details


def get_uom_conversion_factor(item_code, uom):
	return frappe.db.get_value(
		"UOM Conversion Detail", {"parent": item_code, "uom": uom}, "conversion_factor"
	)


def get_subitems(
	doc,
	data,
	item_details,
	bom_no,
	company,
	include_non_stock_items,
	include_subcontracted_items,
	parent_qty,
	planned_qty=1,
):
	items = frappe.db.sql(
		"""
		SELECT
			bom_item.item_code, default_material_request_type, item.item_name,
			ifnull(%(parent_qty)s * sum(bom_item.stock_qty/ifnull(bom.quantity, 1)) * %(planned_qty)s, 0) as qty,
			item.is_sub_contracted_item as is_sub_contracted, bom_item.source_warehouse,
			item.default_bom as default_bom, bom_item.description as description,
			bom_item.stock_uom as stock_uom, item.min_order_qty as min_order_qty, item.safety_stock as safety_stock,
			item_default.default_warehouse, item.purchase_uom, item_uom.conversion_factor
		FROM
			`tabBOM Item` bom_item
			JOIN `tabBOM` bom ON bom.name = bom_item.parent
			JOIN tabItem item ON bom_item.item_code = item.name
			LEFT JOIN `tabItem Default` item_default
				ON item.name = item_default.parent and item_default.company = %(company)s
			LEFT JOIN `tabUOM Conversion Detail` item_uom
				ON item.name = item_uom.parent and item_uom.uom = item.purchase_uom
		where
			bom.name = %(bom)s
			and bom_item.docstatus < 2
			and item.is_stock_item in (1, {0})
		group by bom_item.item_code""".format(
			0 if include_non_stock_items else 1
		),
		{"bom": bom_no, "parent_qty": parent_qty, "planned_qty": planned_qty, "company": company},
		as_dict=1,
	)

	for d in items:
		if not data.get("include_exploded_items") or not d.default_bom:
			if d.item_code in item_details:
				item_details[d.item_code].qty = item_details[d.item_code].qty + d.qty
			else:
				if not d.conversion_factor and d.purchase_uom:
					d.conversion_factor = get_uom_conversion_factor(d.item_code, d.purchase_uom)

				item_details[d.item_code] = d

		if data.get("include_exploded_items") and d.default_bom:
			if (
				d.default_material_request_type in ["Manufacture", "Purchase"] and not d.is_sub_contracted
			) or (d.is_sub_contracted and include_subcontracted_items):
				if d.qty > 0:
					get_subitems(
						doc,
						data,
						item_details,
						d.default_bom,
						company,
						include_non_stock_items,
						include_subcontracted_items,
						d.qty,
					)
	return item_details


def get_material_request_items(
	row, sales_order, company, ignore_existing_ordered_qty, include_safety_stock, warehouse, bin_dict
):
	total_qty = row["qty"]

	required_qty = 0
	if ignore_existing_ordered_qty or bin_dict.get("projected_qty", 0) < 0:
		required_qty = total_qty
	elif total_qty > bin_dict.get("projected_qty", 0):
		required_qty = total_qty - bin_dict.get("projected_qty", 0)
	if required_qty > 0 and required_qty < row["min_order_qty"]:
		required_qty = row["min_order_qty"]
	item_group_defaults = get_item_group_defaults(row.item_code, company)

	if not row["purchase_uom"]:
		row["purchase_uom"] = row["stock_uom"]

	if row["purchase_uom"] != row["stock_uom"]:
		if not (row["conversion_factor"] or frappe.flags.show_qty_in_stock_uom):
			frappe.throw(
				_("UOM Conversion factor ({0} -> {1}) not found for item: {2}").format(
					row["purchase_uom"], row["stock_uom"], row.item_code
				)
			)

			required_qty = required_qty / row["conversion_factor"]

	if frappe.db.get_value("UOM", row["purchase_uom"], "must_be_whole_number"):
		required_qty = ceil(required_qty)

	if include_safety_stock:
		required_qty += flt(row["safety_stock"])

	if required_qty > 0:
		return {
			"item_code": row.item_code,
			"item_name": row.item_name,
			"quantity": required_qty,
			"required_bom_qty": total_qty,
			"stock_uom": row.get("stock_uom"),
			"warehouse": warehouse
			or row.get("source_warehouse")
			or row.get("default_warehouse")
			or item_group_defaults.get("default_warehouse"),
			"safety_stock": row.safety_stock,
			"actual_qty": bin_dict.get("actual_qty", 0),
			"projected_qty": bin_dict.get("projected_qty", 0),
			"ordered_qty": bin_dict.get("ordered_qty", 0),
			"reserved_qty_for_production": bin_dict.get("reserved_qty_for_production", 0),
			"min_order_qty": row["min_order_qty"],
			"material_request_type": row.get("default_material_request_type"),
			"sales_order": sales_order,
			"description": row.get("description"),
			"uom": row.get("purchase_uom") or row.get("stock_uom"),
		}


def get_sales_orders(self):
	so_filter = item_filter = ""
	bom_item = "bom.item = so_item.item_code"

	date_field_mapper = {
		"from_date": (">=", "so.transaction_date"),
		"to_date": ("<=", "so.transaction_date"),
		"from_delivery_date": (">=", "so_item.delivery_date"),
		"to_delivery_date": ("<=", "so_item.delivery_date"),
	}

	for field, value in date_field_mapper.items():
		if self.get(field):
			so_filter += f" and {value[1]} {value[0]} %({field})s"

	for field in ["customer", "project", "sales_order_status"]:
		if self.get(field):
			so_field = "status" if field == "sales_order_status" else field
			so_filter += f" and so.{so_field} = %({field})s"

	if self.item_code and frappe.db.exists("Item", self.item_code):
		bom_item = self.get_bom_item() or bom_item
		item_filter += " and so_item.item_code = %(item_code)s"

	open_so = frappe.db.sql(
		f"""
		select distinct so.name, so.transaction_date, so.customer, so.base_grand_total
		from `tabSales Order` so, `tabSales Order Item` so_item
		where so_item.parent = so.name
			and so.docstatus = 1 and so.status not in ("Stopped", "Closed")
			and so.company = %(company)s
			and so_item.qty > so_item.work_order_qty {so_filter} {item_filter}
			and (exists (select name from `tabBOM` bom where {bom_item}
					and bom.is_active = 1)
				or exists (select name from `tabPacked Item` pi
					where pi.parent = so.name and pi.parent_item = so_item.item_code
						and exists (select name from `tabBOM` bom where bom.item=pi.item_code
							and bom.is_active = 1)))
		""",
		self.as_dict(),
		as_dict=1,
	)

	return open_so


@frappe.whitelist()
def get_bin_details(row, company, for_warehouse=None, all_warehouse=False):
	if isinstance(row, str):
		row = frappe._dict(json.loads(row))

	company = frappe.db.escape(company)
	conditions, warehouse = "", ""

	conditions = " and warehouse in (select name from `tabWarehouse` where company = {0})".format(
		company
	)
	if not all_warehouse:
		warehouse = for_warehouse or row.get("source_warehouse") or row.get("default_warehouse")

	if warehouse:
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		conditions = """ and warehouse in (select name from `tabWarehouse`
			where lft >= {0} and rgt <= {1} and name=`tabBin`.warehouse and company = {2})
		""".format(
			lft, rgt, company
		)

	return frappe.db.sql(
		""" select ifnull(sum(projected_qty),0) as projected_qty,
		ifnull(sum(actual_qty),0) as actual_qty, ifnull(sum(ordered_qty),0) as ordered_qty,
		ifnull(sum(reserved_qty_for_production),0) as reserved_qty_for_production, warehouse,
		ifnull(sum(planned_qty),0) as planned_qty
		from `tabBin` where item_code = %(item_code)s {conditions}
		group by item_code, warehouse
	""".format(
			conditions=conditions
		),
		{"item_code": row["item_code"]},
		as_dict=1,
	)


@frappe.whitelist()
def get_so_details(sales_order):
	return frappe.db.get_value(
		"Sales Order", sales_order, ["transaction_date", "customer", "grand_total"], as_dict=1
	)


def get_warehouse_list(warehouses):
	warehouse_list = []

	if isinstance(warehouses, str):
		warehouses = json.loads(warehouses)

	for row in warehouses:
		child_warehouses = frappe.db.get_descendants("Warehouse", row.get("warehouse"))
		if child_warehouses:
			warehouse_list.extend(child_warehouses)
		else:
			warehouse_list.append(row.get("warehouse"))

	return warehouse_list


@frappe.whitelist()
def get_items_for_material_requests(doc, warehouses=None, get_parent_warehouse_data=None):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	if warehouses:
		warehouses = list(set(get_warehouse_list(warehouses)))

		if (
			doc.get("for_warehouse")
			and not get_parent_warehouse_data
			and doc.get("for_warehouse") in warehouses
		):
			warehouses.remove(doc.get("for_warehouse"))

	doc["mr_items"] = []

	po_items = doc.get("po_items") if doc.get("po_items") else doc.get("items")
	# Check for empty table or empty rows
	if not po_items or not [row.get("item_code") for row in po_items if row.get("item_code")]:
		frappe.throw(
			_("Items to Manufacture are required to pull the Raw Materials associated with it."),
			title=_("Items Required"),
		)

	company = doc.get("company")
	ignore_existing_ordered_qty = doc.get("ignore_existing_ordered_qty")
	include_safety_stock = doc.get("include_safety_stock")

	so_item_details = frappe._dict()
	for data in po_items:
		if not data.get("include_exploded_items") and doc.get("sub_assembly_items"):
			data["include_exploded_items"] = 1

		planned_qty = data.get("required_qty") or data.get("planned_qty")
		ignore_existing_ordered_qty = (
			data.get("ignore_existing_ordered_qty") or ignore_existing_ordered_qty
		)
		warehouse = doc.get("for_warehouse")

		item_details = {}
		if data.get("bom") or data.get("bom_no"):
			if data.get("required_qty"):
				bom_no = data.get("bom")
				include_non_stock_items = 1
				include_subcontracted_items = 1 if data.get("include_exploded_items") else 0
			else:
				bom_no = data.get("bom_no")
				include_subcontracted_items = doc.get("include_subcontracted_items")
				include_non_stock_items = doc.get("include_non_stock_items")

			if not planned_qty:
				frappe.throw(_("For row {0}: Enter Planned Qty").format(data.get("idx")))

			if bom_no:
				if data.get("include_exploded_items") and include_subcontracted_items:
					# fetch exploded items from BOM
					item_details = get_exploded_items(
						item_details, company, bom_no, include_non_stock_items, planned_qty=planned_qty
					)
				else:
					item_details = get_subitems(
						doc,
						data,
						item_details,
						bom_no,
						company,
						include_non_stock_items,
						include_subcontracted_items,
						1,
						planned_qty=planned_qty,
					)
		elif data.get("item_code"):
			item_master = frappe.get_doc("Item", data["item_code"]).as_dict()
			purchase_uom = item_master.purchase_uom or item_master.stock_uom
			conversion_factor = (
				get_uom_conversion_factor(item_master.name, purchase_uom) if item_master.purchase_uom else 1.0
			)

			item_details[item_master.name] = frappe._dict(
				{
					"item_name": item_master.item_name,
					"default_bom": doc.bom,
					"purchase_uom": purchase_uom,
					"default_warehouse": item_master.default_warehouse,
					"min_order_qty": item_master.min_order_qty,
					"default_material_request_type": item_master.default_material_request_type,
					"qty": planned_qty or 1,
					"is_sub_contracted": item_master.is_subcontracted_item,
					"item_code": item_master.name,
					"description": item_master.description,
					"stock_uom": item_master.stock_uom,
					"conversion_factor": conversion_factor,
					"safety_stock": item_master.safety_stock,
				}
			)

		sales_order = doc.get("sales_order")

		for item_code, details in item_details.items():
			so_item_details.setdefault(sales_order, frappe._dict())
			if item_code in so_item_details.get(sales_order, {}):
				so_item_details[sales_order][item_code]["qty"] = so_item_details[sales_order][item_code].get(
					"qty", 0
				) + flt(details.qty)
			else:
				so_item_details[sales_order][item_code] = details

	mr_items = []
	for sales_order, item_code in so_item_details.items():
		item_dict = so_item_details[sales_order]
		for details in item_dict.values():
			bin_dict = get_bin_details(details, doc.company, warehouse)
			bin_dict = bin_dict[0] if bin_dict else {}

			if details.qty > 0:
				items = get_material_request_items(
					details,
					sales_order,
					company,
					ignore_existing_ordered_qty,
					include_safety_stock,
					warehouse,
					bin_dict,
				)
				if items:
					mr_items.append(items)

	if (not ignore_existing_ordered_qty or get_parent_warehouse_data) and warehouses:
		new_mr_items = []
		for item in mr_items:
			get_materials_from_other_locations(item, warehouses, new_mr_items, company)

		mr_items = new_mr_items

	if not mr_items:
		to_enable = frappe.bold(_("Ignore Existing Projected Quantity"))
		warehouse = frappe.bold(doc.get("for_warehouse"))
		message = (
			_(
				"As there are sufficient raw materials, Material Request is not required for Warehouse {0}."
			).format(warehouse)
			+ "<br><br>"
		)
		message += _("If you still want to proceed, please enable {0}.").format(to_enable)

		frappe.msgprint(message, title=_("Note"))

	return mr_items


def get_materials_from_other_locations(item, warehouses, new_mr_items, company):
	from erpnext.stock.doctype.pick_list.pick_list import get_available_item_locations

	locations = get_available_item_locations(
		item.get("item_code"), warehouses, item.get("quantity"), company, ignore_validation=True
	)

	required_qty = item.get("quantity")
	# get available material by transferring to production warehouse
	for d in locations:
		if required_qty <= 0:
			return

		new_dict = copy.deepcopy(item)
		quantity = required_qty if d.get("qty") > required_qty else d.get("qty")

		new_dict.update(
			{
				"quantity": quantity,
				"material_request_type": "Material Transfer",
				"uom": new_dict.get("stock_uom"),  # internal transfer should be in stock UOM
				"from_warehouse": d.get("warehouse"),
			}
		)

		required_qty -= quantity
		new_mr_items.append(new_dict)

	# raise purchase request for remaining qty
	if required_qty:
		stock_uom, purchase_uom = frappe.db.get_value(
			"Item", item["item_code"], ["stock_uom", "purchase_uom"]
		)

		if purchase_uom != stock_uom and purchase_uom == item["uom"]:
			conversion_factor = get_uom_conversion_factor(item["item_code"], item["uom"])
			if not (conversion_factor or frappe.flags.show_qty_in_stock_uom):
				frappe.throw(
					_("UOM Conversion factor ({0} -> {1}) not found for item: {2}").format(
						purchase_uom, stock_uom, item["item_code"]
					)
				)

			required_qty = required_qty / conversion_factor

		if frappe.db.get_value("UOM", purchase_uom, "must_be_whole_number"):
			required_qty = ceil(required_qty)

		item["quantity"] = required_qty

		new_mr_items.append(item)


@frappe.whitelist()
def get_item_data(item_code):
	item_details = get_item_details(item_code)

	return {
		"bom_no": item_details.get("bom_no"),
		"stock_uom": item_details.get("stock_uom")
		# 		"description": item_details.get("description")
	}


def get_sub_assembly_items(bom_no, bom_data, to_produce_qty, indent=0):
	data = get_bom_children(parent=bom_no)
	for d in data:
		if d.expandable:
			parent_item_code = frappe.get_cached_value("BOM", bom_no, "item")
			stock_qty = (d.stock_qty / d.parent_bom_qty) * flt(to_produce_qty)
			bom_data.append(
				frappe._dict(
					{
						"parent_item_code": parent_item_code,
						"description": d.description,
						"production_item": d.item_code,
						"item_name": d.item_name,
						"stock_uom": d.stock_uom,
						"uom": d.stock_uom,
						"bom_no": d.value,
						"is_sub_contracted_item": d.is_sub_contracted_item,
						"bom_level": indent,
						"indent": indent,
						"stock_qty": stock_qty,
					}
				)
			)

			if d.value:
				get_sub_assembly_items(d.value, bom_data, stock_qty, indent=indent + 1)


def set_default_warehouses(row, default_warehouses):
	for field in ["wip_warehouse", "fg_warehouse"]:
		if not row.get(field):
			row[field] = default_warehouses.get(field)
