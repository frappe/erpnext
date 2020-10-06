# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class StockEntryType(Document):
	pass


@frappe.whitelist()
def get_stock_entry_type_details(stock_entry_type):
	doc = frappe.get_cached_doc("Stock Entry Type", stock_entry_type)
	out = frappe._dict({
		'source_warehouse_type': doc.source_warehouse_type,
		'target_warehouse_type': doc.target_warehouse_type,
	})

	if doc.is_opening:
		out.is_opening = doc.is_opening
		if doc.posting_date:
			out.posting_date = doc.posting_date

	return out