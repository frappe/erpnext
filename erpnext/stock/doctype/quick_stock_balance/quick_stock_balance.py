# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.permissions import has_user_permission
from frappe.utils import cstr
from frappe.utils.nestedset import get_descendants_of

from erpnext import _refuse, require_user_permission
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
def get_stock_item_details(warehouse, date, item=None, barcode=None):
	if not frappe.has_permission("Item", "read"):
		_refuse()
	warehouse = cstr(warehouse)
	if not warehouse or not has_user_permission(frappe.get_doc("Warehouse", warehouse)):
		_refuse()
	if frappe.db.get_value("Warehouse", warehouse, "is_group"):
		for descendant in get_descendants_of("Warehouse", warehouse, ignore_permissions=True):
			require_user_permission("Warehouse", descendant)

	out = {}
	if barcode:
		out["item"] = frappe.db.get_value("Item Barcode", filters={"barcode": barcode}, fieldname=["parent"])
		if not out["item"]:
			frappe.throw(_("Invalid Barcode. There is no Item attached to this barcode."))
	else:
		out["item"] = cstr(item)

	if barcode:
		require_user_permission("Item", out["item"])
	elif not out["item"] or not has_user_permission(frappe.get_doc("Item", out["item"])):
		_refuse()

	barcodes = frappe.db.get_values("Item Barcode", filters={"parent": out["item"]}, fieldname=["barcode"])

	out["barcodes"] = [x[0] for x in barcodes]
	out["qty"] = get_stock_balance(out["item"], warehouse, date)
	out["value"] = get_stock_value_on(warehouse, date, out["item"])
	out["image"] = frappe.db.get_value("Item", filters={"name": out["item"]}, fieldname=["image"])
	return out
