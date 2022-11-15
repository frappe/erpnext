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
			"fieldname": "date",
			"label": _("Date"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "document_serie",
			"label": _("Document Serie"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 120
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Reference Doctype"),
			"fieldname": "reference_doctype",
			"width": 240
		},
		{
			"label": _("Reference Name"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 240
		},
		{
			"fieldname": "invoce_date",
			"label": _("Invoice Date"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"width": 240
		},		
		{
			"label": _("Party RTN"),
			"fieldname": "party_rtn",
			"width": 240
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"width": 240
		},
		{
			"label": _("Reason Payment"),
			"fieldname": "reason_payment",
			"width": 240
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Total Allocated Amount"),
			"fieldname": "total_allocated_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Unallocated Amount"),
			"fieldname": "unallocated_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Difference Amount (Company Currency)"),
			"fieldname": "difference_amount",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Cheque/Reference No"),
			"fieldname": "cheque_reference_no",
			"width": 240
		},
		{
			"label": _("Cheque/Reference Date"),
			"fieldname": "cheque_reference_date",
			"width": 240
		},
		{
			"label": _("Created By"),
			"fieldname": "created_by",
			"width": 240
		}
	]
	data = return_data(filters)
	return columns, data

def return_data(filters):
	data = []
	if filters.get("from_date"): from_date = filters.get("from_date")
	if filters.get("to_date"): to_date = filters.get("to_date")
	conditions = return_filters(filters, from_date, to_date)

	registers = frappe.get_all("Payment Entry", ["*"], filters = conditions,  order_by = "name asc")

	for register in registers:
		references = frappe.get_all("Payment Entry Reference", ["*"], filters = {"parent": register.name})
		for refenrence in references:
			invoice_date = ""

			if refenrence.reference_doctype == "Sales Invoice":
				invoice = frappe.get_doc(refenrence.reference_doctype, refenrence.reference_name)
				invoice_date = invoice.posting_date

			row = [register.posting_date, register.name, register.status, refenrence.reference_doctype, refenrence.reference_name, invoice_date, register.party_name, register.party_rtn, register.company, register.reason_payment, register.paid_amount, register.total_allocated_amount, register.unallocated_amount, register.difference_amount, register.reference_no, register.reference_date, register.user]
			data.append(row)

			apply_extra_registers = frappe.get_all("Apply Payment Entries Without References", filters = {"payment_entry": register.name})

			for apply in apply_extra_registers:
				references_apply = frappe.get_all("Apply Payment Entries Without References Detail", ["*"], filters = {"parent": apply.name})
				for reference_apply in references_apply:
					invoice_date_apply = ""

					invoice = frappe.get_doc("Sales Invoice", reference_apply.reference_name)
					invoice_date_apply = invoice.posting_date
					row = [register.posting_date, register.name, register.status,"Sales Invoice", reference_apply.reference_name, invoice_date_apply, register.party_name, register.party_rtn, register.company, register.reason_payment, register.paid_amount, register.total_allocated_amount, register.unallocated_amount, register.difference_amount, register.reference_no, register.reference_date, register.user]
					data.append(row)

	return data

def return_filters(filters, from_date, to_date):
	conditions = ''	

	conditions += "{"
	conditions += '"party_type": "Customer"'
	conditions += ', "posting_date": ["between", ["{}", "{}"]]'.format(from_date, to_date)
	conditions += ', "company": "{}"'.format(filters.get("company"))
	if filters.get("customer"): conditions += ', "party_name": "{}"'.format(filters.get("customer"))
	if filters.get("reason_payment"): conditions += ', "reason_payment": "{}"'.format(filters.get("reason_payment"))
	if filters.get("mode_of_payment"): conditions += ', "mode_of_payment": "{}"'.format(filters.get("mode_of_payment"))
	conditions += '}'

	return conditions