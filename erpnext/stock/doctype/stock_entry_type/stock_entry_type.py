# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint
from frappe.model.document import Document
from six import string_types
import json

class StockEntryType(Document):
	pass


@frappe.whitelist()
def get_stock_entry_type_details(args):
	from erpnext.stock.doctype.stock_entry.stock_entry import get_item_expense_accounts

	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	if not args.stock_entry_type:
		frappe.throw(_("Stock Entry Type is mandatory"))

	doc = frappe.get_cached_doc("Stock Entry Type", args.stock_entry_type)
	out = frappe._dict({
		"parent": frappe._dict({
			'source_warehouse_type': doc.source_warehouse_type,
			'target_warehouse_type': doc.target_warehouse_type,
		}),
		"items": {}
	})

	if doc.is_opening:
		out.parent.is_opening = doc.is_opening
		args.is_opening = out.parent.is_opening
		if doc.posting_date:
			out.parent.posting_date = doc.posting_date

	out.parent.customer_provided = cint(doc.customer_provided == "Yes")

	if args.get('items'):
		out['items'] = get_item_expense_accounts(args)

	return out
