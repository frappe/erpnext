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
	def get_closing_voucher_details(self):
		filters = {
			'doc': self.name,
			'from_date': self.period_start_date,
			'to_date': self.period_end_date,
			'company': self.company,
			'pos_profile': self.pos_profile,
			'user': self.user,
			'is_pos': 1
		}

		invoice_list = get_invoices(filters)
		self.set_invoice_list(invoice_list)

		sales_summary = get_sales_summary(invoice_list)
		self.set_sales_summary_values(sales_summary)

		if not self.get('payment_reconciliation'):
			mop = get_mode_of_payment_details(invoice_list)
			self.set_mode_of_payments(mop)

		taxes = get_tax_details(invoice_list)
		self.set_taxes(taxes)

		return self.get_payment_reconciliation_details()

	def set_invoice_list(self, invoice_list):
		self.sales_invoices_summary = []
		for invoice in invoice_list:
			self.append('sales_invoices_summary', {
				'invoice': invoice['name'],
				'qty_of_items': invoice['pos_total_qty'],
				'grand_total': invoice['grand_total']
			})

	def set_sales_summary_values(self, sales_summary):
		self.grand_total = sales_summary['grand_total']
		self.net_total = sales_summary['net_total']
		self.total_quantity = sales_summary['total_qty']

	def set_mode_of_payments(self, mop):
		self.payment_reconciliation = []
		for m in mop:
			self.append('payment_reconciliation', {
				'mode_of_payment': m['name'],
				'expected_amount': m['amount']
			})

	def set_taxes(self, taxes):
		self.taxes = []
		for tax in taxes:
			self.append('taxes', {
				'rate': tax['rate'],
				'amount': tax['amount']
			})

	def get_payment_reconciliation_details(self):
		currency = get_company_currency(self)
		return frappe.render_template("erpnext/selling/doctype/pos_closing_voucher/closing_voucher_details.html",
			{"data": self, "currency": currency})

@frappe.whitelist()
def get_cashiers(doctype, txt, searchfield, start, page_len, filters):
	cashiers_list = frappe.get_all("POS Profile User", filters=filters, fields=['user'])
	cashiers = [cashier for cashier in set(c['user'] for c in cashiers_list)]
	return [[c] for c in cashiers]

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
	currency = frappe.get_cached_value('Company',  doc.company,  "default_currency")
	return frappe.get_doc('Currency', currency)

def get_invoices(filters):
	return frappe.db.sql("""select a.name, a.base_grand_total as grand_total,
		a.base_net_total as net_total, a.pos_total_qty
		from `tabSales Invoice` a
		where a.docstatus = 1 and a.posting_date >= %(from_date)s
		and a.posting_date <= %(to_date)s and a.company=%(company)s
		and a.pos_profile = %(pos_profile)s and a.is_pos = %(is_pos)s
		and a.owner = %(user)s""",
		filters, as_dict=1)
