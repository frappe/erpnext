# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum


class StockReservationEntry(Document):
	def validate(self) -> None:
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_mandatory()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)

	def on_submit(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def on_cancel(self) -> None:
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def validate_mandatory(self) -> None:
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

	def update_status(self, status: str = None, update_modified: bool = True) -> None:
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


@frappe.whitelist()
def get_available_qty_to_reserve(item_code, warehouse):
	from frappe.query_builder.functions import Sum

	from erpnext.stock.get_item_details import get_bin_details

	available_qty = get_bin_details(item_code, warehouse, include_child_warehouses=True).get(
		"actual_qty"
	)

	if available_qty:
		from erpnext.stock.doctype.warehouse.warehouse import get_child_warehouses

		warehouses = get_child_warehouses(warehouse)
		sre = frappe.qb.DocType("Stock Reservation Entry")
		reserved_qty = (
			frappe.qb.from_(sre)
			.select(Sum(sre.reserved_qty - sre.delivered_qty))
			.where(
				(sre.docstatus == 1)
				& (sre.item_code == item_code)
				& (sre.warehouse.isin(warehouses))
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
		).run()[0][0] or 0.0

		if reserved_qty:
			return available_qty - reserved_qty

	return available_qty


def get_stock_reservation_entries_for_voucher(
	voucher_type: str, voucher_no: str, voucher_detail_no: str = None, fields: list[str] = None
) -> list[dict]:
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


def get_sre_reserved_qty_details_for_voucher_detail_no(
	voucher_type: str, voucher_no: str, voucher_detail_no: str
) -> list:
	sre = frappe.qb.DocType("Stock Reservation Entry")
	return (
		frappe.qb.from_(sre)
		.select(sre.warehouse, (Sum(sre.reserved_qty) - Sum(sre.delivered_qty)).as_("reserved_qty"))
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.voucher_detail_no == voucher_detail_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.groupby(sre.warehouse)
	).run(as_list=True)[0]


def has_reserved_stock(voucher_type: str, voucher_no: str, voucher_detail_no: str = None) -> bool:
	if get_stock_reservation_entries_for_voucher(
		voucher_type, voucher_no, voucher_detail_no, fields=["name"]
	):
		return True

	return False


def get_sre_reserved_qty_details(item_code: str | list, warehouse: str | list) -> dict:
	sre_details = {}

	if item_code and warehouse:
		if isinstance(item_code, str):
			item_code = [item_code]
		if isinstance(warehouse, str):
			warehouse = [warehouse]

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
				& (sre.item_code.isin(item_code))
				& (sre.warehouse.isin(warehouse))
				& (sre.status.notin(["Delivered", "Cancelled"]))
			)
			.groupby(sre.item_code, sre.warehouse)
		).run(as_dict=True)

		if sre_data:
			sre_details = {(d["item_code"], d["warehouse"]): d["reserved_qty"] for d in sre_data}

	return sre_details
