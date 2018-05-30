# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from collections import defaultdict
from erpnext.controllers.taxes_and_totals import get_itemised_tax_breakup_data
import json


class POSClosingVoucher(Document):
	pass

@frappe.whitelist()
def get_closing_voucher_details(**kwargs):
	data = {}
	invoice_list = get_invoices(kwargs)
	data['invoices'] = invoice_list
	data['sales_summary'] = get_sales_summary(invoice_list)
	data['mop'] = get_mode_of_payment_details(invoice_list)
	data['taxes'] = get_tax_details(invoice_list)

	return data

@frappe.whitelist()
def get_payment_reconciliation_details(doc):
	doc = json.loads(doc)
	currency = get_company_currency(doc)
	return frappe.render_template("erpnext/selling/doctype/pos_closing_voucher/closing_voucher_details.html", {"data": doc, "currency": currency})

def get_mode_of_payment_details(invoice_list):
	mode_of_payment_details = []
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

		inv_change_amount = frappe.db.sql("""select a.owner, a.posting_date,
			ifnull(b.mode_of_payment, '') as mode_of_payment, sum(a.base_change_amount) as change_amount
			from `tabSales Invoice` a, `tabSales Invoice Payment` b
			where a.name = b.parent
			and a.name in ({invoice_list_names})
			and b.mode_of_payment = 'Cash'
			and a.base_change_amount > 0
			group by a.owner, a.posting_date, mode_of_payment""".format(invoice_list_names=invoice_list_names), as_dict=1)

		for d in inv_change_amount:
			for det in inv_mop_detail:
				if det["owner"] == d["owner"] and det["posting_date"] == d["posting_date"] and det["mode_of_payment"] == d["mode_of_payment"]:
					paid_amount = det["paid_amount"] - d["change_amount"]
					det["paid_amount"] = paid_amount

		payment_details = defaultdict(int)
		for d in inv_mop_detail:
			payment_details[d.mode_of_payment] += d.paid_amount

		for m in payment_details:
			mode_of_payment_details.append({'name': m, 'amount': payment_details[m]})

	return mode_of_payment_details

def get_tax_details(invoice_list):
	tax_breakup = []
	tax_details = defaultdict(int)
	for invoice in invoice_list:
		doc = frappe.get_doc("Sales Invoice", invoice.name)
		itemised_tax, itemised_taxable_amount = get_itemised_tax_breakup_data(doc)

		if itemised_tax:
			for a in itemised_tax:
				for b in itemised_tax[a]:
					for c in itemised_tax[a][b]:
						if c == 'tax_rate':
							tax_details[itemised_tax[a][b][c]] += itemised_tax[a][b]['tax_amount']

	for t in tax_details:
		tax_breakup.append({'rate': t, 'amount': tax_details[t]})

	return tax_breakup


def get_sales_summary(invoice_list):
	net_total = sum(item['net_total'] for item in invoice_list)
	grand_total = sum(item['grand_total'] for item in invoice_list)
	total_qty = sum(item['pos_total_qty'] for item in invoice_list)

	return {'net_total': net_total, 'grand_total': grand_total, 'total_qty': total_qty}

def get_company_currency(doc):
	currency = frappe.db.get_value("Company", doc['company'], "default_currency")
	return frappe.get_doc('Currency', currency)


def get_invoices(filters):
	return frappe.db.sql("""select a.name, a.base_grand_total as grand_total,
		a.base_net_total as net_total, a.pos_total_qty
		from `tabSales Invoice` a
		where a.docstatus = 1 and a.posting_date >= %(from_date)s
		and a.posting_date <= %(to_date)s and a.company=%(company)s
		and a.pos_profile = %(pos_profile)s and a.is_pos = %(is_pos)s""",
		filters, as_dict=1)
