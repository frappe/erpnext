# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Sum

from erpnext.utilities.transaction_base import TransactionBase


class StockReservationEntry(TransactionBase):
	def validate(self):
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_posting_time()
		self.validate_mandatory()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)

	def on_submit(self):
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def on_cancel(self):
		self.update_reserved_qty_in_voucher()
		self.update_status()

	def validate_mandatory(self):
		mandatory = [
			"item_code",
			"warehouse",
			"posting_date",
			"posting_time",
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

	def update_status(self, status=None, update_modified=True):
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

	def update_reserved_qty_in_voucher(self, update_modified=True):
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
			"Sales Order Item",
			self.voucher_detail_no,
			"stock_reserved_qty",
			reserved_qty,
			update_modified=update_modified,
		)


def get_stock_reservation_entry_for_voucher(voucher_type, voucher_no, voucher_detail_no=None):
	sre = frappe.qb.DocType("Stock Reservation Entry")
	query = (
		frappe.qb.from_(sre)
		.select(
			sre.name,
			sre.item_code,
			sre.warehouse,
			sre.voucher_detail_no,
			sre.reserved_qty,
			sre.delivered_qty,
			sre.stock_uom,
		)
		.where(
			(sre.docstatus == 1)
			& (sre.voucher_type == voucher_type)
			& (sre.voucher_no == voucher_no)
			& (sre.status.notin(["Delivered", "Cancelled"]))
		)
		.orderby(sre.creation)
	)

	if voucher_detail_no:
		query = query.where(sre.voucher_detail_no == voucher_detail_no)

	return query.run(as_dict=True)


def has_reserved_stock(voucher_type, voucher_no, voucher_detail_no=None):
	if get_stock_reservation_entry_for_voucher(voucher_type, voucher_no, voucher_detail_no):
		return True

	return False


def update_delivered_qty(doctype, sre_name, sre_field="against_sre", qty_field="stock_qty"):
	table = frappe.qb.DocType(doctype)
	delivered_qty = (
		frappe.qb.from_(table)
		.select(Sum(table[qty_field]))
		.where((table.docstatus == 1) & (table[sre_field] == sre_name))
	).run(as_list=True)[0][0] or 0.0

	sre_doc = frappe.get_doc("Stock Reservation Entry", sre_name)
	sre_doc.delivered_qty = delivered_qty
	sre_doc.db_update()
	sre_doc.update_status()


def get_stock_reservation_entry_for_items(items, sre_field="against_sre"):
	sre_details = {}

	sre_list = [item.get(sre_field) for item in items if item.get(sre_field)]

	if sre_list:
		sre = frappe.qb.DocType("Stock Reservation Entry")
		sre_data = (
			frappe.qb.from_(sre)
			.select(
				sre.name,
				sre.status,
				sre.docstatus,
				sre.item_code,
				sre.warehouse,
				sre.voucher_type,
				sre.voucher_no,
				sre.voucher_detail_no,
				sre.reserved_qty,
				sre.delivered_qty,
				sre.stock_uom,
			)
			.where(sre.name.isin(sre_list))
			.orderby(sre.creation)
		).run(as_dict=True)

		sre_details = {d.name: d for d in sre_data}

	return sre_details
