# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt
from frappe import _
import datetime

def execute(filters=None):
	if not filters: filters = {}
	columns = [
		{
			"label": _("Date"),
			"fieldname": "date",
			"fieldtype": "Date",
			"width": 240
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 240
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": 240
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 240
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"width": 240
		},
		{
			"label": _("Mode Of Payment"),
			"fieldname": "mode_of_payment",
			"width": 240
		},
		{
			"label": _("Invoice Amount"),
			"fieldname": "invoice_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Amount paid"),
			"fieldname": "amount_paid",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Outstanding Amount"),
			"fieldname": "outstanding_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Currency"),
			"fieldname": "currency",
			"width": 240
		},
	]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	from_date, to_date = None, None
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	data = []
	conditions = return_filters(filters, from_date, to_date)

	purchase_orders = frappe.get_all("Purchase Invoice", ["*"], filters = conditions, order_by = "name asc")

	for purchase_order in purchase_orders:
		row = [purchase_order.posting_date, purchase_order.supplier, "Purchase Invoice", purchase_order.name, purchase_order.company, "", purchase_order.grand_total, purchase_order.total_advance, purchase_order.outstanding_amount, purchase_order.currency]
		data.append(row)
	
	supplier_documents = frappe.get_all("Supplier Documents", ["*"], filters = conditions, order_by = "name asc")

	for supplier_document in supplier_documents:
		total_advance = supplier_document.total - supplier_document.outstanding_amount
		row = [supplier_document.posting_date, supplier_document.supplier, "Supplier Documents", supplier_document.name, supplier_document.company, "", supplier_document.total, total_advance, supplier_document.outstanding_amount, supplier_document.currency]
		data.append(row)
	
	supplier_retentions = frappe.get_all("Supplier Retention", ["*"], filters = conditions, order_by = "name asc")

	for supplier_retention in supplier_retentions:
		row = [supplier_retention.posting_date, supplier_retention.supplier, "Supplier Retention", supplier_retention.name, supplier_retention.company, "", 0, supplier_retention.total_withheld, 0, supplier_retention.currency]
		data.append(row)
	
	condition_payment_entry = return_filters_payment_entry(filters, from_date, to_date)

	payment_entries = frappe.get_all("Payment Entry", ["*"], filters = condition_payment_entry, order_by = "name asc")

	for payment_entry in payment_entries:
		row = [payment_entry.posting_date, payment_entry.party, "Payment Entry", payment_entry.name, payment_entry.company, payment_entry.mode_of_payment, 0, payment_entry.paid_amount, payment_entry.unallocated_amount, payment_entry.paid_to_account_currency]
		data.append(row)
	
	condition_credit_note = return_filters(filters, from_date, to_date)

	credits = frappe.get_all("Credit Note CXP", ["*"], filters = condition_credit_note, order_by = "name asc")

	for credit in credits:
		total_advance = credit.total - credit.outstanding_amount
		row = [credit.posting_date, credit.supplier, "Credit Note CXP", credit.name, credit.company, "", credit.total, total_advance, credit.outstanding_amount, credit.currency]
		data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	date = False
	if from_date != None and to_date !=None:
		date = True

	conditions = ''	

	conditions += "{"
	conditions += '"supplier": "{}"'.format(filters.get("supplier"))
	if date: conditions += ',"posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))	
	conditions += '}'

	return conditions

def return_filters_payment_entry(filters, from_date, to_date):
	date = False
	if from_date != None and to_date !=None:
		date = True

	conditions = ''	

	conditions += "{"
	conditions += '"party_type": "Supplier"'
	conditions += ', "party": "{}"'.format(filters.get("supplier"))
	if date: conditions += ', "posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	if filters.get("company"): conditions += ', "company": "{}"'.format(filters.get("company"))
	conditions += '}'

	return conditions