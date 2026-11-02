# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull
from frappe.utils import add_days, flt, get_link_to_form, getdate, parse_json

from erpnext.manufacturing.doctype.sales_forecast.sales_forecast import update_sales_forecast_status
from erpnext.manufacturing.scheduling.plan_adapter import get_days_needed


class MasterProductionSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.manufacturing.doctype.master_production_schedule_item.master_production_schedule_item import (
			MasterProductionScheduleItem,
		)
		from erpnext.manufacturing.doctype.production_plan_material_request.production_plan_material_request import (
			ProductionPlanMaterialRequest,
		)
		from erpnext.manufacturing.doctype.production_plan_sales_order.production_plan_sales_order import (
			ProductionPlanSalesOrder,
		)

		amended_from: DF.Link | None
		company: DF.Link
		from_date: DF.Date
		items: DF.Table[MasterProductionScheduleItem]
		material_requests: DF.Table[ProductionPlanMaterialRequest]
		naming_series: DF.Literal["MPS.YY.-.######"]
		parent_warehouse: DF.Link | None
		posting_date: DF.Date
		sales_forecast: DF.Link | None
		sales_orders: DF.Table[ProductionPlanSalesOrder]
		select_items: DF.TableMultiSelect[MasterProductionScheduleItem]
		to_date: DF.Date | None
	# end: auto-generated types

	@frappe.whitelist()
	def get_actual_demand(self):
		self.set("items", [])

		actual_demand_data = self.get_demand_data()

		item_wise_data = self.get_item_wise_mps_data(actual_demand_data)

		if not item_wise_data:
			return []

		self.update_item_details(item_wise_data)
		self.add_mps_data(item_wise_data)

		if not self.is_new():
			self.save()

	def validate(self):
		self.set_to_date()
		self.validate_company()
		self.validate_sales_forecast_not_used()

	def validate_sales_forecast_not_used(self):
		if not self.sales_forecast:
			return

		frappe.db.get_value("Sales Forecast", self.sales_forecast, "name", for_update=True)
		existing = frappe.db.get_value(
			"Master Production Schedule",
			{"sales_forecast": self.sales_forecast, "name": ("!=", self.name or "")},
		)
		if existing:
			frappe.throw(
				_("Sales Forecast {0} already has Master Production Schedule {1}").format(
					bold(self.sales_forecast), get_link_to_form("Master Production Schedule", existing)
				)
			)

	def validate_company(self):
		if self.sales_forecast:
			sales_forecast_company = frappe.db.get_value("Sales Forecast", self.sales_forecast, "company")
			if sales_forecast_company != self.company:
				frappe.throw(
					_(
						"The Company {0} of Sales Forecast {1} does not match with the Company {2} of Master Production Schedule {3}."
					).format(
						bold(sales_forecast_company),
						bold(self.sales_forecast),
						bold(self.company),
						bold(self.name),
					)
				)

	def set_to_date(self):
		if self.to_date:
			return

		for row in self.items:
			if not self.to_date or getdate(row.delivery_date) > getdate(self.to_date):
				self.to_date = row.delivery_date

		forecast_delivery_dates = self.get_sales_forecast_data()
		for date in forecast_delivery_dates:
			if not self.to_date or getdate(date) > getdate(self.to_date):
				self.to_date = date

	def get_sales_forecast_data(self):
		if not self.sales_forecast:
			return []

		filters = {"parent": self.sales_forecast}
		if self.select_items:
			items = [d.item_code for d in self.select_items if d.item_code]
			filters["item_code"] = ("in", items)

		return frappe.get_all(
			"Sales Forecast Item",
			filters=filters,
			pluck="delivery_date",
			order_by="delivery_date asc",
		)

	def update_item_details(self, data):
		items = [item[0] for item in data if item[0]]
		item_details = self.get_item_details(items)
		self.load_lead_times([(row.item_code, row.bom_no) for row in item_details.values()])

		for key in data:
			item_data = data[key]
			item_code = key[0]
			if item_code in item_details:
				item_data.update(item_details[item_code])
				item_data.cumulative_lead_time = self.get_cumulative_lead_time(
					item_code, item_data.bom_no, flt(item_data.qty)
				)

	def get_item_details(self, items):
		doctype = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.name.as_("item_code"),
				doctype.default_bom.as_("bom_no"),
				doctype.item_name,
			)
			.where(doctype.name.isin(items))
		)

		return frappe._dict({row.item_code: row for row in query.run(as_dict=True)})

	def load_lead_times(self, roots):
		self._bom_materials = {}
		items, visited, stack = set(), set(), list(roots)
		while stack:
			item_code, bom_no = stack.pop()
			items.add(item_code)
			if bom_no and bom_no not in visited:
				visited.add(bom_no)
				stack.extend((row.item_code, row.bom_no) for row in self.get_bom_materials(bom_no))

		self._lead_times = {
			row.item_code: row
			for row in frappe.get_all(
				"Item Lead Time",
				filters={"item_code": ("in", list(items) or [""])},
				fields=[
					"item_code",
					"capacity_per_day",
					"manufacturing_time_in_mins",
					"no_of_shift",
					"shift_time_in_hours",
					"no_of_workstations",
					"purchase_time",
					"buffer_time",
				],
			)
		}

	def get_bom_materials(self, bom_no):
		if bom_no not in self._bom_materials:
			bom = frappe.qb.DocType("BOM")
			bom_item = frappe.qb.DocType("BOM Item")
			self._bom_materials[bom_no] = (
				frappe.qb.from_(bom_item)
				.join(bom)
				.on(bom.name == bom_item.parent)
				.select(
					bom_item.item_code,
					bom_item.bom_no,
					(bom_item.stock_qty / bom.quantity).as_("qty_per_unit"),
				)
				.where((bom_item.parent == bom_no) & (bom_item.parenttype == "BOM") & (bom.docstatus == 1))
			).run(as_dict=True)

		return self._bom_materials[bom_no]

	def get_cumulative_lead_time(self, item_code, bom_no, qty):
		own_time = get_own_lead_time(self._lead_times.get(item_code), qty, bool(bom_no))
		if not bom_no:
			return own_time

		component_times = [
			self.get_cumulative_lead_time(row.item_code, row.bom_no, qty * flt(row.qty_per_unit))
			for row in self.get_bom_materials(bom_no)
		]
		return own_time + max(component_times, default=0)

	def get_demand_data(self):
		sales_order_data = self.get_sales_orders_data()
		material_request_data = self.get_material_requests_data()

		return sales_order_data + material_request_data

	def get_material_requests_data(self):
		material_requests = [m.material_request for m in self.material_requests if m.material_request]
		if not material_requests:
			return []

		doctype = frappe.qb.DocType("Material Request Item")
		parent = frappe.qb.DocType("Material Request")
		pending_qty = doctype.stock_qty - IfNull(doctype.ordered_qty, 0)

		query = (
			frappe.qb.from_(doctype)
			.join(parent)
			.on(parent.name == doctype.parent)
			.select(
				doctype.item_code,
				doctype.warehouse,
				doctype.stock_uom,
				doctype.schedule_date.as_("delivery_date"),
				doctype.parent.as_("material_request"),
				pending_qty.as_("qty"),
			)
			.where(
				doctype.parent.isin(material_requests)
				& (parent.docstatus == 1)
				& (parent.company == self.company)
				& (parent.status != "Stopped")
				& (pending_qty > 0)
			)
			.orderby(doctype.schedule_date)
		)

		if self.from_date:
			query = query.where(doctype.schedule_date >= self.from_date)

		if self.to_date:
			query = query.where(doctype.schedule_date <= self.to_date)

		return self.filter_selected_items(query, doctype).run(as_dict=True)

	def filter_selected_items(self, query, doctype):
		if items := self.get_items_for_mps():
			query = query.where(doctype.item_code.isin(items))

		return query

	def get_sales_orders_data(self):
		schedules = self.get_sales_order_schedules()
		scheduled_rows = list({row.sales_order_item for row in schedules if row.sales_order_item})
		sales_order_schedules = [
			row for row in deduct_delivered_qty(schedules) if self.is_in_date_range(row.delivery_date)
		]

		return self.get_items_from_sales_orders(scheduled_rows) + sales_order_schedules

	def get_items_from_sales_orders(self, ignore_orders=None):
		doctype = frappe.qb.DocType("Sales Order Item")
		parent = frappe.qb.DocType("Sales Order")
		pending_qty = (doctype.qty - IfNull(doctype.delivered_qty, 0)) * doctype.conversion_factor

		query = (
			frappe.qb.from_(doctype)
			.join(parent)
			.on(parent.name == doctype.parent)
			.select(
				doctype.item_code,
				doctype.warehouse,
				doctype.stock_uom,
				doctype.delivery_date,
				doctype.name.as_("sales_order"),
				pending_qty.as_("qty"),
			)
			.where(
				(doctype.docstatus == 1)
				& (parent.company == self.company)
				& parent.status.notin(["Closed", "Completed"])
				& (pending_qty > 0)
			)
			.orderby(doctype.delivery_date)
		)

		if self.from_date:
			query = query.where(doctype.delivery_date >= self.from_date)

		if self.to_date:
			query = query.where(doctype.delivery_date <= self.to_date)

		if self.sales_orders:
			names = [s.sales_order for s in self.sales_orders if s.sales_order]
			if not names:
				return []

			query = query.where(doctype.parent.isin(names))

		if ignore_orders:
			query = query.where(doctype.name.notin(ignore_orders))

		return self.filter_selected_items(query, doctype).run(as_dict=True)

	def get_sales_order_schedules(self):
		doctype = frappe.qb.DocType("Delivery Schedule Item")
		parent = frappe.qb.DocType("Sales Order")
		so_item = frappe.qb.DocType("Sales Order Item")
		query = (
			frappe.qb.from_(doctype)
			.join(parent)
			.on(parent.name == doctype.sales_order)
			.join(so_item)
			.on(so_item.name == doctype.sales_order_item)
			.select(
				doctype.item_code,
				doctype.warehouse,
				doctype.stock_uom,
				doctype.delivery_date,
				doctype.sales_order,
				doctype.sales_order_item,
				doctype.stock_qty.as_("qty"),
				(IfNull(so_item.delivered_qty, 0) * so_item.conversion_factor).as_("delivered_qty"),
			)
			.where(
				(parent.docstatus == 1)
				& (parent.company == self.company)
				& parent.status.notin(["Closed", "Completed"])
			)
			.orderby(doctype.sales_order_item)
			.orderby(doctype.delivery_date)
		)

		if self.sales_orders:
			names = [s.sales_order for s in self.sales_orders if s.sales_order]
			query = query.where(doctype.sales_order.isin(names))

		return self.filter_selected_items(query, doctype).run(as_dict=True)

	def is_in_date_range(self, delivery_date):
		if self.from_date and getdate(delivery_date) < getdate(self.from_date):
			return False
		return not (self.to_date and getdate(delivery_date) > getdate(self.to_date))

	def get_item_wise_mps_data(self, data):
		item_wise_data = frappe._dict({})

		for item in data:
			key = (item.item_code, item.delivery_date, item.warehouse)

			if key not in item_wise_data:
				item_wise_data[key] = frappe._dict(
					{
						"item_code": item.item_code,
						"delivery_date": item.delivery_date,
						"warehouse": item.warehouse,
						"stock_uom": item.stock_uom,
						"qty": 0.0,
						"cumulative_lead_time": 0.0,
						"order_release_date": item.delivery_date,
					}
				)

			item_details = item_wise_data[key]
			item_details.qty += item.qty

		return item_wise_data

	def add_mps_data(self, data):
		data = frappe._dict(sorted(data.items(), key=lambda x: x[0][1] or ""))

		for key in data:
			row = data[key]
			row.cumulative_lead_time = math.ceil(row.cumulative_lead_time)
			row.order_release_date = add_days(row.delivery_date, -row.cumulative_lead_time)
			row.planned_qty = row.qty
			row.uom = row.stock_uom
			row.warehouse = row.warehouse or self.parent_warehouse
			self.append("items", row)

	def get_distinct_items(self, data):
		items = []
		for item in data:
			if item.item_code not in items:
				items.append(item.item_code)

		return items

	@frappe.whitelist()
	def fetch_materials_requests(self, **data):
		if isinstance(data, str):
			data = parse_json(data)

		self.set("material_requests", [])
		materials_requests = self.get_material_requests(data)
		if not materials_requests:
			frappe.msgprint(
				_("No open Material Requests found for the given criteria."),
				alert=True,
			)
			return

		for row in materials_requests:
			self.append(
				"material_requests",
				{
					"material_request": row.name,
					"material_request_date": row.transaction_date,
				},
			)

		if not self.is_new():
			self.save()

	def get_material_requests(self, data):
		doctype = frappe.qb.DocType("Material Request")

		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.name,
				doctype.transaction_date,
			)
			.where((doctype.docstatus == 1) & (doctype.status.notin(["Closed", "Completed"])))
			.orderby(doctype.schedule_date)
		)

		if data.get("material_request_type"):
			query = query.where(doctype.material_request_type == data.get("material_request_type"))

		if data.get("from_date"):
			query = query.where(doctype.transaction_date >= data.get("from_date"))

		if data.get("to_date"):
			query = query.where(doctype.transaction_date <= data.get("to_date"))

		if self.from_date:
			query = query.where(doctype.schedule_date >= self.from_date)

		if self.to_date:
			query = query.where(doctype.schedule_date <= self.to_date)

		return query.run(as_dict=True)

	@frappe.whitelist()
	def fetch_sales_orders(self, **data):
		if isinstance(data, str):
			data = parse_json(data)

		self.set("sales_orders", [])
		sales_orders = self.get_sales_orders(data)
		if not sales_orders:
			return

		for row in sales_orders:
			self.append(
				"sales_orders",
				{
					"sales_order": row.name,
					"sales_order_date": row.transaction_date,
					"delivery_date": row.delivery_date,
					"customer": row.customer,
					"status": row.status,
					"grand_total": row.grand_total,
				},
			)

		if not self.is_new():
			self.save()

	def get_sales_orders(self, kwargs):
		doctype = frappe.qb.DocType("Sales Order")

		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.name,
				doctype.transaction_date,
				doctype.delivery_date,
				doctype.customer,
				doctype.status,
				doctype.grand_total,
			)
			.where((doctype.docstatus == 1) & (doctype.status.notin(["Closed", "Completed"])))
			.orderby(doctype.delivery_date)
		)

		if kwargs.get("customer"):
			query = query.where(doctype.customer == kwargs.get("customer"))

		if kwargs.get("from_date"):
			query = query.where(doctype.transaction_date >= kwargs.get("from_date"))

		if kwargs.get("to_date"):
			query = query.where(doctype.transaction_date <= kwargs.get("to_date"))

		if kwargs.get("delivery_from_date"):
			query = query.where(doctype.delivery_date >= kwargs.get("delivery_from_date"))

		if kwargs.get("delivery_to_date"):
			query = query.where(doctype.delivery_date <= kwargs.get("delivery_to_date"))

		if items := self.get_items_for_mps():
			doctype_item = frappe.qb.DocType("Sales Order Item")
			query = query.join(doctype_item).on(doctype_item.parent == doctype.name)
			query = query.where(doctype_item.item_code.isin(items))

		return query.run(as_dict=True)

	def get_items_for_mps(self):
		if not self.select_items:
			return

		return [d.item_code for d in self.select_items if d.item_code]

	def on_update(self):
		previous = self.get_doc_before_save()
		if previous and previous.sales_forecast != self.sales_forecast:
			update_sales_forecast_status(previous.sales_forecast)

		update_sales_forecast_status(self.sales_forecast)

	def after_delete(self):
		update_sales_forecast_status(self.sales_forecast)

	def on_submit(self):
		self.enqueue_mrp_creation()

	def enqueue_mrp_creation(self):
		frappe.enqueue_doc("Master Production Schedule", self.name, "make_mrp", queue="long", timeout=1800)

		frappe.msgprint(
			_("MRP Log documents are being created in the background."),
			alert=True,
		)


def get_own_lead_time(lead_time, qty, is_manufactured):
	if not lead_time:
		return 0

	if is_manufactured:
		days = get_days_needed(lead_time, qty, 0)
	else:
		days = flt(lead_time.purchase_time)

	return days + flt(lead_time.buffer_time)


@frappe.whitelist()
def get_mps_details(mps: str):
	frappe.has_permission("Master Production Schedule", "read", doc=mps, throw=True)
	return frappe.db.get_value(
		"Master Production Schedule",
		mps,
		["name", "from_date", "to_date", "company", "posting_date"],
		as_dict=True,
	)


def deduct_delivered_qty(schedules):
	delivered_by_row = {}
	pending = []
	for row in schedules:
		delivered = delivered_by_row.setdefault(row.sales_order_item, flt(row.delivered_qty))
		covered = min(delivered, flt(row.qty))
		delivered_by_row[row.sales_order_item] = delivered - covered
		row.qty = flt(row.qty) - covered
		if row.qty > 0:
			pending.append(row)
	return pending
