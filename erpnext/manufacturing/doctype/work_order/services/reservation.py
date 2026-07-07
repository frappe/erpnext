# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Stock reservation logic for Work Order.

Extracted from work_order.py. ``WorkOrderStockReservation`` wraps a Work Order
document (composition) and owns the reservation-related behaviour; the
module-level helpers are reused by the controller and by Production Plan.
work_order.py re-exports them to preserve whitelist dotted-paths and imports.
"""

from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import cint, flt, parse_json
from pypika import functions as fn

from erpnext.stock.doctype.stock_reservation_entry.stock_reservation_entry import StockReservation

_SCIO_FIELDS = [
	"item_code",
	"name",
	"qty as stock_qty",
	"produced_qty as stock_reserved_qty",
	"delivery_warehouse as warehouse",
	"parent as voucher_no",
	"parenttype as voucher_type",
	"delivered_qty",
]
_SO_FIELDS = [
	"item_code",
	"name",
	"stock_qty",
	"stock_reserved_qty",
	"warehouse",
	"parent as voucher_no",
	"parenttype as voucher_type",
	"delivered_qty",
]
_SERIAL_BATCH_FIELDS = [
	"`tabSerial and Batch Entry`.`serial_no`",
	"`tabSerial and Batch Entry`.`batch_no`",
	"`tabSerial and Batch Entry`.`qty`",
	"`tabSerial and Batch Bundle`.`warehouse`",
	"`tabSerial and Batch Bundle`.`item_code`",
	"`tabSerial and Batch Bundle`.`voucher_detail_no`",
]


class WorkOrderStockReservation:
	def __init__(self, doc):
		self.doc = doc

	def validate_fg_warehouse_for_reservation(self):
		if not (
			self.doc.reserve_stock
			and self.doc.sales_order
			and not self.doc.subcontracting_inward_order
			and not self.doc.production_plan_sub_assembly_item
		):
			return

		warehouses = frappe.get_all(
			"Sales Order Item",
			filters={"parent": self.doc.sales_order, "item_code": self.doc.production_item},
			pluck="warehouse",
		)
		if self.doc.fg_warehouse not in warehouses:
			self._throw_warehouse_not_allowed(warehouses)

	def _throw_warehouse_not_allowed(self, warehouses):
		frappe.throw(
			_("Warehouse {0} is not allowed for Sales Order {1}, it should be {2}").format(
				self.doc.fg_warehouse, self.doc.sales_order, warehouses[0]
			),
			title=_("Target Warehouse Reservation Error"),
		)

	def set_reserve_stock(self):
		for row in self.doc.required_items:
			row.reserve_stock = self.doc.reserve_stock

	def enable_auto_reserve_stock(self):
		if self.doc.is_new() and frappe.db.get_single_value("Stock Settings", "auto_reserve_stock"):
			self.doc.reserve_stock = 1

	def update_stock_reservation(self):
		self.doc.set_qty_change()
		reserve_stock_for_work_order(self.doc)
		self.doc.db_set("status", self.doc.get_status())

	def update_qty_in_stock_reservation(self, row, transferred_qty, row_wise_serial_batch):
		# `transferred_qty` is the absolute qty transferred to WIP recomputed from submitted stock
		# entries, so this method must also be able to *lower* it (e.g. when a transfer is cancelled).
		# A fully-transferred entry is "Closed"; it must stay eligible here, otherwise cancelling the
		# transfer can never reset its transferred_qty and the Store reservation is lost. Only truly
		# cancelled entries (docstatus 2) are excluded.
		names = frappe.get_all(
			"Stock Reservation Entry",
			filters={
				"voucher_no": self.doc.name,
				"item_code": row.item_code,
				"voucher_detail_no": row.name,
				"warehouse": row.source_warehouse,
				"docstatus": 1,
			},
			pluck="name",
			order_by="creation",
		)
		for name in names:
			transferred_qty = self._apply_transferred_qty(name, transferred_qty, row_wise_serial_batch)

	def _apply_transferred_qty(self, name, transferred_qty, row_wise_serial_batch):
		if transferred_qty < 0:
			return transferred_qty

		doc = frappe.get_doc("Stock Reservation Entry", name)
		qty_to_update, transferred_qty = self._split_transferred_qty(doc, transferred_qty)
		if qty_to_update < 0:
			return transferred_qty

		self._apply_reservation_transfer(doc, qty_to_update, row_wise_serial_batch)
		return transferred_qty

	@staticmethod
	def _split_transferred_qty(doc, transferred_qty):
		if transferred_qty > flt(doc.reserved_qty - doc.consumed_qty):
			qty_to_update = doc.reserved_qty - doc.transferred_qty
			return qty_to_update, transferred_qty - qty_to_update
		return transferred_qty, 0.0

	@staticmethod
	def _apply_reservation_transfer(doc, qty_to_update, row_wise_serial_batch):
		doc.db_set("transferred_qty", flt(qty_to_update), update_modified=False)
		if (doc.has_batch_no or doc.has_serial_no) and doc.reservation_based_on == "Serial and Batch":
			doc.consume_serial_batch_for_material_transfer(row_wise_serial_batch)

		if doc.transferred_qty >= doc.reserved_qty:
			doc.db_set("status", "Closed", update_modified=False)

		doc.update_status()
		doc.update_reserved_stock_in_bin()

	def update_consumed_qty_in_stock_reservation(self, item, consumed_qty, wip_warehouse):
		filters = {
			"voucher_no": self.doc.name,
			"item_code": item.item_code,
			"voucher_detail_no": item.name,
			"warehouse": wip_warehouse,
			"docstatus": 1,
		}
		if not self.doc.skip_transfer:
			filters["from_voucher_no"] = ("is", "set")

		row_wise_serial_batch = get_row_wise_serial_batch(self.doc.name, "Manufacture")
		names = frappe.get_all("Stock Reservation Entry", filters=filters, pluck="name", order_by="creation")
		for name in names:
			consumed_qty = self._apply_consumed_qty(name, consumed_qty, row_wise_serial_batch)

	@staticmethod
	def _apply_consumed_qty(name, consumed_qty, row_wise_serial_batch):
		consumed_qty = max(consumed_qty, 0)
		doc = frappe.get_doc("Stock Reservation Entry", name)
		qty_to_update = consumed_qty if consumed_qty < doc.reserved_qty else doc.reserved_qty
		if qty_to_update >= 0:
			doc.db_set("consumed_qty", flt(qty_to_update), update_modified=False)
			consumed_qty -= qty_to_update

		if (doc.has_batch_no or doc.has_serial_no) and doc.reservation_based_on == "Serial and Batch":
			doc.consume_serial_batch_for_material_transfer(row_wise_serial_batch)

		doc.update_status()
		doc.update_reserved_stock_in_bin()
		return consumed_qty

	def validate_reserved_qty(self):
		sre_details = get_sre_details(self.doc.name)
		for item in self.doc.required_items:
			if details := sre_details.get(item.name):
				if details.reserved_qty < details.consumed_qty:
					frappe.throw(
						_("Consumed Qty {0} cannot be greater than Reserved Qty {1} for item {2}").format(
							details.consumed_qty, details.reserved_qty, item.item_code
						)
					)

	def set_reserved_qty_for_wip_and_fg(self, stock_entry):
		if stock_entry.is_return:
			return

		stock_entry.reload()
		items = self._reservation_items_for(stock_entry)
		if not items:
			return

		reserve_stock_for_work_order(self.doc, list(items.values()), is_transfer=False, notify=True)

	def _reservation_items_for(self, stock_entry):
		is_finished_good = stock_entry.purpose == "Manufacture" and (
			self.doc.sales_order
			or self.doc.production_plan_sub_assembly_item
			or self.doc.subcontracting_inward_order
			or stock_entry.job_card
		)
		if is_finished_good:
			return self.get_finished_goods_for_reservation(stock_entry)
		if stock_entry.purpose == "Material Transfer for Manufacture":
			return self.get_list_of_materials_for_reservation(stock_entry)
		return frappe._dict()

	def get_list_of_materials_for_reservation(self, stock_entry):
		items = frappe._dict()
		voucher_detail_no = {d.item_code: d.name for d in self.doc.required_items}

		for row in stock_entry.items:
			if row.item_code not in items:
				items[row.item_code] = self._material_reservation_row(stock_entry, row, voucher_detail_no)
			else:
				items[row.item_code]["stock_qty"] += row.transfer_qty
				if row.serial_and_batch_bundle:
					items[row.item_code]["serial_and_batch_bundles"].append(row.serial_and_batch_bundle)

		return items

	def _material_reservation_row(self, stock_entry, row, voucher_detail_no):
		return frappe._dict(
			{
				"voucher_no": self.doc.name,
				"voucher_type": self.doc.doctype,
				"voucher_detail_no": voucher_detail_no.get(row.item_code),
				"item_code": row.item_code,
				"warehouse": row.t_warehouse,
				"stock_qty": row.transfer_qty,
				"from_voucher_no": stock_entry.name,
				"from_voucher_type": stock_entry.doctype,
				"from_voucher_detail_no": row.name,
				"serial_and_batch_bundles": [row.serial_and_batch_bundle],
			}
		)

	def get_finished_goods_for_reservation(self, stock_entry):
		item_details = self._finished_goods_item_details(stock_entry)
		if item_details is None:
			return

		items = frappe._dict()
		for item in item_details:
			self._reserve_finished_good(items, item, stock_entry)
		return items

	def _finished_goods_item_details(self, stock_entry):
		if self.doc.production_plan_sub_assembly_item:
			# Reserve the sub-assembly item for the final product for the work order.
			return self.get_wo_details()
		if self.doc.subcontracting_inward_order:
			return self.get_scio_details()
		if stock_entry.job_card:
			# Reserve the final product for the job card.
			finished_good = frappe.db.get_value("Job Card", stock_entry.job_card, "finished_good")
			if finished_good == self.doc.production_item:
				return None
			return self.get_items_to_reserve_for_job_card(stock_entry, finished_good)
		# Reserve the final product for the sales order.
		return self.get_so_details()

	def _reserve_finished_good(self, items, item, stock_entry):
		qty_to_reserve = flt(item.stock_qty) - flt(item.stock_reserved_qty + item.delivered_qty)
		if qty_to_reserve <= 0:
			return

		warehouse = self._reservation_warehouse(item)
		for row in stock_entry.items:
			if not self._is_reservable_fg_row(row, item, warehouse):
				continue

			reserved_qty = min(qty_to_reserve, row.transfer_qty)
			qty_to_reserve = qty_to_reserve - row.transfer_qty if qty_to_reserve > row.transfer_qty else 0
			if row.item_code not in items:
				items[row.item_code] = self._fg_reservation_row(item, row, reserved_qty, stock_entry)
			else:
				items[row.item_code]["stock_qty"] += reserved_qty

	@staticmethod
	def _is_reservable_fg_row(row, item, warehouse):
		return bool(
			row.t_warehouse
			and row.is_finished_item
			and row.t_warehouse == warehouse
			and row.item_code == item.item_code
		)

	@staticmethod
	def _reservation_warehouse(item):
		if (
			item.get("parenttype") == "Work Order"
			and item.get("skip_transfer")
			and item.get("from_wip_warehouse")
		):
			return item.wip_warehouse
		return item.warehouse

	@staticmethod
	def _fg_reservation_row(item, row, reserved_qty, stock_entry):
		return frappe._dict(
			{
				"voucher_no": item.voucher_no,
				"voucher_type": item.voucher_type,
				"voucher_detail_no": item.name,
				"item_code": row.item_code,
				"warehouse": row.t_warehouse,
				"stock_qty": reserved_qty,
				"from_voucher_no": stock_entry.name,
				"from_voucher_type": stock_entry.doctype,
				"from_voucher_detail_no": row.name,
				"serial_and_batch_bundles": [row.serial_and_batch_bundle],
			}
		)

	def get_items_to_reserve_for_job_card(self, stock_entry, finished_good):
		for row in stock_entry.items:
			if row.item_code == finished_good:
				return self._job_card_reservation_details(stock_entry, row, finished_good)
		return []

	def _job_card_reservation_details(self, stock_entry, row, finished_good):
		name = frappe.db.get_value(
			"Work Order Item", {"item_code": finished_good, "parent": self.doc.name}, "name"
		)
		pending_qty = row.qty - self._reserved_qty_for_job_card(finished_good, name, row.t_warehouse)
		if pending_qty <= 0:
			return []

		return [
			frappe._dict(
				{
					"item_code": row.item_code,
					"stock_qty": pending_qty,
					"stock_reserved_qty": 0,
					"warehouse": row.t_warehouse,
					"voucher_no": stock_entry.work_order,
					"voucher_type": "Work Order",
					"name": name,
					"delivered_qty": 0,
				}
			)
		]

	def _reserved_qty_for_job_card(self, finished_good, name, warehouse):
		sres = frappe.get_all(
			"Stock Reservation Entry",
			fields=["reserved_qty"],
			filters={
				"voucher_no": self.doc.name,
				"item_code": finished_good,
				"voucher_detail_no": name,
				"warehouse": warehouse,
				"docstatus": 1,
				"status": "Reserved",
			},
		)
		return sum(d.reserved_qty for d in sres)

	def get_wo_details(self):
		wo = frappe.qb.DocType("Work Order")
		item = frappe.qb.DocType("Work Order Item")
		query = (
			frappe.qb.from_(wo)
			.inner_join(item)
			.on(wo.name == item.parent)
			.select(
				item.name,
				item.required_qty.as_("stock_qty"),
				item.transferred_qty.as_("delivered_qty"),
				item.stock_reserved_qty,
				item.source_warehouse.as_("warehouse"),
				wo.wip_warehouse,
				wo.skip_transfer,
				wo.from_wip_warehouse,
				item.parenttype,
				item.item_code,
				item.parent.as_("voucher_no"),
				item.parenttype.as_("voucher_type"),
			)
			.where(self._wo_details_filter(wo, item))
		)
		return query.run(as_dict=1)

	def _wo_details_filter(self, wo, item):
		return (
			(item.item_code == self.doc.production_item)
			& (wo.docstatus == 1)
			& (wo.production_plan == self.doc.production_plan)
			& (IfNull(wo.production_plan_sub_assembly_item, "") != self.doc.production_plan_sub_assembly_item)
		)

	def get_scio_details(self):
		return frappe.get_all(
			"Subcontracting Inward Order Item",
			filters={"name": self.doc.subcontracting_inward_order_item, "docstatus": 1},
			fields=_SCIO_FIELDS,
		)

	def get_so_details(self):
		return frappe.get_all(
			"Sales Order Item",
			filters={"parent": self.doc.sales_order, "item_code": self.doc.production_item, "docstatus": 1},
			fields=_SO_FIELDS,
		)

	def get_voucher_details(self, stock_entry):
		if stock_entry.purpose == "Manufacture" and self.doc.sales_order:
			return frappe._dict({self.doc.production_item: self._so_voucher_detail()})
		return frappe._dict({d.item_code: d.name for d in self.doc.required_items})

	def _so_voucher_detail(self):
		return frappe.db.get_value(
			"Sales Order Item",
			{
				"parent": self.doc.sales_order,
				"item_code": self.doc.production_item,
				"docstatus": 1,
				"stock_reserved_qty": 0,
			},
			["name", "stock_qty", "stock_reserved_qty"],
			as_dict=1,
		)

	def cancel_reserved_qty_for_wip_and_fg(self, ste_doc):
		# Reservations created by this stock entry are identified by `from_voucher_no`. They can be
		# held against the Work Order *or* against another voucher -- e.g. the finished good of an
		# SO-linked Work Order is reserved against the Sales Order. They must be cancelled directly:
		# routing through the Work-Order-scoped `cancel_stock_reservation_entries` would silently skip
		# any entry whose `voucher_type`/`voucher_no` is not the Work Order, leaving the finished good
		# reserved and making the manufacture impossible to cancel (NegativeStockError).
		cancelled = False
		for row in ste_doc.items:
			sre_list = frappe.get_all(
				"Stock Reservation Entry",
				filters={"from_voucher_no": ste_doc.name, "from_voucher_detail_no": row.name, "docstatus": 1},
				pluck="name",
			)
			for name in sre_list:
				frappe.get_doc("Stock Reservation Entry", name).cancel()
				cancelled = True

		if cancelled:
			self.doc.reload()
			self.doc.db_set("status", self.doc.get_status())

	def release_reserved_qty_for_subcontract_transfer(self):
		"""Free this Work Order's own reservation for items sent to a subcontractor.

		A ``Send to Subcontractor`` Stock Entry raised against a Work Order consumes stock that
		the same Work Order reserved (e.g. the semi-finished item of a subcontracted operation).
		The sent qty is recorded as ``transferred_qty`` on the matching Stock Reservation Entries
		so the negative-stock guard stops treating it as reserved for "other transactions". The
		figure is recomputed from every submitted ``Send to Subcontractor`` entry for the Work
		Order, so it self-corrects on cancellation / reposting.

		Note: only qty-based reservations are handled here; serial/batch reservations are left to
		the existing material-transfer machinery.
		"""
		sent = self._subcontract_transferred_qty_by_item()

		entries = frappe.get_all(
			"Stock Reservation Entry",
			filters={"voucher_no": self.doc.name, "voucher_type": "Work Order", "docstatus": 1},
			fields=["name", "item_code", "warehouse", "reservation_based_on"],
			order_by="creation",
		)

		for entry in entries:
			if entry.reservation_based_on == "Serial and Batch":
				continue

			key = (entry.item_code, entry.warehouse)
			sre = frappe.get_doc("Stock Reservation Entry", entry.name)

			# Cap at what is still reservable (qty not already delivered/consumed). Always set the
			# value -- including back to 0 when nothing (or less) is now sent -- so cancelling a
			# transfer restores the reservation.
			available = flt(sre.reserved_qty) - flt(sre.consumed_qty) - flt(sre.delivered_qty)
			qty_to_set = max(min(flt(sent.get(key, 0.0)), available), 0.0)
			if key in sent:
				sent[key] = flt(sent[key]) - qty_to_set

			if flt(sre.transferred_qty) == qty_to_set:
				continue

			sre.db_set("transferred_qty", qty_to_set, update_modified=False)
			sre.update_status()
			sre.update_reserved_stock_in_bin()

	def _subcontract_transferred_qty_by_item(self):
		"""Qty sent to subcontractors for this Work Order, keyed by (item_code, source warehouse).

		The transfer Stock Entries are linked to the Work Order through its subcontracted Job Cards
		(Job Card -> Subcontracting Order / Purchase Order -> Send to Subcontractor entry), since the
		entry itself does not retain ``work_order``. Only submitted (docstatus 1) entries contribute,
		so a cancelled transfer drops out and the reservation is restored on the next recompute.
		"""
		job_cards = frappe.get_all(
			"Job Card", filters={"work_order": self.doc.name, "is_subcontracted": 1}, pluck="name"
		)
		if not job_cards:
			return {}

		sco_names = frappe.get_all(
			"Subcontracting Order Item", filters={"job_card": ["in", job_cards]}, pluck="parent"
		)
		po_names = frappe.get_all(
			"Purchase Order Item", filters={"job_card": ["in", job_cards]}, pluck="parent"
		)
		if not sco_names and not po_names:
			return {}

		ste = frappe.qb.DocType("Stock Entry")
		ste_child = frappe.qb.DocType("Stock Entry Detail")

		link = None
		if sco_names:
			link = ste.subcontracting_order.isin(list(set(sco_names)))
		if po_names:
			po_link = ste.purchase_order.isin(list(set(po_names)))
			link = po_link if link is None else (link | po_link)

		rows = (
			frappe.qb.from_(ste)
			.inner_join(ste_child)
			.on(ste_child.parent == ste.name)
			.select(ste_child.item_code, ste_child.s_warehouse, fn.Sum(ste_child.transfer_qty).as_("qty"))
			.where(
				(ste.docstatus == 1)
				& (ste.purpose == "Send to Subcontractor")
				& (ste_child.s_warehouse.isnotnull())
				& link
			)
			.groupby(ste_child.item_code, ste_child.s_warehouse)
		).run(as_dict=1)
		return {(d.item_code, d.s_warehouse): flt(d.qty) for d in rows}


@frappe.whitelist()
def make_stock_reservation_entries(
	doc: str | Document, items: str | list | None = None, is_transfer: bool = True, notify: bool = False
):
	"""Whitelisted entry point: verify Work Order write access, then reserve stock."""
	if isinstance(doc, str):
		doc = parse_json(doc)
		doc = frappe.get_doc("Work Order", doc.get("name"))

	frappe.has_permission("Work Order", "write", doc=doc, throw=True)
	reserve_stock_for_work_order(doc, items=items, is_transfer=is_transfer, notify=notify)


def reserve_stock_for_work_order(
	doc: Document, items: str | list | None = None, is_transfer: bool = True, notify: bool = False
):
	"""Reserve (or transfer/cancel) stock for a Work Order. Internal: no permission check.

	Called both by the whitelisted entry point above and from the Work Order /
	Stock Entry lifecycle, where the triggering user may legitimately lack direct
	Work Order write access.
	"""
	is_transfer = cint(is_transfer)
	if items and isinstance(items, str):
		items = parse_json(items)

	sre = StockReservation(doc, items=items)
	if doc.docstatus == 2 or doc.status == "Closed":
		sre.cancel_stock_reservation_entries()
	elif doc.docstatus == 1:
		_reserve_or_transfer(sre, doc, is_transfer)

	doc.reload()
	doc.db_set("status", doc.get_status())


def _reserve_or_transfer(sre, doc, is_transfer):
	if doc.production_plan and is_transfer:
		sre.transfer_reservation_entries_to(
			doc.production_plan, from_doctype="Production Plan", to_doctype="Work Order"
		)
	elif doc.subcontracting_inward_order and is_transfer:
		sre.transfer_reservation_entries_to(
			doc.subcontracting_inward_order,
			from_doctype="Subcontracting Inward Order",
			to_doctype="Work Order",
			against_fg_item=doc.subcontracting_inward_order_item,
			qty_change=doc.qty_change,
		)
	elif sre.make_stock_reservation_entries():
		frappe.msgprint(_("Stock Reservation Entries Created"), alert=True)


@frappe.whitelist()
def cancel_stock_reservation_entries(doc: str | dict, sre_list: str | list):
	"""Whitelisted entry point: verify Work Order write access, then cancel reservations."""
	if isinstance(doc, str):
		doc = parse_json(doc)
		doc = frappe.get_doc("Work Order", doc.get("name"))

	frappe.has_permission("Work Order", "write", doc=doc, throw=True)
	unreserve_stock_for_work_order(doc, sre_list)


def unreserve_stock_for_work_order(doc: Document, sre_list: str | list):
	"""Cancel stock reservation entries for a Work Order. Internal: no permission check."""
	sre = StockReservation(doc)
	sre.cancel_stock_reservation_entries(sre_list)

	doc.reload()
	doc.db_set("status", doc.get_status())


def get_sre_details(work_order):
	sre_details = frappe._dict()
	data = frappe.get_all(
		"Stock Reservation Entry",
		filters={"voucher_no": work_order, "docstatus": 1},
		fields=[
			"item_code",
			"warehouse",
			"reserved_qty",
			"transferred_qty",
			"consumed_qty",
			"voucher_detail_no",
		],
	)
	for row in data:
		_accumulate_sre_details(sre_details, row)
	return sre_details


def _accumulate_sre_details(sre_details, row):
	existing = sre_details.get(row.voucher_detail_no)
	if not existing:
		sre_details[row.voucher_detail_no] = row
		return

	existing.reserved_qty += row.reserved_qty
	existing.transferred_qty += row.transferred_qty
	existing.consumed_qty += row.consumed_qty


def get_consumed_qty(work_order, item_code):
	stock_entry = frappe.qb.DocType("Stock Entry")
	stock_entry_detail = frappe.qb.DocType("Stock Entry Detail")
	result = (
		frappe.qb.from_(stock_entry)
		.inner_join(stock_entry_detail)
		.on(stock_entry_detail.parent == stock_entry.name)
		.select(fn.Sum(stock_entry_detail.transfer_qty).as_("qty"))
		.where(_consumed_qty_filter(stock_entry, stock_entry_detail, work_order, item_code))
	).run()
	return flt(result[0][0]) if result else 0


def _consumed_qty_filter(stock_entry, stock_entry_detail, work_order, item_code):
	return (
		(stock_entry.work_order == work_order)
		& (stock_entry.purpose.isin(["Manufacture", "Material Consumption for Manufacture"]))
		& (stock_entry.docstatus == 1)
		& (stock_entry_detail.s_warehouse.isnotnull())
		& ((stock_entry_detail.item_code == item_code) | (stock_entry_detail.original_item == item_code))
	)


def get_reserved_qty_for_production(
	item_code: str,
	warehouse: str,
	non_completed_production_plans: list | None = None,
	check_production_plan: bool = False,
) -> float:
	"""Get total reserved quantity for any item in specified warehouse"""
	wo = frappe.qb.DocType("Work Order")
	wo_item = frappe.qb.DocType("Work Order Item")
	qty_field = wo_item.required_qty if check_production_plan else _production_reserved_qty_field(wo, wo_item)

	query = (
		frappe.qb.from_(wo)
		.from_(wo_item)
		.select(Sum(qty_field))
		.where(
			(wo_item.item_code == item_code)
			& (wo_item.parent == wo.name)
			& (wo.docstatus == 1)
			& (wo_item.source_warehouse == warehouse)
		)
	)
	query = _apply_production_plan_filter(
		query, wo, wo_item, check_production_plan, non_completed_production_plans
	)
	return query.run()[0][0] or 0.0


def _production_reserved_qty_field(wo, wo_item):
	qty_field = Case()
	qty_field = qty_field.when(
		(wo.skip_transfer == 0) & (wo_item.transferred_qty > wo_item.required_qty), 0.0
	)
	qty_field = qty_field.when(wo.skip_transfer == 0, wo_item.required_qty - wo_item.transferred_qty)
	return qty_field.else_(wo_item.required_qty - wo_item.consumed_qty)


def _apply_production_plan_filter(query, wo, wo_item, check_production_plan, non_completed_production_plans):
	if check_production_plan:
		query = query.where(wo.production_plan.isnotnull())
	else:
		query = query.where(
			(wo.status.notin(["Stopped", "Completed", "Closed"]))
			& (
				(wo_item.required_qty > wo_item.transferred_qty)
				| (wo_item.required_qty > wo_item.consumed_qty)
			)
		)

	if non_completed_production_plans:
		query = query.where(wo.production_plan.isin(non_completed_production_plans))
	return query


def get_row_wise_serial_batch(work_order, purpose=None):
	purpose = purpose or "Material Transfer for Manufacture"
	stock_entries = frappe.get_all(
		"Stock Entry",
		filters={"work_order": work_order, "purpose": purpose, "docstatus": 1},
		pluck="name",
	)

	row_wise_serial_batch = {}
	for entry in _serial_batch_entries(stock_entries):
		_accumulate_serial_batch(row_wise_serial_batch, entry)
	return row_wise_serial_batch


def _serial_batch_entries(stock_entries):
	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=_SERIAL_BATCH_FIELDS,
		filters=[
			["Serial and Batch Bundle", "voucher_type", "=", "Stock Entry"],
			["Serial and Batch Bundle", "voucher_no", "in", stock_entries],
			["Serial and Batch Bundle", "voucher_detail_no", "is", "set"],
			["Serial and Batch Bundle", "docstatus", "<", 2],
			["Serial and Batch Bundle", "is_cancelled", "=", 0],
			["Serial and Batch Entry", "qty", "<", 0],
		],
	)


def _accumulate_serial_batch(row_wise_serial_batch, entry):
	key = (entry.item_code, entry.warehouse)
	details = row_wise_serial_batch.setdefault(
		key, frappe._dict({"serial_nos": [], "batch_nos": defaultdict(float)})
	)
	if entry.serial_no:
		details.serial_nos.append(entry.serial_no)
	if entry.batch_no:
		details.batch_nos[entry.batch_no] += abs(entry.qty)
