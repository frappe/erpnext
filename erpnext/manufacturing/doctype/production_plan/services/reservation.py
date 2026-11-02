# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Stock reservation for Production Plan (extracted from production_plan.py)."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt, parse_json

from erpnext.deprecation_dumpster import deprecated
from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation

_RESERVATION_TABLES = {
	"sub_assembly_items": {
		"table_name": "sub_assembly_items",
		"qty_field": "required_qty",
		"warehouse_field": "fg_warehouse",
	},
	"mr_items": {
		"table_name": "mr_items",
		"qty_field": "required_bom_qty",
		"warehouse_field": "warehouse",
	},
}


def get_reserved_qty_for_production_plan(item_code, warehouse):
	plan_reservations = _get_plan_reservations(item_code)
	if not plan_reservations:
		return None

	work_order_reservations = _get_work_order_reservations(item_code, list(plan_reservations))
	reserved_qty = 0.0
	for plan, plan_qty_by_warehouse in plan_reservations.items():
		reserved_qty += _get_remaining_reserved_qty(
			plan_qty_by_warehouse, work_order_reservations.get(plan, {}), warehouse
		)

	return reserved_qty


def _get_remaining_reserved_qty(plan_qty_by_warehouse, work_order_qty_by_warehouse, warehouse):
	remaining_qty_by_warehouse = {
		plan_warehouse: max(qty - work_order_qty_by_warehouse.get(plan_warehouse, 0.0), 0.0)
		for plan_warehouse, qty in plan_qty_by_warehouse.items()
	}
	total_remaining_qty = sum(remaining_qty_by_warehouse.values())
	if not total_remaining_qty:
		return 0.0

	matched_qty = sum(plan_qty_by_warehouse.values()) - total_remaining_qty
	unmatched_qty = min(sum(work_order_qty_by_warehouse.values()) - matched_qty, total_remaining_qty)
	remaining_qty = remaining_qty_by_warehouse.get(warehouse, 0.0)
	return remaining_qty - remaining_qty * unmatched_qty / total_remaining_qty


def _get_plan_reservations(item_code):
	return _group_by_plan_and_warehouse(
		_get_material_request_plan_query(item_code), _get_sub_assembly_plan_query(item_code)
	)


def _get_material_request_plan_query(item_code):
	table = frappe.qb.DocType("Production Plan")
	child = frappe.qb.DocType("Material Request Plan Item")
	return (
		frappe.qb.from_(table)
		.inner_join(child)
		.on(table.name == child.parent)
		.select(
			table.name.as_("production_plan"),
			child.warehouse,
			Sum(child.required_bom_qty).as_("reserved_qty"),
		)
		.where(_is_open_plan(table) & (child.item_code == item_code))
		.groupby(table.name, child.warehouse)
	)


def _get_sub_assembly_plan_query(item_code):
	table = frappe.qb.DocType("Production Plan")
	child = frappe.qb.DocType("Production Plan Sub Assembly Item")
	return (
		frappe.qb.from_(table)
		.inner_join(child)
		.on(table.name == child.parent)
		.select(
			table.name.as_("production_plan"),
			child.fg_warehouse.as_("warehouse"),
			Sum(child.required_qty).as_("reserved_qty"),
		)
		.where(
			_is_open_plan(table)
			& (child.production_item == item_code)
			& (child.type_of_manufacturing == "In House")
		)
		.groupby(table.name, child.fg_warehouse)
	)


def _is_open_plan(table):
	return (table.docstatus == 1) & table.status.notin(["Completed", "Closed"])


def _get_work_order_reservations(item_code, plan_names):
	work_order = frappe.qb.DocType("Work Order")
	work_order_item = frappe.qb.DocType("Work Order Item")
	query = (
		frappe.qb.from_(work_order)
		.from_(work_order_item)
		.select(
			work_order.production_plan,
			work_order_item.source_warehouse.as_("warehouse"),
			Sum(work_order_item.required_qty).as_("reserved_qty"),
		)
		.where(
			(work_order_item.item_code == item_code)
			& (work_order_item.parent == work_order.name)
			& (work_order.docstatus == 1)
			& (IfNull(work_order_item.source_warehouse, "") != "")
			& work_order.production_plan.isin(plan_names)
		)
		.groupby(work_order.production_plan, work_order_item.source_warehouse)
	)
	return _group_by_plan_and_warehouse(query)


def _group_by_plan_and_warehouse(*queries):
	reservations = defaultdict(lambda: defaultdict(float))
	for query in queries:
		for row in query.run(as_dict=True):
			reservations[row.production_plan][row.warehouse] += flt(row.reserved_qty)
	return reservations


@deprecated(
	f"{__name__}.get_reserved_qty_for_sub_assembly",
	"2026-10-07",
	"v18",
	"Use get_reserved_qty_for_production_plan, which also counts sub-assembly items.",
)
def get_reserved_qty_for_sub_assembly(item_code, warehouse):
	return get_reserved_qty_for_production_plan(item_code, warehouse)


class ProductionPlanStockReservation:
	"""Reservation lifecycle for a Production Plan.

	A Production Plan reserves stock for two of its child tables: the sub-assembly
	items it will manufacture and the raw materials of its material-request rows
	(see ``_RESERVATION_TABLES``). On submit the rows are reserved; on cancel the
	reservations are released.

	The reserved-qty *query* helpers in this module
	(``get_reserved_qty_for_production_plan`` etc.) are read-only and answer "how
	much is reserved?" for bins and reports, so they stay module-level functions
	rather than methods, mirroring the engine's own query helpers.
	"""

	def __init__(self, doc):
		self.doc = doc

	def reserve(self, items: str | list | None = None, table_name: str | None = None, notify: bool = False):
		"""Reserve (docstatus 1) or release (docstatus 2) stock for the plan's tables."""
		if items and isinstance(items, str):
			items = parse_json(items)

		for child_table_name, table in _RESERVATION_TABLES.items():
			if table_name and table_name != child_table_name:
				continue
			self._reserve_or_cancel_plan_table(items, table)

		self.doc.reload()

	def _reserve_or_cancel_plan_table(self, items, table):
		sre = StockReservation(self.doc, items=items, **table)
		if self.doc.docstatus == 1:
			if sre.make_stock_reservation_entries():
				frappe.msgprint(_("Stock Reservation Entries Created"), alert=True)
		elif self.doc.docstatus == 2:
			sre.cancel_stock_reservation_entries()

	def cancel(self, sre_list: str | list | None = None):
		"""Cancel specific (or all) Stock Reservation Entries held by the plan."""
		StockReservation(self.doc).cancel_stock_reservation_entries(sre_list)
		self.doc.reload()

	def release_untouched(self) -> None:
		sre_list = frappe.get_all(
			"Stock Reservation Entry",
			filters={
				"voucher_type": self.doc.doctype,
				"voucher_no": self.doc.name,
				"docstatus": 1,
				"status": ("in", ["Reserved", "Partially Reserved"]),
			},
			pluck="name",
		)
		for sre_name in sre_list:
			sre_doc = frappe.get_doc("Stock Reservation Entry", sre_name)
			sre_doc.flags.ignore_permissions = True
			sre_doc.cancel()

	def reserve_received(self, receipt: Document, rows: list) -> None:
		unclaimed_qty = self.get_unclaimed_qty({plan_row for _row, plan_row in rows})
		items = []
		for row, plan_row in rows:
			qty = flt(min(row.stock_qty, unclaimed_qty[plan_row]), row.precision("stock_qty"))
			if qty <= 0:
				continue

			unclaimed_qty[plan_row] -= qty
			items.append(get_received_item(receipt, row, plan_row, qty))

		if not items:
			return

		StockReservation(
			self.doc, items=items, **_RESERVATION_TABLES["mr_items"]
		).make_stock_reservation_entries()
		self.hand_off_to_work_orders(items)

	def hand_off_to_work_orders(self, items: list) -> None:
		work_order_rows = self.get_reserving_work_order_items(list({item.item_code for item in items}))
		work_order_items = [
			frappe._dict(voucher_detail_no=row.name, from_voucher_detail_no=item.voucher_detail_no)
			for item in items
			for row in work_order_rows
			if row.item_code == item.item_code
		]
		if work_order_items:
			self.hand_off("Work Order", work_order_items)
			self.update_work_order_status({row.parent for row in work_order_rows})

	def hand_off(self, to_doctype: str, items: list | None = None) -> None:
		StockReservation(self.doc, items=items).transfer_reservation_entries_to(
			self.doc.name, from_doctype=self.doc.doctype, to_doctype=to_doctype
		)

	def update_work_order_status(self, work_orders: set) -> None:
		for name in work_orders:
			work_order = frappe.get_doc("Work Order", name)
			work_order.db_set("status", work_order.get_status())

	def get_reserving_work_order_items(self, item_codes: list) -> list:
		work_order = frappe.qb.DocType("Work Order")
		work_order_item = frappe.qb.DocType("Work Order Item")
		return (
			frappe.qb.from_(work_order)
			.inner_join(work_order_item)
			.on(work_order_item.parent == work_order.name)
			.select(work_order_item.name, work_order_item.item_code, work_order_item.parent)
			.where(
				(work_order.production_plan == self.doc.name)
				& (work_order.docstatus == 1)
				& (work_order.reserve_stock == 1)
				& (work_order.status != "Closed")
				& work_order_item.item_code.isin(item_codes)
			)
		).run(as_dict=True)

	def get_unclaimed_qty(self, plan_rows: set) -> defaultdict:
		unclaimed_qty = defaultdict(float)
		for row in self.doc.mr_items:
			if row.name in plan_rows:
				unclaimed_qty[row.name] += flt(row.required_bom_qty)

		sre = frappe.qb.DocType("Stock Reservation Entry")
		claimed_qty = (
			frappe.qb.from_(sre)
			.select(sre.voucher_detail_no, Sum(sre.reserved_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.voucher_type == self.doc.doctype)
				& (sre.voucher_no == self.doc.name)
				& sre.voucher_detail_no.isin(list(plan_rows))
			)
			.groupby(sre.voucher_detail_no)
		).run()
		for plan_row, qty in claimed_qty:
			unclaimed_qty[plan_row] -= flt(qty)

		return unclaimed_qty


def get_received_item(receipt: Document, row: Document, plan_row: str, qty: float) -> frappe._dict:
	item = frappe._dict(
		{
			"idx": row.idx,
			"item_code": row.item_code,
			"warehouse": row.warehouse,
			"stock_qty": qty,
			"voucher_detail_no": plan_row,
			"from_voucher_type": receipt.doctype,
			"from_voucher_no": receipt.name,
			"from_voucher_detail_no": row.name,
		}
	)
	if row.serial_and_batch_bundle:
		item.serial_and_batch_bundles = [row.serial_and_batch_bundle]

	return item


def hand_off_reserved_stock(plan: str, to_doctype: str, items: list | None = None) -> None:
	ProductionPlanStockReservation(frappe.get_lazy_doc("Production Plan", plan)).hand_off(to_doctype, items)


def reserve_received_stock(receipt: Document) -> None:
	ReceivedStockReservation(receipt).reserve()


class ReceivedStockReservation:
	def __init__(self, doc):
		self.doc = doc

	def reserve(self) -> None:
		if self.doc.is_return or not frappe.get_single_value("Stock Settings", "enable_stock_reservation"):
			return

		for plan, rows in self.get_rows_by_plan().items():
			plan_doc = frappe.get_doc("Production Plan", plan)
			ProductionPlanStockReservation(plan_doc).reserve_received(self.doc, rows)

	def get_rows_by_plan(self) -> dict:
		production_plan_references = self.get_production_plan_references()
		if not production_plan_references:
			return {}

		reservable_plans = self.get_reservable_production_plans(production_plan_references)
		if not reservable_plans:
			return {}

		self.doc.reload()
		rows_by_plan = defaultdict(list)
		for row in self.doc.items:
			ref = production_plan_references.get(row.material_request_item)
			if ref and ref.production_plan in reservable_plans:
				rows_by_plan[ref.production_plan].append((row, ref.material_request_plan_item))

		return rows_by_plan

	def get_reservable_production_plans(self, production_plan_references: frappe._dict) -> set:
		"""Production Plans that opted into stock reservation (``reserve_stock``).

		A Production Plan only gets this flag set if "Auto Reserve Stock" was enabled in
		Stock Settings when it was created, or the user ticked "Reserve Stock" manually.
		Without this check, a Purchase Receipt would auto-reserve stock for every
		Production Plan whenever "Enable Stock Reservation" is on, ignoring both of those.
		"""
		plan_names = {ref.production_plan for ref in production_plan_references.values()}
		return {
			p.name
			for p in frappe.get_all(
				"Production Plan",
				filters={"name": ["in", list(plan_names)]},
				fields=["name", "reserve_stock"],
			)
			if p.reserve_stock
		}

	def get_production_plan_references(self) -> frappe._dict:
		production_plan_references = frappe._dict()
		material_request_items = []

		for row in self.doc.items:
			if row.material_request_item:
				material_request_items.append(row.material_request_item)

		if not material_request_items:
			return frappe._dict()

		items = frappe.get_all(
			"Material Request Item",
			fields=["material_request_plan_item", "production_plan", "name"],
			filters={"name": ["in", material_request_items], "docstatus": 1},
		)

		for item in items:
			if not item.production_plan:
				continue

			production_plan_references.setdefault(item.name, item)

		return production_plan_references


@frappe.whitelist()
def make_stock_reservation_entries(
	doc: str | Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Whitelisted entry point: verify Production Plan write access, then reserve stock."""
	doc = _load_production_plan(doc)
	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	ProductionPlanStockReservation(doc).reserve(items=items, table_name=table_name, notify=notify)


def reserve_stock_for_production_plan(
	doc: Document, items: str | list | None = None, table_name: str | None = None, notify: bool = False
):
	"""Reserve stock for a Production Plan. Internal: no permission check (also called
	from the Production Plan submit/cancel lifecycle)."""
	ProductionPlanStockReservation(doc).reserve(items=items, table_name=table_name, notify=notify)


@frappe.whitelist()
def cancel_stock_reservation_entries(doc: str | Document, sre_list: str | list):
	"""Whitelisted entry point: verify Production Plan write access, then cancel reservations."""
	doc = _load_production_plan(doc)
	frappe.has_permission("Production Plan", "write", doc=doc, throw=True)
	ProductionPlanStockReservation(doc).cancel(sre_list)


def _load_production_plan(doc: str | dict | Document) -> Document:
	if isinstance(doc, str | dict):
		doc = parse_json(doc)
		doc = frappe.get_doc("Production Plan", doc.get("name"))
	return doc
