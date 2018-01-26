# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr

def execute(filters=None):
	columns, data = [], []
	columns=get_columns()
	data=get_sales_payment_data(filters, columns)
	return columns, data

def get_columns():
	return [
		_("Date") + ":Date:80",
		_("Owner") + ":Data:200",
		_("Payment Mode") + ":Data:240",
		_("Sales and Returns") + ":Currency/currency:120",
		_("Taxes") + ":Currency/currency:120",
		_("Payments") + ":Currency/currency:120"
	]

def get_sales_payment_data(filters, columns):
	data = []
	show_payment_detail = False

	sales_invoice_data = get_sales_invoice_data(filters)
	mode_of_payments = get_mode_of_payments(filters)
	mode_of_payment_details = get_mode_of_payment_details(filters)

	if filters.get("payment_detail"):
		show_payment_detail = True
	else:
		show_payment_detail = False

	for inv in sales_invoice_data:
		owner_posting_date = inv["owner"]+cstr(inv["posting_date"])
		if show_payment_detail:
			row = [inv.posting_date, inv.owner," ",inv.net_total,inv.total_taxes, 0]
			data.append(row)
			for mop_detail in mode_of_payment_details.get(owner_posting_date,[]):
				row = [inv.posting_date, inv.owner,mop_detail[0],0,0,mop_detail[1],0]
				data.append(row)
		else:
			total_payment = 0
			for mop_detail in mode_of_payment_details.get(owner_posting_date,[]):
				total_payment = total_payment + mop_detail[1]
			row = [inv.posting_date, inv.owner,", ".join(mode_of_payments.get(owner_posting_date, [])),
			inv.net_total,inv.total_taxes,total_payment]
			data.append(row)
	return data

def get_conditions(filters):
	conditions = "1=1"
	if filters.get("from_date"): conditions += " and a.posting_date >= %(from_date)s"
	if filters.get("to_date"): conditions += " and a.posting_date <= %(to_date)s"
	if filters.get("company"): conditions += " and a.company=%(company)s"
	if filters.get("customer"): conditions += " and a.customer = %(customer)s"
	if filters.get("owner"): conditions += " and a.owner = %(owner)s"
	if filters.get("is_pos"): conditions += " and a.is_pos = %(is_pos)s"
	return conditions

def get_sales_invoice_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		select
			a.posting_date, a.owner,
			sum(a.net_total) as "net_total",
			sum(a.total_taxes_and_charges) as "total_taxes",
			sum(a.base_paid_amount) as "paid_amount",
			sum(a.outstanding_amount) as "outstanding_amount"
		from `tabSales Invoice` a
		where a.docstatus = 1
			and {conditions}
			group by
			a.owner, a.posting_date
	""".format(conditions=conditions), filters, as_dict=1)

def get_mode_of_payments(filters):
	mode_of_payments = {}
	invoice_list = get_invoices(filters)
	invoice_list_names = ",".join(['"' + invoice['name'] + '"' for invoice in invoice_list])
	if invoice_list:
		inv_mop = frappe.db.sql("""select a.owner,a.posting_date, ifnull(b.mode_of_payment, '') as mode_of_payment
			from `tabSales Invoice` a, `tabSales Invoice Payment` b
			where a.name = b.parent
			and a.name in ({invoice_list_names})
			union
			select a.owner,a.posting_date, ifnull(b.mode_of_payment, '') as mode_of_payment
			from `tabSales Invoice` a, `tabPayment Entry` b,`tabPayment Entry Reference` c
			where a.name = c.reference_name
			and b.name = c.parent
			and a.name in ({invoice_list_names})
			union
			select a.owner, a.posting_date,
			ifnull(a.voucher_type,'') as mode_of_payment
			from `tabJournal Entry` a, `tabJournal Entry Account` b
			where a.name = b.parent
			and a.docstatus = 1
			and b.reference_type = "Sales Invoice"
			and b.reference_name in ({invoice_list_names})
			""".format(invoice_list_names=invoice_list_names), as_dict=1)
		for d in inv_mop:
			mode_of_payments.setdefault(d["owner"]+cstr(d["posting_date"]), []).append(d.mode_of_payment)
	return mode_of_payments

def get_invoices(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""select a.name
		from `tabSales Invoice` a
		where a.docstatus = 1 and {conditions}""".format(conditions=conditions),
		filters, as_dict=1)

def get_mode_of_payment_details(filters):
	mode_of_payment_details = {}
	invoice_list = get_invoices(filters)
	invoice_list_names = ",".join(['"' + invoice['name'] + '"' for invoice in invoice_list])
	if invoice_list:
		inv_mop_detail = frappe.db.sql("""select a.owner, a.posting_date,
			ifnull(b.mode_of_payment, '') as mode_of_payment, sum(b.base_amount) as paid_amount
			from `tabSales Invoice` a, `tabSales Invoice Payment` b
			where a.name = b.parent
			and a.name in ({invoice_list_names})
			group by a.owner, a.posting_date, mode_of_payment
			union
			select a.owner,a.posting_date,
			ifnull(b.mode_of_payment, '') as mode_of_payment, sum(b.base_paid_amount) as paid_amount
			from `tabSales Invoice` a, `tabPayment Entry` b,`tabPayment Entry Reference` c
			where a.name = c.reference_name
			and b.name = c.parent
			and a.name in ({invoice_list_names})
			group by a.owner, a.posting_date, mode_of_payment
			union
			select a.owner, a.posting_date,
			ifnull(a.voucher_type,'') as mode_of_payment, sum(b.credit)
			from `tabJournal Entry` a, `tabJournal Entry Account` b
			where a.name = b.parent
			and a.docstatus = 1
			and b.reference_type = "Sales Invoice"
			and b.reference_name in ({invoice_list_names})
			group by a.owner, a.posting_date, mode_of_payment
			""".format(invoice_list_names=invoice_list_names), as_dict=1)
		for d in inv_mop_detail:
			mode_of_payment_details.setdefault(d["owner"]+cstr(d["posting_date"]), []).append((d.mode_of_payment,d.paid_amount))
	return mode_of_payment_details