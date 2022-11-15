# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
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

	sales_orders = [d.get('name') for d in data if d.get('doctype') == "Sales Order" and d.get('claim_customer') == customer]
	sales_order_rows = [d.get('row_name') for d in data if d.get('doctype') == "Sales Order" and d.get('claim_customer') == customer]

	delivery_notes = [d.get('name') for d in data if d.get('doctype') == "Delivery Note" and d.get('claim_customer') == customer]
	delivery_note_rows = [d.get('row_name') for d in data if d.get('doctype') == "Delivery Note" and d.get('claim_customer') == customer]

	if not sales_orders and not delivery_notes:
		frappe.throw(_("No unbilled Sales Orders or Delivery Notes in report against Claim {0}")
			.format(frappe.get_desk_link("Customer", customer)))

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
	target_doc.run_method("reset_taxes_and_charges")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc
