# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.mapper import map_docs
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from erpnext.accounts.report.sales_items_to_be_billed.sales_items_to_be_billed import ItemsToBeBilled


def execute(filters=None):
	return ItemsToBeBilled(filters).run("Customer", claim_billing=True)

@frappe.whitelist()
def claim_items_invoice(data, target_doc):
	so_source = [data.get('name') if data.get('doctype') == "Sales Order"]
	so_source = [data.get('name') if data.get('doctype') == "Sales Order"]
	so_source = [data.get('name') if data.get('doctype') == "Sales Order"]
	so_source = [data.get('name') if data.get('doctype') == "Sales Order"]
	print(data)
