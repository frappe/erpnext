# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
from erpnext.stock.utils import get_stock_balance, get_stock_value_on

class StockQuickBalance(Document):
	pass

@frappe.whitelist()
def get_item_stock_details(item, warehouse, date):
	out = {}
	barcodes = frappe.db.get_values("Item Barcode", filters={
		"parent": item}, fieldname=["barcode"])

	out["item_barcode"] = [x[0] for x in barcodes]
	out["qty"] = get_stock_balance(item, warehouse, date)
	out["value"] = get_stock_value_on(warehouse, date, item)
	out["image"] = frappe.db.get_value(
		"Item", filters={"name": item}, fieldname=["image"])
	return out

@frappe.whitelist()
def get_barcode_stock_details(barcode, warehouse, date):
	out = {}
	out["item"] = frappe.db.get_value(
		"Item Barcode", filters={"barcode": barcode}, fieldname=["parent"])

	if not out["item"]:
		frappe.throw(
			_("Invalid Barcode. There is no Item attached to this barcode."))
	else:
		details = frappe.db.get_value("Item", filters={"name": out["item"]}, fieldname=[
									  "item_name", "description"], as_dict=1)
		out["item_name"], out["item_description"] = details["item_name"], details["description"]
		return out