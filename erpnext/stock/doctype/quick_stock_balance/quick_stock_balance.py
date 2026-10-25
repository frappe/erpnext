# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.permissions import has_user_permission
from frappe.query_builder import Order
from frappe.query_builder.functions import Sum
from frappe.utils import cstr, flt
from pypika import analytics as an

from erpnext import _refuse, require_user_permission
from erpnext.stock.utils import get_stock_value_on


class QuickStockBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date
		item: DF.Link
		item_barcode: DF.Data | None
		item_description: DF.SmallText | None
		item_name: DF.Data | None
		qty: DF.Float
		value: DF.Currency
		warehouse: DF.Link
	# end: auto-generated types

	pass


@frappe.whitelist()
def get_stock_item_details(warehouse: str, date: str, item: str | None = None, barcode: str | None = None):
	if not frappe.has_permission("Item", "read"):
		_refuse()
	warehouse = cstr(warehouse)
	if not warehouse or not has_user_permission(frappe.get_doc("Warehouse", warehouse)):
		_refuse()
	if frappe.db.get_value("Warehouse", warehouse, "is_group"):
		for child_warehouse in frappe.db.get_descendants("Warehouse", warehouse):
			require_user_permission("Warehouse", child_warehouse)

	out = {}
	if barcode:
		out["item"] = frappe.db.get_value("Item Barcode", filters={"barcode": barcode}, fieldname=["parent"])
		if not out["item"]:
			frappe.throw(_("Invalid Barcode. There is no Item attached to this barcode."))
		require_user_permission("Item", out["item"])
	else:
		item = cstr(item)
		out["item"] = item
		if not item or not has_user_permission(frappe.get_doc("Item", item)):
			_refuse()

	barcodes = frappe.db.get_values("Item Barcode", filters={"parent": out["item"]}, fieldname=["barcode"])

	out["barcodes"] = [x[0] for x in barcodes]
	out["qty"] = get_balance_qty(out["item"], warehouse, date)
	out["value"] = get_stock_value_on(warehouse, date, out["item"])
	out["image"] = frappe.db.get_value("Item", filters={"name": out["item"]}, fieldname=["image"])
	return out


def get_balance_qty(item_code, warehouse, date):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	latest_first = (
		an.RowNumber()
		.over(sle.warehouse)
		.orderby(sle.posting_datetime, order=Order.desc)
		.orderby(sle.creation, order=Order.desc)
	)
	ranked = (
		frappe.qb.from_(sle)
		.select(sle.qty_after_transaction, latest_first.as_("row_no"))
		.where(
			(sle.item_code == item_code)
			& (sle.is_cancelled == 0)
			& (sle.posting_date <= date)
			& (sle.warehouse.isin(get_leaf_warehouses(warehouse)))
		)
	).as_("ranked")

	result = frappe.qb.from_(ranked).select(Sum(ranked.qty_after_transaction)).where(ranked.row_no == 1).run()
	return flt(result[0][0]) if result else 0.0


def get_leaf_warehouses(warehouse):
	if not frappe.db.get_value("Warehouse", warehouse, "is_group"):
		return [warehouse]

	lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
	return frappe.get_all(
		"Warehouse", filters={"lft": (">", lft), "rgt": ("<", rgt), "is_group": 0}, pluck="name"
	) or [warehouse]
