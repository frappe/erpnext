# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [_("Date") + "::240", _("Supplier") + "::240",  _("Voucher Type") + "::240",  _("Voucher No.") + "::240",  _("Invoice Amount") + ":Currency:120", _("Amount paid") + ":Currency:120", _("Outstanding Amount") + ":Currency:120", _("Currency") + "::240"]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	conditions = return_filters(filters)

	purchase_orders = frappe.get_all("Purchase Invoice", ["*"], filters = conditions, order_by = "name asc")

	for purchase_order in purchase_orders:
		row = [purchase_order.posting_date, purchase_order.supplier, "Purchase Invoice", purchase_order.name, purchase_order.grand_total, purchase_order.total_advance, purchase_order.outstanding_amount, purchase_order.curency]
		data.append(row)
	
	supplier_documents = frappe.get_all("Supplier Documents", ["*"], filters = conditions, order_by = "name asc")

	for supplier_document in supplier_documents:
		total_advance = supplier_document.total - supplier_document.outstanding_amount
		row = [supplier_document.posting_date, supplier_document.supplier, "Supplier Documents", supplier_document.name, supplier_document.total, total_advance, supplier_document.outstanding_amount, supplier_document.curency]
		data.append(row)
	
	supplier_retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions, order_by = "name asc")

	for supplier_retention in supplier_retentions:
		row = [supplier_retention.posting_date, supplier_retention.supplier, "Supplier Retention", supplier_retention.name, supplier_retention.total_references, 0, 0, supplier_retention.curency]
		data.append(row)
	
	condition_payment_entry = return_filters_payment_entry(filters)

	payment_entries = frappe.get_all("Payment Entry", ["*"], filters = condition_payment_entry, order_by = "name asc")

	for payment_entry in payment_entries:
		row = [payment_entry.posting_date, payment_entry.party, "Payment Entry", payment_entry.name, payment_entry.total_allocated_amount, payment_entry.paid_amount, payment_entry.unallocated_amount, payment_entry.curency]
		data.append(row)

	return data

def return_filters(filters):
	conditions = ''	

	conditions += "{"
	conditions += '"supplier": "{}"'.format(filters.get("supplier"))
	conditions += '}'

	return conditions

def return_filters_payment_entry(filters):
	conditions = ''	

	conditions += "{"
	conditions += '"party_type": "Supplier"'
	conditions += ', "party": "{}"'.format(filters.get("supplier"))
	conditions += '}'

	return conditions