# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import math

import frappe
from frappe import _, bold
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, flt, getdate, parse_json, today
from frappe.utils.nestedset import get_descendants_of


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
		self.to_date = None
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

		for key in data:
			item_data = data[key]
			item_code = key[0]
			if item_code in item_details:
				item_data.update(item_details[item_code])

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

		item_details = query.run(as_dict=True)
		item_wise_details = frappe._dict({})

		if not item_details:
			return item_wise_details

		for row in item_details:
			row.cumulative_lead_time = self.get_cumulative_lead_time(row.item_code, row.bom_no)

		for row in item_details:
			item_wise_details.setdefault(row.item_code, row)

		return item_wise_details

	def get_cumulative_lead_time(self, item_code, bom_no, time_in_days=0):
		if not time_in_days:
			time_in_days = get_item_lead_time(item_code)

		bom_materials = frappe.get_all(
			"BOM Item",
			filters={"parent": bom_no, "docstatus": 1},
			fields=["item_code", "bom_no"],
		)

		for row in bom_materials:
			if row.bom_no:
				time_in_days += self.get_cumulative_lead_time(row.item_code, row.bom_no)
			else:
				lead_time = get_item_lead_time(row.item_code)
				time_in_days += lead_time

		return time_in_days

	def get_demand_data(self):
		sales_order_data = self.get_sales_orders_data()
		material_request_data = self.get_material_requests_data()

		return sales_order_data + material_request_data

	def get_material_requests_data(self):
		if not self.material_requests:
			return []

		doctype = frappe.qb.DocType("Material Request Item")

		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.item_code,
				doctype.warehouse,
				doctype.stock_uom,
				doctype.schedule_date.as_("delivery_date"),
				doctype.parent.as_("material_request"),
				doctype.stock_qty.as_("qty"),
			)
			.orderby(doctype.schedule_date)
		)

		if self.material_requests:
			material_requests = [m.material_request for m in self.material_requests if m.material_request]
			query = query.where(doctype.parent.isin(material_requests))

		if self.from_date:
			query = query.where(doctype.schedule_date >= self.from_date)

		if self.to_date:
			query = query.where(doctype.schedule_date <= self.to_date)

		return query.run(as_dict=True)

	def get_sales_orders_data(self):
		sales_order_schedules = self.get_sales_order_schedules()
		ignore_orders = []
		if sales_order_schedules:
			for row in sales_order_schedules:
				if row.sales_order_item and row.sales_order_item not in ignore_orders:
					ignore_orders.append(row.sales_order_item)

		sales_orders = self.get_items_from_sales_orders(ignore_orders)

		return sales_orders + sales_order_schedules

	def get_items_from_sales_orders(self, ignore_orders=None):
		doctype = frappe.qb.DocType("Sales Order Item")
		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.item_code,
				doctype.warehouse,
				doctype.stock_uom,
				doctype.delivery_date,
				doctype.name.as_("sales_order"),
				doctype.stock_qty.as_("qty"),
			)
			.where(doctype.docstatus == 1)
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

		return query.run(as_dict=True)

	def get_sales_order_schedules(self):
		doctype = frappe.qb.DocType("Delivery Schedule Item")
		query = frappe.qb.from_(doctype).select(
			doctype.item_code,
			doctype.warehouse,
			doctype.stock_uom,
			doctype.delivery_date,
			doctype.sales_order,
			doctype.sales_order_item,
			doctype.stock_qty.as_("qty"),
		)

		if self.sales_orders:
			names = [s.sales_order for s in self.sales_orders if s.sales_order]
			query = query.where(doctype.sales_order.isin(names))

		if self.from_date:
			query = query.where(doctype.delivery_date >= self.from_date)

		return query.run(as_dict=True)

	def get_item_wise_mps_data(self, data):
		item_wise_data = frappe._dict({})

		for item in data:
			key = (item.item_code, item.delivery_date)

			if key not in item_wise_data:
				item_wise_data[key] = frappe._dict(
					{
						"item_code": item.item_code,
						"delivery_date": item.delivery_date,
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
		data = frappe._dict(sorted(data.items(), key=lambda x: x[0][1]))

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
			query = query.where(doctype.delivery_date <= kwargs.get("to_delivery_date"))

		if items := self.get_items_for_mps():
			doctype_item = frappe.qb.DocType("Sales Order Item")
			query = query.join(doctype_item).on(doctype_item.parent == doctype.name)
			query = query.where(doctype_item.item_code.isin(items))

		return query.run(as_dict=True)

	def get_items_for_mps(self):
		if not self.select_items:
			return

		return [d.item_code for d in self.select_items if d.item_code]

	def on_submit(self):
		self.enqueue_mrp_creation()

	def enqueue_mrp_creation(self):
		frappe.enqueue_doc("Master Production Schedule", self.name, "make_mrp", queue="long", timeout=1800)

		frappe.msgprint(
			_("MRP Log documents are being created in the background."),
			alert=True,
		)


def get_item_lead_time(item_code):
	doctype = frappe.qb.DocType("Item Lead Time")

	query = (
		frappe.qb.from_(doctype)
		.select(
			((doctype.manufacturing_time_in_mins / 1440) + doctype.purchase_time + doctype.buffer_time).as_(
				"cumulative_lead_time"
			)
		)
		.where(doctype.item_code == item_code)
	)

	result = query.run(as_dict=True)
	if result:
		return result[0].cumulative_lead_time or 0

	return 0


@frappe.whitelist()
def get_mps_details(mps):
	return frappe.db.get_value(
		"Master Production Schedule",
		mps,
		["name", "from_date", "to_date", "company", "posting_date"],
		as_dict=True,
	)
