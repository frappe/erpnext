# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from operator import itemgetter
from typing import Any, TypedDict

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import add_days, cint, date_diff, flt, getdate
from frappe.utils.nestedset import get_descendants_of

import erpnext
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import StockClosing
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.utils import add_additional_uom_columns


class StockBalanceFilter(TypedDict):
	company: str | None
	from_date: str
	to_date: str
	item_group: str | None
	item: list[str] | None
	warehouse: list[str] | None
	warehouse_type: str | None
	include_uom: str | None  # include extra info in converted UOM
	show_stock_ageing_data: bool
	show_variant_attributes: bool


SLEntry = dict[str, Any]


def execute(filters: StockBalanceFilter | None = None):
	return StockBalanceReport(filters).run()


class StockBalanceReport:
	def __init__(self, filters: StockBalanceFilter | None) -> None:
		self.filters = filters
		self.from_date = getdate(filters.get("from_date"))
		self.to_date = getdate(filters.get("to_date"))

		self.start_from = None
		self.data = []
		self.columns = []
		self.sle_entries: list[SLEntry] = []
		self.set_company_currency()

	def set_company_currency(self) -> None:
		if self.filters.get("company"):
			self.company_currency = erpnext.get_company_currency(self.filters.get("company"))
		else:
			self.company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	def run(self):
		self.float_precision = cint(frappe.db.get_default("float_precision")) or 3

		self.item_warehouse_map = frappe._dict({})
		self.inventory_dimensions = self.get_inventory_dimension_fields()
		self.prepare_opening_stock()
		self.prepare_sle_query()
		self.prepare_item_warehouse_map_for_current_period()
		self.prepare_new_data()

		if not self.columns:
			self.columns = self.get_columns()

		self.add_additional_uom_columns()

		return self.columns, self.data

	def prepare_opening_stock(self) -> None:
		opening_entries = self.get_entries_from_stock_closing_balance()

		for entry in opening_entries:
			key = self.get_group_by_key(entry)

			self.item_warehouse_map[key] = frappe._dict(
				{
					"item_code": entry.item_code,
					"warehouse": entry.warehouse,
					"item_group": entry.item_group,
					"company": entry.company,
					"currency": self.company_currency,
					"stock_uom": entry.stock_uom,
					"item_name": entry.item_name,
					"opening_qty": entry.actual_qty,
					"opening_val": entry.stock_value_difference,
					"opening_fifo_queue": json.loads(entry.fifo_queue) if entry.fifo_queue else [],
					"in_qty": 0.0,
					"in_val": 0.0,
					"out_qty": 0.0,
					"out_val": 0.0,
					"bal_qty": entry.actual_qty,
					"bal_val": entry.stock_value_difference,
					"val_rate": 0.0,
				}
			)

	def get_entries_from_stock_closing_balance(self) -> list:
		stk_cl_obj = StockClosing(self.filters.company, self.from_date, self.from_date)
		if not stk_cl_obj.last_closing_balance:
			return []

		self.start_from = add_days(stk_cl_obj.last_closing_balance.to_date, 1)

		query_filters = {}
		dimenion_keys = []
		for field in self.filter_fields():
			if not self.filters.get(field):
				continue

			if field in self.inventory_dimensions:
				dimenion_keys.append(field)

			query_filters[field] = self.filters.get(field)

		if dimenion_keys:
			query_filters["inventory_dimension_key"] = json.dumps(("item_code", "warehouse", *dimenion_keys))
		else:
			query_filters["inventory_dimension_key"] = ("is", "not set")

		opening_entries = stk_cl_obj.get_stock_closing_balance(query_filters)
		if not opening_entries:
			return []

		return opening_entries

	def filter_fields(self) -> list[str]:
		fields = ["item_code", "warehouse"]

		for field in self.inventory_dimensions:
			fields.append(field)

		return fields

	def prepare_sle_query(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		item_table = frappe.qb.DocType("Item")

		query = (
			frappe.qb.from_(sle)
			.inner_join(item_table)
			.on(sle.item_code == item_table.name)
			.select(
				sle.item_code,
				sle.warehouse,
				sle.posting_date,
				sle.actual_qty,
				sle.valuation_rate,
				sle.company,
				sle.voucher_type,
				sle.qty_after_transaction,
				sle.stock_value_difference,
				sle.item_code.as_("name"),
				sle.voucher_no,
				sle.stock_value,
				sle.batch_no,
				sle.serial_no,
				sle.serial_and_batch_bundle,
				sle.has_serial_no,
				item_table.item_group,
				item_table.stock_uom,
				item_table.item_name,
			)
			.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
			.orderby(sle.posting_datetime)
			.orderby(sle.creation)
		)

		query = self.apply_inventory_dimensions_filters(query, sle)
		query = self.apply_warehouse_filters(query, sle)
		query = self.apply_items_filters(query, item_table)
		query = self.apply_date_filters(query, sle)

		if self.filters.get("company"):
			query = query.where(sle.company == self.filters.get("company"))

		self.sle_query = query

	def prepare_item_warehouse_map_for_current_period(self):
		self.opening_vouchers = self.get_opening_vouchers()

		if self.filters.get("show_stock_ageing_data"):
			self.sle_entries = self.sle_query.run(as_dict=True)

		# HACK: This is required to avoid causing db query in flt
		_system_settings = frappe.get_cached_doc("System Settings")
		with frappe.db.unbuffered_cursor():
			if not self.filters.get("show_stock_ageing_data"):
				self.sle_entries = self.sle_query.run(as_dict=True, as_iterator=True)

			for entry in self.sle_entries:
				group_by_key = self.get_group_by_key(entry)
				if group_by_key not in self.item_warehouse_map:
					self.initialize_data(group_by_key, entry)

				self.prepare_item_warehouse_map(entry, group_by_key)

		self.item_warehouse_map = filter_items_with_no_transactions(
			self.item_warehouse_map, self.float_precision, self.inventory_dimensions
		)

	def prepare_new_data(self):
		if self.filters.get("show_stock_ageing_data"):
			self.filters["show_warehouse_wise_stock"] = True
			item_wise_fifo_queue = FIFOSlots(self.filters).generate()

		_func = itemgetter(1)

		del self.sle_entries

		sre_details = self.get_sre_reserved_qty_details()

		variant_values = {}
		if self.filters.get("show_variant_attributes"):
			variant_values = self.get_variant_values_for()

		for _key, report_data in self.item_warehouse_map.items():
			if variant_data := variant_values.get(report_data.item_code):
				report_data.update(variant_data)

			if self.filters.get("show_stock_ageing_data"):
				opening_fifo_queue = self.get_opening_fifo_queue(report_data) or []

				fifo_queue = []
				if fifo_queue := item_wise_fifo_queue.get((report_data.item_code, report_data.warehouse)):
					fifo_queue = fifo_queue.get("fifo_queue")

				if fifo_queue:
					opening_fifo_queue.extend(fifo_queue)

				stock_ageing_data = {"average_age": 0, "earliest_age": 0, "latest_age": 0}

				if opening_fifo_queue:
					fifo_queue = sorted(filter(_func, opening_fifo_queue), key=_func)
					if not fifo_queue:
						continue

					to_date = self.to_date
					stock_ageing_data["average_age"] = get_average_age(fifo_queue, to_date)
					stock_ageing_data["earliest_age"] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data["latest_age"] = date_diff(to_date, fifo_queue[-1][1])
					stock_ageing_data["fifo_queue"] = fifo_queue

				report_data.update(stock_ageing_data)

			report_data.update(
				{"reserved_stock": sre_details.get((report_data.item_code, report_data.warehouse), 0.0)}
			)

			if (
				not self.filters.get("include_zero_stock_items")
				and report_data
				and report_data.bal_qty == 0
				and report_data.bal_val == 0
			):
				continue

			self.data.append(report_data)

	def get_sre_reserved_qty_details(self) -> dict:
		from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import (
			get_sre_reserved_qty_for_items_and_warehouses as get_reserved_qty_details,
		)

		item_code_list, warehouse_list = [], []
		for d in self.item_warehouse_map:
			item_code_list.append(d[0])
			warehouse_list.append(d[1])

		return get_reserved_qty_details(item_code_list, warehouse_list)

	def prepare_item_warehouse_map(self, entry, group_by_key):
		qty_dict = self.item_warehouse_map[group_by_key]
		for field in self.inventory_dimensions:
			qty_dict[field] = entry.get(field)

		if entry.voucher_type == "Stock Reconciliation" and (not entry.batch_no or entry.serial_no):
			qty_diff = flt(entry.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(entry.actual_qty)

		value_diff = flt(entry.stock_value_difference)

		if entry.posting_date < self.from_date or entry.voucher_no in self.opening_vouchers.get(
			entry.voucher_type, []
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif entry.posting_date >= self.from_date and entry.posting_date <= self.to_date:
			if flt(qty_diff, self.float_precision) >= 0:
				qty_dict.in_qty += qty_diff
			else:
				qty_dict.out_qty += abs(qty_diff)

			if flt(value_diff, self.float_precision) >= 0:
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = entry.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	def initialize_data(self, group_by_key, entry):
		self.item_warehouse_map[group_by_key] = frappe._dict(
			{
				"item_code": entry.item_code,
				"warehouse": entry.warehouse,
				"item_group": entry.item_group,
				"company": entry.company,
				"currency": self.company_currency,
				"stock_uom": entry.stock_uom,
				"item_name": entry.item_name,
				"opening_qty": 0.0,
				"opening_val": 0.0,
				"opening_fifo_queue": [],
				"in_qty": 0.0,
				"in_val": 0.0,
				"out_qty": 0.0,
				"out_val": 0.0,
				"bal_qty": 0.0,
				"bal_val": 0.0,
				"val_rate": 0.0,
			}
		)

	def get_group_by_key(self, row) -> tuple:
		group_by_key = [row.item_code, row.warehouse]

		for fieldname in self.inventory_dimensions:
			if not row.get(fieldname):
				continue

			if self.filters.get(fieldname) or self.filters.get("show_dimension_wise_stock"):
				group_by_key.append(row.get(fieldname))

		return tuple(group_by_key)

	def apply_inventory_dimensions_filters(self, query, sle) -> str:
		inventory_dimension_fields = self.get_inventory_dimension_fields()
		if inventory_dimension_fields:
			for fieldname in inventory_dimension_fields:
				query = query.select(fieldname)
				if self.filters.get(fieldname):
					query = query.where(sle[fieldname].isin(self.filters.get(fieldname)))

		return query

	def apply_warehouse_filters(self, query, sle) -> str:
		warehouse_table = frappe.qb.DocType("Warehouse")

		if self.filters.get("warehouse"):
			query = apply_warehouse_filter(query, sle, self.filters)

		elif warehouse_type := self.filters.get("warehouse_type"):
			query = (
				query.join(warehouse_table)
				.on(warehouse_table.name == sle.warehouse)
				.where(warehouse_table.warehouse_type == warehouse_type)
			)

		return query

	def apply_items_filters(self, query, item_table) -> str:
		if item_group := self.filters.get("item_group"):
			children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
			query = query.where(item_table.item_group.isin([*children, item_group]))

		if item_codes := self.filters.get("item_code"):
			query = query.where(item_table.name.isin(item_codes))

		if brand := self.filters.get("brand"):
			query = query.where(item_table.brand == brand)

		return query

	def apply_date_filters(self, query, sle) -> str:
		if not self.filters.ignore_closing_balance and self.start_from:
			query = query.where(sle.posting_date >= self.start_from)

		if self.to_date:
			query = query.where(sle.posting_date <= self.to_date)

		return query

	def get_columns(self):
		columns = [
			{
				"label": _("Item"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100,
			},
			{"label": _("Item Name"), "fieldname": "item_name", "width": 150},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 100,
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 100,
			},
		]

		if self.filters.get("show_dimension_wise_stock"):
			for dimension in get_inventory_dimensions():
				columns.append(
					{
						"label": _(dimension.doctype),
						"fieldname": dimension.fieldname,
						"fieldtype": "Link",
						"options": dimension.doctype,
						"width": 110,
					}
				)

		columns.extend(
			[
				{
					"label": _("Stock UOM"),
					"fieldname": "stock_uom",
					"fieldtype": "Link",
					"options": "UOM",
					"width": 90,
				},
				{
					"label": _("Balance Qty"),
					"fieldname": "bal_qty",
					"fieldtype": "Float",
					"width": 100,
					"convertible": "qty",
				},
				{
					"label": _("Balance Value"),
					"fieldname": "bal_val",
					"fieldtype": "Currency",
					"width": 100,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("Opening Qty"),
					"fieldname": "opening_qty",
					"fieldtype": "Float",
					"width": 100,
					"convertible": "qty",
				},
				{
					"label": _("Opening Value"),
					"fieldname": "opening_val",
					"fieldtype": "Currency",
					"width": 110,
					"options": "Company:company:default_currency",
				},
				{
					"label": _("In Qty"),
					"fieldname": "in_qty",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Float", "width": 80},
				{
					"label": _("Out Qty"),
					"fieldname": "out_qty",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Float", "width": 80},
				{
					"label": _("Valuation Rate"),
					"fieldname": "val_rate",
					"fieldtype": self.filters.valuation_field_type or "Currency",
					"width": 90,
					"convertible": "rate",
					"options": "Company:company:default_currency"
					if self.filters.valuation_field_type == "Currency"
					else None,
				},
				{
					"label": _("Reserved Stock"),
					"fieldname": "reserved_stock",
					"fieldtype": "Float",
					"width": 80,
					"convertible": "qty",
				},
				{
					"label": _("Company"),
					"fieldname": "company",
					"fieldtype": "Link",
					"options": "Company",
					"width": 100,
				},
			]
		)

		if self.filters.get("show_stock_ageing_data"):
			columns += [
				{"label": _("Average Age"), "fieldname": "average_age", "width": 100},
				{"label": _("Earliest Age"), "fieldname": "earliest_age", "width": 100},
				{"label": _("Latest Age"), "fieldname": "latest_age", "width": 100},
			]

		if self.filters.get("show_variant_attributes"):
			columns += [
				{"label": att_name, "fieldname": att_name, "width": 100}
				for att_name in get_variants_attributes()
			]

		return columns

	def add_additional_uom_columns(self):
		if not self.filters.get("include_uom"):
			return

		conversion_factors = self.get_itemwise_conversion_factor()
		add_additional_uom_columns(self.columns, self.data, self.filters.include_uom, conversion_factors)

	def get_itemwise_conversion_factor(self):
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		table = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			frappe.qb.from_(table)
			.select(
				table.conversion_factor,
				table.parent,
			)
			.where((table.parenttype == "Item") & (table.uom == self.filters.include_uom))
		)

		if items:
			query = query.where(table.parent.isin(items))

		result = query.run(as_dict=1)
		if not result:
			return {}

		return {d.parent: d.conversion_factor for d in result}

	def get_variant_values_for(self):
		"""Returns variant values for items."""
		attribute_map = {}
		items = []
		if self.filters.item_code or self.filters.item_group:
			items = [d.item_code for d in self.data]

		filters = {}
		if items:
			filters = {"parent": ("in", items)}

		attribute_info = frappe.get_all(
			"Item Variant Attribute",
			fields=["parent", "attribute", "attribute_value"],
			filters=filters,
		)

		for attr in attribute_info:
			attribute_map.setdefault(attr["parent"], {})
			attribute_map[attr["parent"]].update({attr["attribute"]: attr["attribute_value"]})

		return attribute_map

	def get_opening_vouchers(self):
		opening_vouchers = {"Stock Entry": [], "Stock Reconciliation": []}

		se = frappe.qb.DocType("Stock Entry")
		sr = frappe.qb.DocType("Stock Reconciliation")

		vouchers_data = (
			frappe.qb.from_(
				(
					frappe.qb.from_(se)
					.select(se.name, Coalesce("Stock Entry").as_("voucher_type"))
					.where((se.docstatus == 1) & (se.posting_date <= self.to_date) & (se.is_opening == "Yes"))
				)
				+ (
					frappe.qb.from_(sr)
					.select(sr.name, Coalesce("Stock Reconciliation").as_("voucher_type"))
					.where(
						(sr.docstatus == 1)
						& (sr.posting_date <= self.to_date)
						& (sr.purpose == "Opening Stock")
					)
				)
			).select("voucher_type", "name")
		).run(as_dict=True)

		if vouchers_data:
			for d in vouchers_data:
				opening_vouchers[d.voucher_type].append(d.name)

		return opening_vouchers

	@staticmethod
	def get_inventory_dimension_fields():
		return [dimension.fieldname for dimension in get_inventory_dimensions()]

	@staticmethod
	def get_opening_fifo_queue(report_data):
		opening_fifo_queue = report_data.get("opening_fifo_queue") or []
		for row in opening_fifo_queue:
			row[1] = getdate(row[1])

		return opening_fifo_queue


def filter_items_with_no_transactions(
	iwb_map, float_precision: float, inventory_dimensions: list | None = None
):
	pop_keys = []
	for group_by_key in iwb_map:
		qty_dict = iwb_map[group_by_key]

		no_transactions = True
		for key, val in qty_dict.items():
			if inventory_dimensions and key in inventory_dimensions:
				continue

			if key in [
				"item_code",
				"warehouse",
				"item_name",
				"item_group",
				"project",
				"stock_uom",
				"company",
				"opening_fifo_queue",
			]:
				continue

			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			pop_keys.append(group_by_key)

	for key in pop_keys:
		iwb_map.pop(key)

	return iwb_map


def get_variants_attributes() -> list[str]:
	"""Return all item variant attributes."""
	return frappe.get_all("Item Attribute", pluck="name")
