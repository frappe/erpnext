# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt


class StockReservationEntry(Document):
	def validate(self) -> None:
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_amended_doc()
		self.validate_mandatory()
		self.validate_for_group_warehouse()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)
		self.validate_reserved_qty()

	def on_submit(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def on_update_after_submit(self) -> None:
		self.validate_reserved_qty()
		self.update_reserved_qty_in_voucher()
		self.update_status()
		self.reload()

	def on_cancel(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def validate_amended_doc(self) -> None:
		"""Raises exception if document is amended."""

		if self.amended_from:
			frappe.throw(
				_(
					f"Cannot amend {self.doctype} {frappe.bold(self.amended_from)}, please create a new one instead."
				)
			)

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

	def validate_reserved_qty(self) -> None:
		"""Validates `Reserved Qty`"""

		self.db_set(
			"available_qty",
			get_available_qty_to_reserve(self.item_code, self.warehouse, ignore_sre=self.name),
		)
		total_reserved_qty = get_sre_reserved_qty_for_voucher_detail_no(
			self.voucher_type, self.voucher_no, self.voucher_detail_no, ignore_sre=self.name
		)
		max_qty_can_be_reserved = min(self.available_qty, (self.voucher_qty - total_reserved_qty))

		qty_to_be_reserved = 0
		if self.reservation_based_on == "Qty":
			if self.sb_entries:
				self.sb_entries = []

			qty_to_be_reserved = self.reserved_qty
		elif self.reservation_based_on == "Serial and Batch":
			for entry in self.sb_entries:
				if self.has_serial_no and entry.qty != 1:
					frappe.throw(_(f"Row #{entry.idx}: Qty should be 1 for Serialized Item."))

				qty_to_be_reserved += entry.qty

			if not qty_to_be_reserved:
				frappe.throw(
					_("Please select Serial/Batch No to reserve or change Reservation Based On to Qty.")
				)

		if qty_to_be_reserved > max_qty_can_be_reserved:
			frappe.throw(
				_(f"Cannot reserve more than {frappe.bold(max_qty_can_be_reserved)} {self.stock_uom}.")
			)
		if qty_to_be_reserved <= self.delivered_qty:
			frappe.throw(_("Reserved Qty should be greater than Delivered Qty."))

		if self.reservation_based_on == "Serial and Batch":
			self.db_set("reserved_qty", qty_to_be_reserved)

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


def get_available_qty_to_reserve(item_code: str, warehouse: str, ignore_sre=None) -> float:
	"""Returns `Available Qty to Reserve (Actual Qty - Reserved Qty)` for Item and Warehouse combination."""

	from erpnext.stock.utils import get_stock_balance

	available_qty = get_stock_balance(item_code, warehouse)

	if available_qty:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		query = (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse == warehouse)
				& (sre.reserved_qty >= sre.delivered_qty)
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		)

		if ignore_sre:
			query = query.where(sre.name != ignore_sre)

		reserved_qty = query.run()[0][0] or 0.0

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


def get_sre_reserved_qty_for_voucher_detail_no(
	voucher_type: str, voucher_no: str, voucher_detail_no: str, ignore_sre=None
) -> float:
	"""Returns `Reserved Qty` against the Voucher."""

	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.select(
			(Sum(sre.reserved_qty) - Sum(sre.delivered_qty)),
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.voucher_detail_no == voucher_detail_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
	)

	if ignore_sre:
		query = query.where(sre.name != ignore_sre)

	reserved_qty = query.run(as_list=True)

	return flt(reserved_qty[0][0])


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
