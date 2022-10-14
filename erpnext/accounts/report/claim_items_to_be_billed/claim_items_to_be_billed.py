# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import json
import frappe
from frappe.model.mapper import map_docs
from erpnext.accounts.report.sales_items_to_be_billed.sales_items_to_be_billed import ItemsToBeBilled
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice as invoice_from_sales_order
from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice as invoice_from_delivery_note
from six import string_types


def execute(filters=None):
	return ItemsToBeBilled(filters).run("Customer", claim_billing=True)


@frappe.whitelist()
def make_claim_sales_invoice(data, customer):
	if isinstance(data, string_types):
		data = json.loads(data)

	sales_orders = [item.get('name') for item in data if item.get('doctype') == "Sales Order"]
	sales_order_rows = [item.get('row_name') for item in data if item.get('doctype') == "Sales Order"]

	delivery_notes = [item.get('name') for item in data if item.get('doctype') == "Delivery Note"]
	delivery_note_rows = [item.get('row_name') for item in data if item.get('doctype') == "Delivery Note"]

	target_doc = frappe.new_doc("Sales Invoice")
	target_doc.customer = customer
	target_doc.bill_to = customer
	target_doc.claim_billing = 1

	frappe.flags.selected_children = delivery_note_rows
	for name in delivery_notes:
		target_doc = invoice_from_delivery_note(name, target_doc, only_items=True, skip_postprocess=True)

	frappe.flags.selected_children = sales_order_rows
	for name in sales_orders:
		target_doc = invoice_from_sales_order(name, target_doc, only_items=True, skip_postprocess=True)

	target_doc.ignore_pricing_rule = 1
	target_doc.run_method("set_missing_values")
	target_doc.run_method("append_taxes_from_master")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc
