# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from erpnext import require_user_permission
from erpnext.stock.utils import get_stock_balance, get_stock_value_on


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
	# The warehouse decides which stock this reports, and a User Permission on Warehouse is what
	# separates one caller's warehouses from another's. get_stock_balance() does check Item, but
	# at doctype level and never against the warehouse it reads, so the fence is unenforced here.
	#
	# The fence only, not a Warehouse DocPerm gate: this page is entitled to System Manager,
	# Stock User and Stock Manager, and warehouse.json ships a row for only Stock User -- a role
	# gate on Warehouse would refuse two of the three roles that own the page.
	require_user_permission("Warehouse", warehouse)

	out = {}
	if barcode:
		out["item"] = frappe.db.get_value("Item Barcode", filters={"barcode": barcode}, fieldname=["parent"])
		if not out["item"]:
			frappe.throw(_("Invalid Barcode. There is no Item attached to this barcode."))
	else:
		out["item"] = item

	# Resolved after the barcode lookup, because a barcode names its item indirectly and the
	# caller may be fenced away from whatever it resolves to.
	require_user_permission("Item", out["item"])

	barcodes = frappe.db.get_values("Item Barcode", filters={"parent": out["item"]}, fieldname=["barcode"])

	out["barcodes"] = [x[0] for x in barcodes]
	out["qty"] = get_stock_balance(out["item"], warehouse, date)
	out["value"] = get_stock_value_on(warehouse, date, out["item"])
	out["image"] = frappe.db.get_value("Item", filters={"name": out["item"]}, fieldname=["image"])
	return out
