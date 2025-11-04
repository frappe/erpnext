# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import math
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum
from frappe.utils import (
	add_days,
	add_months,
	cint,
	days_diff,
	flt,
	formatdate,
	get_date_str,
	get_first_day,
	getdate,
	parse_json,
	today,
)
from frappe.utils.nestedset import get_descendants_of


def execute(filters: dict | None = None):
	obj = MaterialRequirementsPlanningReport(filters)
	data, chart = obj.generate_mrp()
	columns = obj.get_columns()

	return columns, data, None, chart


class MaterialRequirementsPlanningReport:
	def __init__(self, filters):
		self.filters = filters

	def generate_mrp(self):
		self.fg_items = []
		self.rm_items = []
		self.dates = self.get_dates()
		self.mps_data = self.get_mps_data()
		items = self.get_items_from_mps(self.mps_data)
		self.update_sales_forecast_data()

		self.item_rm_details = self.get_raw_materials_data(items)

		self._bin_details = self.get_item_wise_bin_details()
		self.add_non_planned_orders(items)

		self._wo_details = self.get_work_order_data()
		self._po_details = self.get_purchase_order_data()
		self._so_details = self.get_sales_order_data()

		data, chart = self.get_mrp_data()

		return data, chart

	def add_non_planned_orders(self, items):
		_adhoc_so_details = frappe._dict({})

		so = frappe.qb.DocType("Sales Order")
		so_item = frappe.qb.DocType("Sales Order Item")

		query = (
			frappe.qb.from_(so)
			.inner_join(so_item)
			.on(so.name == so_item.parent)
			.select(
				so_item.item_code,
				so_item.item_name,
				so.delivery_date,
				so_item.warehouse,
				((so_item.qty - so_item.delivered_qty) * so_item.conversion_factor).as_("adhoc_qty"),
			)
			.where(
				(so.docstatus == 1)
				& (so.status.notin(["Closed", "Completed", "Stopped"]))
				& (so_item.docstatus == 1)
				& (so_item.item_code.isin(items))
			)
		)

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(so_item.warehouse.isin(warehouses))

		if skip_orders := self.get_orders_to_skip():
			query = query.where(so.name.notin(skip_orders))

		if self.filters.get("from_date"):
			query = query.where(so.transaction_date >= self.filters.get("from_date"))

		if self.filters.get("to_date"):
			query = query.where(so.transaction_date <= self.filters.get("to_date"))

		data = query.run(as_dict=True)

		for row in data:
			self.mps_data.append(
				frappe._dict(
					{
						"item_code": row.item_code,
						"item_name": row.item_code,
						"delivery_date": row.delivery_date,
						"adhoc_qty": row.adhoc_qty,
						"warehouse": row.warehouse,
						"is_adhoc": 1,
					}
				)
			)

	def get_orders_to_skip(self):
		return frappe.get_all(
			"Production Plan Sales Order",
			filters={"parent": self.filters.mps},
			pluck="sales_order",
		)

	def get_item_wise_bin_details(self):
		items = self.fg_items + self.rm_items
		if not items:
			return {}

		_bin_details = frappe._dict({})

		doctype = frappe.qb.DocType("Bin")
		query = (
			frappe.qb.from_(doctype)
			.select(
				doctype.item_code,
				Sum(doctype.actual_qty).as_("actual_qty"),
				Sum(doctype.reserved_stock).as_("reserved_stock"),
				Sum(doctype.indented_qty).as_("indented_qty"),
				Sum(doctype.reserved_qty_for_production).as_("reserved_qty_for_production"),
				Sum(doctype.reserved_qty_for_sub_contract).as_("reserved_qty_for_sub_contract"),
				Sum(doctype.reserved_qty_for_production_plan).as_("reserved_qty_for_production_plan"),
				Sum(doctype.reserved_qty).as_("reserved_qty"),
				Sum(doctype.projected_qty).as_("projected_qty"),
			)
			.where(doctype.item_code.isin(items))
			.groupby(doctype.item_code)
		)

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.warehouse.isin(warehouses))

		bin_data = query.run(as_dict=True)

		for row in bin_data:
			if row.item_code not in _bin_details:
				_bin_details[row.item_code] = row

		self.update_mps_data_with_bin_details(_bin_details)

		return _bin_details

	def update_mps_data_with_bin_details(self, bin_details):
		if not self.filters.mps:
			return

		items = self.fg_items + self.rm_items

		if not items:
			return

		sales_orders = frappe.get_all(
			"Production Plan Sales Order",
			filters={"parent": self.filters.mps},
			pluck="sales_order",
		)

		if not sales_orders:
			return

		sales_order_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": ["in", sales_orders], "docstatus": 1, "item_code": ["in", items]},
			fields=["item_code", "qty", "delivered_qty", "conversion_factor"],
		)

		if not sales_order_items:
			return

		for row in sales_order_items:
			reserved_qty = flt(flt(row.qty) - flt(row.delivered_qty)) * flt(row.conversion_factor)
			if reserved_qty <= 0:
				continue

			if details := bin_details.get(row.item_code, {}):
				details.reserved_qty -= reserved_qty
				details.projected_qty += reserved_qty

	def update_sales_forecast_data(self):
		sales_forecast_data = self.get_sales_forecast_data()

		if not sales_forecast_data:
			return

		for row in sales_forecast_data:
			record_exists = False
			for d in self.mps_data:
				if not d.sales_forecast_qty:
					d.sales_forecast_qty = 0

				if row.item_code == d.item_code and getdate(row.delivery_date) == getdate(d.delivery_date):
					d.sales_forecast_qty += row.qty
					record_exists = True

			if not record_exists:
				self.mps_data.append(
					frappe._dict(
						{
							"item_code": row.item_code,
							"item_name": row.item_code,
							"delivery_date": row.delivery_date,
							"projected_qty": 0,
							"sales_forecast_qty": row.qty,
							"warehouse": self.filters.get("warehouse"),
						}
					)
				)

	def get_mrp_data(self):
		data = self.get_detailed_view_data()
		data = self.filter_based_on_type_of_materials(data)
		chart = self.get_chart_data(data) or {}

		if self.filters.show_in_bucket_view:
			return self.get_bucket_view_data(data), chart

		return data, chart

	def filter_based_on_type_of_materials(self, data):
		new_data = []
		if self.filters.type_of_material == "All":
			return data

		mapper = {
			"Finished Goods": "Manufacture",
			"Raw Materials": "Purchase",
		}.get(self.filters.type_of_material)

		for row in data:
			if row.type_of_material == mapper:
				row.indent = 0
				new_data.append(row)

		return new_data

	def get_chart_data(self, data):
		# Prepare chart for demand vs supply

		if self.filters.get("show_in_bucket_view"):
			return self.get_bucket_view_chart_data(data)
		else:
			return self.get_detailed_view_chart_data(data)

	def get_detailed_view_chart_data(self, data):
		chart_data = frappe._dict({})
		i = 0

		sorted_data = sorted(data, key=lambda x: getdate(x.get("delivery_date")))
		for row in sorted_data:
			if getdate(row.deliver_date) < getdate(today()):
				continue

			if not row.delivery_date:
				continue

			if i == 10:
				break

			delivery_date = formatdate(row.delivery_date, "dd MMM")
			if delivery_date not in chart_data:
				i += 1
				chart_data[delivery_date] = frappe._dict(
					{
						"demand": 0.0,
						"supply": 0.0,
					}
				)

			demand_supply_data = chart_data[delivery_date]
			demand_supply_data.demand += math.ceil(flt(row.planned_qty))
			demand_supply_data.supply += (
				flt(row.in_hand_qty) + flt(row.po_ordered_qty) + flt(row.wo_ordered_qty)
			)

		demand_data = []
		supply_data = []
		for row in chart_data:
			value = chart_data[row]

			demand_data.append(math.ceil(flt(value.demand)))
			supply_data.append(math.ceil(flt(value.supply)))

		return {
			"data": {
				"labels": list(chart_data.keys()),
				"datasets": [
					{
						"name": _("Demand"),
						"values": demand_data,
					},
					{
						"name": _("Supply"),
						"values": supply_data,
					},
				],
			},
			"type": "bar",
			"height": 350,
			"colors": ["#7cd6fd", "green"],
			"title": _("Demand vs Supply"),
		}

	def get_bucket_view_chart_data(self, data):
		chart_data = frappe._dict({})
		labels = []
		i = 0
		for row in self.dates:
			if self.filters.bucket_size == "Daily" and i == 15:
				break

			if self.filters.bucket_size == "Weekly" and i == 12:
				break

			row = frappe._dict(row)
			for d in data:
				if getdate(d.delivery_date) >= getdate(row.from_date) and getdate(d.delivery_date) <= getdate(
					row.to_date
				):
					if row.from_date not in chart_data:
						i += 1
						label = row.label
						if self.filters.bucket_size == "Weekly":
							label = formatdate(row.from_date, "dd") + "-" + formatdate(row.to_date, "dd MMM")

						labels.append(label)
						chart_data[row.from_date] = frappe._dict(
							{
								"demand": 0.0,
								"supply": 0.0,
							}
						)

					demand_supply_data = chart_data[row.from_date]
					demand_supply_data.demand += math.ceil(flt(d.planned_qty))
					demand_supply_data.supply += (
						flt(d.in_hand_qty) + flt(d.po_ordered_qty) + flt(d.wo_ordered_qty)
					)

		demand_data = []
		supply_data = []

		for row in chart_data:
			value = chart_data[row]

			demand_data.append(math.ceil(flt(value.demand)))
			supply_data.append(math.ceil(flt(value.supply)))

		return {
			"data": {
				"labels": labels,
				"datasets": [
					{
						"name": _("Demand"),
						"values": demand_data,
					},
					{
						"name": _("Supply"),
						"values": supply_data,
					},
				],
			},
			"type": "bar",
			"height": 350,
			"colors": ["#7cd6fd", "green"],
			"title": _("Demand vs Supply"),
		}

	def get_bucket_view_data(self, data):
		new_data = []

		item_wise_data = frappe._dict({})
		for item in data:
			if item.item_code not in item_wise_data:
				item_wise_data[item.item_code] = frappe._dict(
					{
						"item_code": item.item_code,
						"item_name": item.item_name,
						"lead_time": item.lead_time,
						"parents_bom": item.parent_bom,
						"bom_no": item.bom_no,
						"indent": item.indent,
						"capacity": item.capacity,
					}
				)

			item_data = item_wise_data[item.item_code]

			for date in self.dates:
				date = frappe._dict(date)
				if date["from_date"] not in item_data:
					item_data[date["from_date"]] = 0.0

				if self.filters.bucket_view == "Delivery Date":
					if getdate(item.delivery_date) >= getdate(date.from_date) and getdate(
						item.delivery_date
					) <= getdate(date.to_date):
						item_data[date["from_date"]] += flt(item.required_qty)
				else:
					if getdate(item.release_date) >= getdate(date.from_date) and getdate(
						item.release_date
					) <= getdate(date.to_date):
						item_data[date["from_date"]] += flt(item.required_qty)

		for row in item_wise_data:
			new_data.append(frappe._dict(item_wise_data[row]))

		return new_data

	def get_detailed_view_data(self):
		data = []
		i = 0

		sorted_data = sorted(self.mps_data, key=lambda x: getdate(x["delivery_date"]))

		for row in sorted_data:
			rm_details = self.item_rm_details.get(row.item_code) or frappe._dict({})

			row.indent = 0
			row.bom_no = rm_details.get("bom_no")
			row.lead_time = math.ceil(rm_details.get("lead_time", 0))
			if not row.sales_forecast_qty:
				row.sales_forecast_qty = 0

			row.demand_qty = max(flt(row.planned_qty), flt(row.sales_forecast_qty))
			row.planned_qty = max(flt(row.planned_qty), flt(row.sales_forecast_qty))
			if row.get("is_adhoc"):
				row.planned_qty += row.adhoc_qty

			for field in ["min_order_qty", "purchase_uom", "safety_stock"]:
				if rm_details.get(field):
					row[field] = rm_details.get(field)

			self.update_required_qty(row)
			row.release_date = add_days(row.delivery_date, row.lead_time * -1)
			if i != 0:
				data.append(frappe._dict({}))

			i += 1
			row.capacity = 0
			if rm_details.raw_materials:
				row.capacity = get_item_capacity(row.item_code, self.filters.bucket_size)
				row.type_of_material = "Manufacture"

			data.append(row)
			if rm_details.raw_materials:
				self.update_rm_details(
					rm_details.raw_materials, row.release_date, row.required_qty, rm_details.bom_no, data
				)

		return data

	def add_non_planned_so(self, row):
		if so_details := self._so_details.get((row.item_code, row.delivery_date)):
			row.adhoc_qty = so_details.qty
			row.planned_qty += so_details.qty
			del self._so_details[(row.item_code, row.delivery_date)]

	def add_bin_details(self, row):
		if bin_details := self._bin_details.get(row.item_code):
			current_qty = bin_details.get("actual_qty", 0.0) - flt(bin_details.get("reserved_stock", 0.0))
			if current_qty > 0:
				if row.required_qty > current_qty:
					row.in_hand_qty = current_qty
					row.required_qty -= current_qty
					bin_details["actual_qty"] = 0.0
				else:
					row.in_hand_qty = row.required_qty
					bin_details["actual_qty"] -= row.required_qty
					row.required_qty = 0.0

	def add_po_details(self, row):
		if row.required_qty > 0 and self._po_details:
			dict_update = {}
			for (item_code, delivery_date), po_data in self._po_details.items():
				if row.item_code == item_code and getdate(delivery_date) <= getdate(row.delivery_date):
					po_ordered_qty = po_data.qty
					if row.required_qty > po_ordered_qty:
						row.po_ordered_qty = po_ordered_qty
						row.required_qty -= po_ordered_qty
						dict_update[(item_code, delivery_date)] = 0.0
					else:
						row.po_ordered_qty = row.required_qty
						dict_update[(item_code, delivery_date)] = flt(po_data.qty) - flt(row.required_qty)
						row.required_qty = 0.0

					if row.required_qty <= 0.0:
						break

			for key, qty in dict_update.items():
				if qty <= 0.0 and key in self._po_details:
					del self._po_details[key]
				elif key in self._po_details:
					self._po_details[key].qty = qty

	def add_wo_details(self, row):
		if row.required_qty > 0 and self._wo_details:
			dict_update = {}
			for (item_code, delivery_date), wo_data in self._wo_details.items():
				if row.item_code == item_code and getdate(delivery_date) <= getdate(row.delivery_date):
					wo_ordered_qty = wo_data.qty
					if row.required_qty > wo_ordered_qty:
						row.wo_ordered_qty = wo_ordered_qty
						row.required_qty -= wo_ordered_qty
						dict_update[(item_code, delivery_date)] = 0.0
					else:
						row.wo_ordered_qty = row.required_qty
						dict_update[(item_code, delivery_date)] = flt(wo_data.qty) - flt(row.required_qty)
						row.required_qty = 0.0

					if row.required_qty <= 0.0:
						break

			if dict_update:
				for key, qty in dict_update.items():
					if qty <= 0.0 and key in self._wo_details:
						del self._wo_details[key]
					elif key in self._wo_details:
						self._wo_details[key].qty = qty

	def update_required_qty(self, row):
		row.required_qty = flt(row.planned_qty)
		row.in_hand_qty = 0.0

		self.add_non_planned_so(row)
		self.add_bin_details(row)
		self.add_po_details(row)
		self.add_wo_details(row)
		self.add_safety_stock(row)

	def add_safety_stock(self, row):
		if self.filters.add_safety_stock:
			row.required_qty += flt(row.safety_stock)

	def get_work_order_data(self):
		wo_details = frappe._dict({})

		doctype = frappe.qb.DocType("Work Order")
		query = (
			frappe.qb.from_(doctype)
			.select(
				(doctype.qty - doctype.produced_qty).as_("qty"),
				doctype.production_item.as_("item_code"),
				doctype.planned_end_date.as_("delivery_date"),
			)
			.where((doctype.docstatus == 1) & (doctype.status.notin(["Stopped", "Closed", "Completed"])))
		)

		items = self.fg_items + self.rm_items

		if items:
			query = query.where(doctype.production_item.isin(items))

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.fg_warehouse.isin(warehouses))

		data = query.run(as_dict=True)

		for row in data:
			key = (row.item_code, row.delivery_date)
			if key not in wo_details:
				wo_details[key] = row
			else:
				wo_details[key].qty += row.qty

		return wo_details

	def get_purchase_order_data(self):
		po_details = frappe._dict({})

		parent_doctype = frappe.qb.DocType("Purchase Order")
		doctype = frappe.qb.DocType("Purchase Order Item")

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(doctype)
			.on(parent_doctype.name == doctype.parent)
			.select(
				((doctype.qty - doctype.received_qty) * doctype.conversion_factor).as_("qty"),
				doctype.item_code.as_("item_code"),
				doctype.schedule_date.as_("delivery_date"),
			)
			.where(
				(doctype.docstatus == 1)
				& (parent_doctype.status.notin(["Stopped", "Closed", "Completed", "Received"]))
			)
		)

		items = self.fg_items + self.rm_items
		if items:
			query = query.where(doctype.item_code.isin(items))

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.warehouse.isin(warehouses))

		data = query.run(as_dict=True)

		for row in data:
			key = (row.item_code, row.delivery_date)
			if key not in po_details:
				po_details[key] = row
			else:
				po_details[key].qty += row.qty

		if sco := self.get_subcontracted_data():
			for row in sco:
				key = (row.item_code, row.delivery_date)
				if key not in po_details:
					po_details[key] = row
				else:
					po_details[key].qty += row.qty

		return po_details

	def get_sales_order_data(self):
		if not self.rm_items:
			return frappe._dict({})

		so_details = frappe._dict({})

		parent_doctype = frappe.qb.DocType("Sales Order")
		doctype = frappe.qb.DocType("Sales Order Item")

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(doctype)
			.on(parent_doctype.name == doctype.parent)
			.select(
				((doctype.qty - doctype.delivered_qty) * doctype.conversion_factor).as_("qty"),
				doctype.item_code.as_("item_code"),
				doctype.delivery_date,
			)
			.where(
				(doctype.docstatus == 1)
				& (parent_doctype.status.notin(["Stopped", "Closed", "Completed", "Received"]))
			)
		)

		if self.rm_items:
			query = query.where(doctype.item_code.isin(self.rm_items))

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.warehouse.isin(warehouses))

		data = query.run(as_dict=True)

		for row in data:
			key = (row.item_code, row.delivery_date)
			if key not in so_details:
				so_details[key] = row
			else:
				so_details[key].qty += row.qty

		if packed_items := self.get_packed_items_sales_order():
			for row in packed_items:
				key = (row.item_code, row.delivery_date)
				if key not in so_details:
					so_details[key] = row
				else:
					so_details[key].qty += row.qty

		return so_details

	def get_packed_items_sales_order(self):
		parent_doctype = frappe.qb.DocType("Sales Order")
		so_item = frappe.qb.DocType("Sales Order Item")
		doctype = frappe.qb.DocType("Packed Item")

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(so_item)
			.on(parent_doctype.name == so_item.parent)
			.inner_join(doctype)
			.on(so_item.name == doctype.parent_detail_docname)
			.select(
				((doctype.qty) * doctype.conversion_factor).as_("qty"),
				doctype.item_code,
				doctype.item_name,
				so_item.delivery_date,
			)
			.where(
				(doctype.docstatus == 1)
				& (parent_doctype.status.notin(["Stopped", "Closed", "Completed", "Received"]))
				& ((so_item.qty - so_item.delivered_qty) > 0)
			)
		)

		if self.rm_items:
			query = query.where(doctype.item_code.isin(self.rm_items))

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.warehouse.isin(warehouses))

		return query.run(as_dict=True)

	def get_subcontracted_data(self):
		parent_doctype = frappe.qb.DocType("Subcontracting Order")
		doctype = frappe.qb.DocType("Subcontracting Order Item")

		query = (
			frappe.qb.from_(parent_doctype)
			.inner_join(doctype)
			.on(parent_doctype.name == doctype.parent)
			.select(
				(doctype.qty - doctype.received_qty).as_("qty"),
				doctype.item_code.as_("item_code"),
				doctype.schedule_date.as_("delivery_date"),
			)
			.where(
				(doctype.docstatus == 1) & (parent_doctype.status.notin(["Stopped", "Closed", "Completed"]))
			)
		)

		items = self.fg_items + self.rm_items
		if items:
			query = query.where(doctype.item_code.isin(items))

		if self.filters.get("warehouse"):
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))

			query = query.where(doctype.warehouse.isin(warehouses))

		return query.run(as_dict=True)

	def update_rm_details(self, raw_materials, delivery_date, planned_qty, bom_no, data):
		for material in raw_materials:
			lead_time = math.ceil(material.lead_time)
			row = frappe._dict(
				{
					"item_code": material.item_code,
					"item_name": material.item_name,
					"default_warehouse": material.default_warehouse,
					"default_supplier": material.default_supplier,
					"planned_qty": material.stock_qty * planned_qty,
					"projected_qty": 0,
					"delivery_date": delivery_date,
					"lead_time": lead_time,
					"release_date": add_days(delivery_date, lead_time * -1),
					"indent": material.indent + 1,
					"parent_bom": bom_no,
					"bom_no": material.bom_no,
					"warehouse": self.filters.get("warehouse"),
					"min_order_qty": flt(material.get("min_order_qty", 0)),
					"purchase_uom": material.get("purchase_uom"),
					"safety_stock": flt(material.get("safety_stock", 0)),
				}
			)

			row.capacity = 0
			if material.raw_materials:
				row.capacity = get_item_capacity(material.item_code, self.filters.bucket_size)
				row.type_of_material = "Manufacture"
			else:
				row.type_of_material = "Purchase"

			self.update_required_qty(row)

			data.append(row)

			if material.raw_materials:
				self.update_rm_details(
					material.raw_materials, row.release_date, row.required_qty, material.bom_no, data
				)

	def get_mps_data(self):
		doctype = frappe.qb.DocType("Master Production Schedule")
		child_doctype = frappe.qb.DocType("Master Production Schedule Item")

		query = (
			frappe.qb.from_(doctype)
			.inner_join(child_doctype)
			.on(doctype.name == child_doctype.parent)
			.select(
				child_doctype.item_code,
				child_doctype.delivery_date,
				doctype.parent_warehouse,
				child_doctype.name,
				child_doctype.item_name,
				child_doctype.planned_qty,
				child_doctype.uom,
			)
			.where(
				(doctype.from_date >= self.filters.from_date)
				& (doctype.to_date <= self.filters.to_date)
				& (child_doctype.parentfield == "items")
			)
			.orderby(child_doctype.delivery_date)
		)

		fields = {
			"parent_warehouse": self.filters.get("warehouse"),
			"name": self.filters.get("mps"),
			"item_code": self.filters.get("item_code"),
		}

		for field, value in fields.items():
			if not value:
				continue

			if field == "item_code":
				query = query.where(child_doctype[field] == value)
			else:
				query = query.where(doctype[field] == value)

		return query.run(as_dict=True)

	def get_items_from_mps(self, mps_data):
		items = []
		for row in mps_data:
			if row.item_code not in items:
				items.append(row.item_code)

		if self.filters.mps:
			sales_forecasts = frappe.get_all(
				"Master Production Schedule",
				filters={"name": self.filters.mps},
				pluck="sales_forecast",
			)

			if sales_forecasts:
				sales_forecast_items = frappe.get_all(
					"Sales Forecast Item",
					filters={"parent": ("in", sales_forecasts)},
					pluck="item_code",
				)

				if sales_forecast_items:
					items.extend(sales_forecast_items)

		return items

	def get_raw_materials_data(self, items):
		item_wise_rm_details = frappe._dict()
		for item_code in items:
			if item_code not in item_wise_rm_details:
				item_wise_rm_details[item_code] = frappe.db.get_value(
					"Item",
					item_code,
					["default_bom as bom_no", "safety_stock", "min_order_qty", "purchase_uom"],
					as_dict=True,
				)

			item_data = item_wise_rm_details[item_code]
			item_data.lead_time = get_item_lead_time(
				item_code, "Manufacture" if item_data.bom_no else "Purchase"
			)

			if item_code not in self.fg_items:
				self.fg_items.append(item_code)

			if item_data.bom_no:
				item_data.raw_materials = self.get_raw_materials(item_data.bom_no, indent=0)

		return item_wise_rm_details

	def get_raw_materials(self, bom_no, indent=0):
		company = self.filters.get("company")
		raw_materials = frappe.get_all(
			"BOM",
			filters=[["BOM Item", "parent", "=", bom_no], ["BOM", "docstatus", "=", 1]],
			fields=[
				"`tabBOM Item`.`item_code`",
				"`tabBOM Item`.`stock_qty`",
				"`tabBOM`.quantity as parent_qty",
				"`tabBOM Item`.`bom_no`",
				"`tabBOM`.`name` as parent_bom",
				"`tabBOM Item`.`item_name`",
				"`tabBOM Item`.`stock_uom` as uom",
			],
		)

		for material in raw_materials:
			material.indent = indent
			material.qty = flt(material.stock_qty / material.parent_qty)

			if details := get_item_details(material.item_code, company):
				material.update(details)

			if material.item_code not in self.rm_items:
				self.rm_items.append(material.item_code)

			if material.bom_no:
				material.raw_materials = self.get_raw_materials(material.bom_no, indent + 1)
				material.lead_time = get_item_lead_time(material.item_code, "Manufacture")
			else:
				material.lead_time = get_item_lead_time(material.item_code, "Purchase")

		return raw_materials

	def get_columns(self):
		if self.filters.show_in_bucket_view:
			columns = [
				{
					"fieldname": "item_code",
					"label": _("Item Code"),
					"fieldtype": "Link",
					"options": "Item",
					"width": 150,
				},
				{
					"fieldname": "item_name",
					"label": _("Item Name"),
					"fieldtype": "Data",
				},
			]

			label = _("Capacity") + " (" + _(self.filters.bucket_size) + ")"
			columns.append(
				{
					"fieldname": "capacity",
					"label": _(label),
					"fieldtype": "Int",
				}
			)

			for date in self.dates:
				columns.append(
					{
						"fieldname": date["from_date"],
						"label": date["label"],
						"fieldtype": "Float",
						"width": 135,
					}
				)

			return columns

		columns = [
			{
				"fieldname": "item_code",
				"label": _("Item Code"),
				"fieldtype": "Link",
				"options": "Item",
				"width": 150,
			},
			{
				"fieldname": "item_name",
				"label": _("Item Name"),
				"fieldtype": "Data",
			},
			{
				"fieldname": "type_of_material",
				"label": _("Type"),
				"fieldtype": "Data",
				"width": 100,
			},
			{
				"fieldname": "warehouse",
				"label": _("Warehouse"),
				"fieldtype": "Link",
				"options": "Warehouse",
				"hidden": True,
			},
		]

		columns += [
			{
				"fieldname": "demand_qty",
				"label": _("Demand Qty"),
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"fieldname": "adhoc_qty",
				"label": _("Ad-hoc Qty"),
				"fieldtype": "Float",
				"width": 120,
			},
		]

		columns += [
			{
				"fieldname": "planned_qty",
				"label": _("Planned Qty"),
				"fieldtype": "Float",
				"width": 120,
			},
			{
				"fieldname": "in_hand_qty",
				"label": _("On Hand"),
				"fieldtype": "Float",
				"width": 90,
			},
			{
				"fieldname": "po_ordered_qty",
				"label": _("Planned Purchase Order"),
				"fieldtype": "Float",
			},
			{
				"fieldname": "wo_ordered_qty",
				"label": _("Planned Work Order"),
				"fieldtype": "Float",
			},
			{
				"fieldname": "safety_stock",
				"label": _("Safety Stock"),
				"fieldtype": "Float",
			},
			{
				"fieldname": "required_qty",
				"label": _("Required Qty"),
				"fieldtype": "Float",
			},
			{
				"fieldname": "min_order_qty",
				"label": _("Min Order Qty"),
				"fieldtype": "Float",
			},
			{
				"fieldname": "delivery_date",
				"label": _("Delivery Date"),
				"fieldtype": "Date",
			},
			{
				"fieldname": "lead_time",
				"label": _("Lead Time"),
				"fieldtype": "Int",
			},
			{
				"fieldname": "release_date",
				"label": _("Release Date"),
				"fieldtype": "Date",
			},
			{
				"fieldname": "bom_no",
				"label": _("BOM No"),
				"fieldtype": "Link",
				"options": "BOM",
				"width": 150,
			},
		]

		return columns

	def get_dates(self):
		bucket_size = self.filters.bucket_size

		from_date = self.filters.from_date
		if bucket_size == "Weekly":
			from_date = self.get_first_date_of_week(from_date)
		elif bucket_size == "Monthly":
			from_date = get_first_day(from_date)

		dates_list = []
		while getdate(self.filters.to_date) > getdate(from_date):
			args = {"from_date": from_date}

			days = 1 if bucket_size == "Daily" else 7
			if bucket_size == "Monthly":
				from_date = add_months(from_date, 1)
			else:
				from_date = add_days(from_date, days)

			args["to_date"] = add_days(from_date, -1)

			if bucket_size == "Monthly":
				args["label"] = formatdate(from_date, "MMM YYYY")
			else:
				if bucket_size == "Weekly":
					args["label"] = (
						formatdate(args["from_date"], "dd MMM")
						+ " - "
						+ formatdate(args["to_date"], "dd MMM")
					)
				else:
					args["label"] = formatdate(args["to_date"], "dd MMM")

			dates_list.append(args)

		return dates_list

	def get_first_date_of_week(self, input_date):
		# convert string to datetime
		if isinstance(input_date, str):
			input_date = datetime.strptime(input_date, "%Y-%m-%d")

		start_of_week = input_date - timedelta(days=input_date.weekday())
		return start_of_week.strftime("%Y-%m-%d")

	def get_last_date_of_week(self, input_date):
		# convert string to datetime
		if isinstance(input_date, str):
			input_date = datetime.strptime(input_date, "%Y-%m-%d")

		end_of_week = input_date + timedelta(days=(6 - input_date.weekday()))
		return end_of_week.strftime("%Y-%m-%d")

	def get_sales_forecast_data(self):
		forecast_doc = frappe.qb.DocType("Sales Forecast")
		doctype = frappe.qb.DocType("Sales Forecast Item")

		query = (
			frappe.qb.from_(forecast_doc)
			.inner_join(doctype)
			.on(forecast_doc.name == doctype.parent)
			.select(
				forecast_doc.frequency,
				doctype.item_code,
				doctype.delivery_date,
				doctype.parent.as_("sales_forecast"),
				doctype.uom.as_("stock_uom"),
				doctype.demand_qty.as_("qty"),
			)
			.where((forecast_doc.docstatus == 1) & (doctype.parentfield == "items"))
			.orderby(doctype.idx)
		)

		if self.filters.mps:
			forecast = frappe.db.get_value("Master Production Schedule", self.filters.mps, "sales_forecast")
			query = query.where(forecast_doc.name == forecast)

		if self.filters.from_date:
			query = query.where(doctype.delivery_date >= self.filters.from_date)

		if self.filters.to_date:
			query = query.where(doctype.delivery_date <= self.filters.to_date)

		if self.filters.warehouse:
			warehouses = [self.filters.get("warehouse")]
			if frappe.db.get_value("Warehouse", self.filters.get("warehouse"), "is_group"):
				warehouses = get_descendants_of("Warehouse", self.filters.get("warehouse"))
				warehouses.append(self.filters.get("warehouse"))

			query = query.where(forecast_doc.parent_warehouse.isin(warehouses))

		if self.filters.item_code:
			query = query.where(doctype.item_code == self.filters.item_code)

		sales_data = query.run(as_dict=True)

		return convert_to_daily_bucket_data(sales_data)


@frappe.request_cache
def get_item_details(item_code, company):
	data = frappe.db.get_value(
		"Item", item_code, ["safety_stock", "min_order_qty", "purchase_uom"], as_dict=True
	) or frappe._dict({"safety_stock": 0})

	default_data = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		["default_warehouse", "default_supplier"],
		as_dict=True,
	)

	if default_data:
		data.update(default_data)

	return data


@frappe.request_cache
def get_item_lead_time(item_code, type_of_material):
	doctype = frappe.qb.DocType("Item Lead Time")

	query = frappe.qb.from_(doctype).where(doctype.item_code == item_code)

	if type_of_material == "Manufacture":
		query = query.select(
			Case()
			.when(doctype.manufacturing_time_in_mins.isnull(), 0)
			.else_(doctype.manufacturing_time_in_mins / 1440 + doctype.buffer_time)
			.as_("lead_time")
		)
	else:
		query = query.select(
			Case()
			.when(doctype.purchase_time.isnull(), 0)
			.else_(doctype.purchase_time + doctype.buffer_time)
			.as_("lead_time")
		)

	time = query.run(pluck="lead_time")

	return time[0] if time else 0


def convert_to_daily_bucket_data(data):
	bucketed_data = []

	for row in data:
		if row.frequency == "Monthly":
			# Convert monthly data to daily buckets
			start_date = get_first_day(row.delivery_date)
			no_of_days = days_diff(add_months(start_date, 1), start_date)

			for i in range(no_of_days):  # Assuming 30 days in a month
				bucketed_data.append(
					frappe._dict(
						{
							"frequency": "Daily",
							"item_code": row.item_code,
							"delivery_date": add_days(start_date, i),
							"sales_forecast": row.sales_forecast,
							"stock_uom": row.stock_uom,
							"qty": row.qty / no_of_days,  # Assuming equal distribution across days
						}
					)
				)

		elif row.frequency == "Weekly":
			# Convert weekly data to daily buckets
			start_date = getdate(row.delivery_date)
			for i in range(7):
				bucketed_data.append(
					frappe._dict(
						{
							"frequency": "Daily",
							"item_code": row.item_code,
							"delivery_date": add_days(start_date, i),
							"sales_forecast": row.sales_forecast,
							"stock_uom": row.stock_uom,
							"qty": row.qty / 7,  # Assuming equal distribution across days
						}
					)
				)

	return bucketed_data


@frappe.request_cache
def get_item_capacity(item_code, bucket_size):
	capacity = frappe.db.get_value(
		"Item Lead Time",
		item_code,
		"capacity_per_day",
	)

	if not capacity:
		return 0.0

	no_of_days = 7 if bucket_size == "Weekly" else 30
	if bucket_size == "Daily":
		no_of_days = 1

	return math.ceil(cint(capacity) * no_of_days)


@frappe.whitelist()
def make_order(selected_rows, company, warehouse=None, mps=None):
	if not frappe.has_permission("Purchase Order", "create"):
		frappe.throw(_("Not permitted to make Purchase Orders"), frappe.PermissionError)

	if isinstance(selected_rows, str):
		selected_rows = parse_json(selected_rows)

	if not frappe.db.exists("Company", company):
		frappe.throw(_("Company {0} does not exist").format(company))

	purchase_orders = {}
	work_orders = []
	for row in selected_rows:
		row = frappe._dict(row)
		if row.type_of_material == "Purchase":
			purchase_orders.setdefault((row.default_supplier, row.release_date), []).append(row)

		if row.type_of_material == "Manufacture" and row.bom_no:
			work_orders.append(row)

	if purchase_orders:
		make_purchase_orders(purchase_orders, company, warehouse=warehouse, mps=mps)

	if work_orders:
		make_work_orders(work_orders, company, warehouse=warehouse, mps=mps)


def make_purchase_orders(purchase_orders, company, warehouse=None, mps=None):
	for (supplier, release_date), items in purchase_orders.items():
		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = company
		po.mps = mps
		po.transaction_date = release_date
		po.set("items", [])

		for item in items:
			uom = item.purchase_uom or item.uom
			if not uom:
				uom_details = get_item_uom(item.item_code)
				uom = uom_details.purchase_uom or uom_details.stock_uom

			if is_whole_number(uom):
				item.required_qty = math.ceil(item.required_qty)

			if flt(item.required_qty) < flt(item.min_order_qty):
				item.required_qty = item.min_order_qty

			po.append(
				"items",
				{
					"item_code": item.item_code,
					"qty": item.required_qty,
					"uom": uom,
					"schedule_date": item.delivery_date if item.delivery_date else today(),
					"warehouse": warehouse or item.default_warehouse,
				},
			)

		if len(po.items) > 0:
			po.insert()
			frappe.msgprint(
				_("Purchase Order {0} created").format(frappe.bold(po.name)),
				alert=True,
			)


def make_work_orders(work_orders, company, warehouse=None, mps=None):
	for item in work_orders:
		uom = item.uom
		if not uom:
			uom_details = get_item_uom(item.item_code)
			uom = uom_details.purchase_uom or uom_details.stock_uom

		if is_whole_number(uom):
			item.required_qty = math.ceil(item.required_qty)

		wo = frappe.new_doc("Work Order")
		wo.production_item = item.item_code
		wo.bom_no = item.bom_no
		wo.company = company
		wo.qty = item.required_qty
		wo.mps = mps
		wo.stock_uom = uom
		wo.wip_warehouse = item.default_warehouse
		wo.fg_warehouse = warehouse or item.default_warehouse
		wo.planned_start_date = item.release_date if item.release_date else today()
		wo.planned_end_date = item.delivery_date if item.delivery_date else today()
		wo.flags.ignore_mandatory = True
		wo.insert()
		frappe.msgprint(
			_("Work Order {0} created").format(frappe.bold(wo.name)),
			alert=True,
		)


@frappe.request_cache
def get_item_uom(item_code):
	return frappe.get_cached_value("Item", item_code, ["stock_uom", "purchase_uom"], as_dict=True)


@frappe.request_cache
def is_whole_number(uom):
	return frappe.get_cached_value("UOM", uom, "must_be_whole_number")
