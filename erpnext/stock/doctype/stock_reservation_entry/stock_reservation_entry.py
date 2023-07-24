# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum


class StockReservationEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		available_qty: DF.Float
		company: DF.Link | None
		delivered_qty: DF.Float
		item_code: DF.Link | None
		project: DF.Link | None
		reserved_qty: DF.Float
		status: DF.Literal[
			"Draft", "Partially Reserved", "Reserved", "Partially Delivered", "Delivered", "Cancelled"
		]
		stock_uom: DF.Link | None
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_qty: DF.Float
		voucher_type: DF.Literal["", "Sales Order"]
		warehouse: DF.Link | None
	# end: auto-generated types
	def validate(self) -> None:
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_mandatory()
		self.validate_for_group_warehouse()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)

	def on_submit(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def on_cancel(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def validate_mandatory(self) -> None:
		"""Raises exception if mandatory fields are not set."""

		mandatory = [
			"item_code",
			"warehouse",
			"voucher_type",
			"voucher_no",
			"voucher_detail_no",
			"available_qty",
			"voucher_qty",
			"stock_uom",
			"reserved_qty",
			"company",
		]
		for d in mandatory:
			if not self.get(d):
				frappe.throw(_("{0} is required").format(self.meta.get_label(d)))

	def validate_for_group_warehouse(self) -> None:
		"""Raises exception if `Warehouse` is a Group Warehouse."""

		if frappe.get_cached_value("Warehouse", self.warehouse, "is_group"):
			frappe.throw(
				_("Stock cannot be reserved in group warehouse {0}.").format(frappe.bold(self.warehouse)),
				title=_("Invalid Warehouse"),
			)

	def update_status(self, status: str = None, update_modified: bool = True) -> None:
		"""Updates status based on Voucher Qty, Reserved Qty and Delivered Qty."""

		if not status:
			if self.docstatus == 2:
				status = "Cancelled"
			elif self.docstatus == 1:
				if self.reserved_qty == self.delivered_qty:
					status = "Delivered"
				elif self.delivered_qty and self.delivered_qty < self.reserved_qty:
					status = "Partially Delivered"
				elif self.reserved_qty == self.voucher_qty:
					status = "Reserved"
				else:
					status = "Partially Reserved"
			else:
				status = "Draft"

		frappe.db.set_value(self.doctype, self.name, "status", status, update_modified=update_modified)

	def update_reserved_qty_in_voucher(
		self, reserved_qty_field: str = "stock_reserved_qty", update_modified: bool = True
	) -> None:
		"""Updates total reserved qty in the voucher."""

		item_doctype = "Sales Order Item" if self.voucher_type == "Sales Order" else None

		if item_doctype:
			sre = frappe.qb.DocType("Stock Reservation Entry")
			reserved_qty = (
				frappe.qb.from_(sre)
				.select(Sum(sre.reserved_qty))
				.where(
					(sre.docstatus == 1)
					& (sre.voucher_type == self.voucher_type)
					& (sre.voucher_no == self.voucher_no)
					& (sre.voucher_detail_no == self.voucher_detail_no)
				)
			).run(as_list=True)[0][0] or 0

			frappe.db.set_value(
				item_doctype,
				self.voucher_detail_no,
				reserved_qty_field,
				reserved_qty,
				update_modified=update_modified,
			)


def validate_stock_reservation_settings(voucher: object) -> None:
	"""Raises an exception if `Stock Reservation` is not enabled or `Voucher Type` is not allowed."""

	if not frappe.db.get_single_value("Stock Settings", "enable_stock_reservation"):
		frappe.throw(
			_("Please enable {0} in the {1}.").format(
				frappe.bold("Stock Reservation"), frappe.bold("Stock Settings")
			)
		)

	# Voucher types allowed for stock reservation
	allowed_voucher_types = ["Sales Order"]

	if voucher.doctype not in allowed_voucher_types:
		frappe.throw(
			_("Stock Reservation can only be created against {0}.").format(", ".join(allowed_voucher_types))
		)


def get_available_qty_to_reserve(item_code: str, warehouse: str) -> float:
	"""Returns `Available Qty to Reserve (Actual Qty - Reserved Qty)` for Item and Warehouse combination."""

	from erpnext.stock.utils import get_stock_balance

	available_qty = get_stock_balance(item_code, warehouse)

	if available_qty:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		reserved_qty = (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		).run()[0][0] or 0.0

		if reserved_qty:
			return available_qty - reserved_qty

	return available_qty


def get_stock_reservation_entries_for_voucher(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None, fields: list[str] = None
) -> list[dict]:
	"""Returns list of Stock Reservation Entries against a Voucher."""

	if not fields or not isinstance(fields, list):
		fields = [
			"name",
			"item_code",
			"warehouse",
			"voucher_detail_no",
			"reserved_qty",
			"delivered_qty",
			"stock_uom",
		]

	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
	)

	for field in fields:
		query = query.select(sre[field])

	if voucher_detail_no:
		query = query.where(sre.voucher_detail_no == voucher_detail_no)

	return query.run(as_dict=True)


def get_sre_reserved_qty_details_for_item_and_warehouse(
	item_code_list: list, warehouse_list: list
) -> dict:
	"""Returns a dict like {("item_code", "warehouse"): "reserved_qty", ... }."""

	sre_details = {}

	if item_code_list and warehouse_list:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		sre_data = (
			frappe.qb.from_(sre)
			.select(
				sre.item_code,
				sre.warehouse,
				Sum(sre.reserved_qty - sre.delivered_qty).as_("reserved_qty"),
			)
			.where(
				(sre.docstatus == 1)
				& (sre.item_code.isin(item_code_list))
				& (sre.warehouse.isin(warehouse_list))
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
			.groupby(sre.item_code, sre.warehouse)
		).run(as_dict=True)

		if sre_data:
			sre_details = {(d["item_code"], d["warehouse"]): d["reserved_qty"] for d in sre_data}

	return sre_details


def get_sre_reserved_qty_for_item_and_warehouse(item_code: str, warehouse: str) -> float:
	"""Returns `Reserved Qty` for Item and Warehouse combination."""

	reserved_qty = 0.0

	if item_code and warehouse:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		return (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		).run(as_list=True)[0][0] or 0.0

	return reserved_qty


def get_sre_reserved_qty_details_for_voucher(voucher_type: str, voucher_no: str) -> dict:
	"""Returns a dict like {"voucher_detail_no": "reserved_qty", ... }."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	data = (
		frappe.qb.from_(sre)
		.select(
			sre.voucher_detail_no,
			(Sum(sre.reserved_qty) - Sum(sre.delivered_qty)).as_("reserved_qty"),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.groupby(sre.voucher_detail_no)
	).run(as_list=True)

	return frappe._dict(data)


def get_sre_reserved_qty_details_for_voucher_detail_no(
	voucher_type: str, voucher_no: str, voucher_detail_no: str
) -> list:
	"""Returns a list like ["warehouse", "reserved_qty"]."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	reserved_qty_details = (
		frappe.qb.from_(sre)
		.select(sre.warehouse, (Sum(sre.reserved_qty) - Sum(sre.delivered_qty)))
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.voucher_detail_no == voucher_detail_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
		.groupby(sre.warehouse)
	).run(as_list=True)

	if reserved_qty_details:
		return reserved_qty_details[0]

	return reserved_qty_details


def has_reserved_stock(voucher_type: str, voucher_no: str, voucher_detail_no: str = None) -> bool:
	"""Returns True if there is any Stock Reservation Entry for the given voucher."""

	if get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	):
		return True

	return False


@frappe.whitelist()
def cancel_stock_reservation_entries(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None, notify: bool = True
) -> None:
	"""Cancel Stock Reservation Entries for the given voucher."""

	sre_list = get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	)

	if sre_list:
		for sre in sre_list:
			frappe.get_doc("Stock Reservation Entry", sre.name).cancel()

		if notify:
			frappe.msgprint(_("Stock Reservation Entries Cancelled"), alert=True, indicator="red")
