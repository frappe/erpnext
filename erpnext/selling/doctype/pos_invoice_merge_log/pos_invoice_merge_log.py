# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, add_months, today, date_diff, getdate, add_days, cstr, nowdate
from frappe.model.document import Document
from frappe.model.mapper import map_doc
from frappe.model import default_fields

from six import iteritems

class POSInvoiceMergeLog(Document):
	def validate(self):
		self.validate_customer()
		self.validate_pos_invoice_status()

	def validate_customer(self):
		for d in self.pos_invoices:
			if d.customer != self.customer:
				frappe.throw(_("Row #{}: POS Invoice {} is not against customer {}").format(d.idx, d.pos_invoice, self.customer))

	def validate_pos_invoice_status(self):
		for d in self.pos_invoices:
			status, docstatus = frappe.db.get_value('POS Invoice', d.pos_invoice, ['status', 'docstatus'])
			if docstatus != 1:
				frappe.throw(_("Row #{}: POS Invoice {} is not submitted yet").format(d.idx, d.pos_invoice))
			if status in ['Consolidated']:
				frappe.throw(_("Row #{}: POS Invoice {} has been {}").format(d.idx, d.pos_invoice, status))

	def on_submit(self):
		pos_invoice_docs = [frappe.get_doc("POS Invoice", d.pos_invoice) for d in self.pos_invoices]

		returns = [d for d in pos_invoice_docs if d.get('is_return') == 1]
		sales = [d for d in pos_invoice_docs if d.get('is_return') == 0]

		sales_invoice = self.process_merging_into_sales_invoice(sales)
		
		if len(returns):
			credit_note = self.process_merging_into_credit_note(returns)
		else:
			credit_note = ""

		self.save() # save consolidated_sales_invoice & consolidated_credit_note ref in merge log

		self.update_pos_invoices(sales_invoice, credit_note)

	def process_merging_into_sales_invoice(self, data):
		sales_invoice = self.get_new_sales_invoice()
		
		sales_invoice = self.merge_pos_invoice_into(sales_invoice, data)

		sales_invoice.is_consolidated = 1
		sales_invoice.save()
		sales_invoice.submit()
		self.consolidated_invoice = sales_invoice.name

		return sales_invoice.name

	def process_merging_into_credit_note(self, data):
		credit_note = self.get_new_sales_invoice()
		credit_note.is_return = 1

		credit_note = self.merge_pos_invoice_into(credit_note, data)

		credit_note.is_consolidated = 1
		# TODO: return could be against multiple sales invoice which could also have been consolidated?
		credit_note.return_against = self.consolidated_invoice
		credit_note.save()
		credit_note.submit()
		self.consolidated_credit_note = credit_note.name

		return credit_note.name
	
	def merge_pos_invoice_into(self, invoice, data):
		items, payments, taxes = [], [], []
		loyalty_amount_sum, loyalty_points_sum = 0, 0
		for doc in data:
			map_doc(doc, invoice, table_map={ "doctype": invoice.doctype })
			
			if doc.redeem_loyalty_points:
				invoice.loyalty_redemption_account = doc.loyalty_redemption_account
				invoice.loyalty_redemption_cost_center = doc.loyalty_redemption_cost_center
				loyalty_points_sum += doc.loyalty_points
				loyalty_amount_sum += doc.loyalty_amount
			
			for item in doc.get('items'):
				items.append(item)
			
			for tax in doc.get('taxes'):
				found = False
				for t in taxes:
					if t.account_head == tax.account_head and t.cost_center == tax.cost_center and t.rate == tax.rate:
						t.tax_amount = flt(t.tax_amount) + flt(tax.tax_amount)
						t.base_tax_amount = flt(t.base_tax_amount) + flt(tax.base_tax_amount)
						found = True
				if not found:
					tax.charge_type = 'Actual'
					taxes.append(tax)

			for payment in doc.get('payments'):
				found = False
				for pay in payments:
					if pay.account == payment.account and pay.mode_of_payment == payment.mode_of_payment:
						pay.amount = flt(pay.amount) + flt(payment.amount)
						pay.base_amount = flt(pay.base_amount) + flt(payment.base_amount)
						found = True
				if not found:
					payments.append(payment)

		if loyalty_points_sum:
			invoice.redeem_loyalty_points = 1
			invoice.loyalty_points = loyalty_points_sum
			invoice.loyalty_amount = loyalty_amount_sum

		invoice.set('items', items)
		invoice.set('payments', payments)
		invoice.set('taxes', taxes)

		return invoice
	
	def get_new_sales_invoice(self):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = self.customer
		sales_invoice.is_pos = 1
		# date can be pos closing date?
		sales_invoice.posting_date = getdate(nowdate())

		return sales_invoice
	
	def update_pos_invoices(self, sales_invoice, credit_note):
		for d in self.pos_invoices:
			doc = frappe.get_doc('POS Invoice', d.pos_invoice)
			if not doc.is_return:
				doc.update({'consolidated_invoice': sales_invoice})
			else:
				doc.update({'consolidated_invoice': credit_note})
			doc.set_status(update=True)
			doc.save()

def get_all_invoices():
	filters = {
		'consolidated_invoice': [ 'in', [ '', None ]],
		'status': ['not in', ['Consolidated']],
		'docstatus': 1
	}
	pos_invoices = frappe.db.get_all('POS Invoice', filters=filters,
		fields=["name as pos_invoice", 'posting_date', 'grand_total', 'customer'])
	
	return pos_invoices

def get_invoices_customer_map(pos_invoices):
	# pos_invoice_customer_map = { 'Customer 1': [{}, {}, {}], 'Custoemr 2' : [{}] }
	pos_invoice_customer_map = {}
	for invoice in pos_invoices:
		customer = invoice.get('customer')
		pos_invoice_customer_map.setdefault(customer, [])
		pos_invoice_customer_map[customer].append(invoice)
	
	return pos_invoice_customer_map

def merge_pos_invoices(pos_invoices=[]):
	if not pos_invoices:
		pos_invoices = get_all_invoices()
	
	pos_invoice_map = get_invoices_customer_map(pos_invoices)
	create_merge_logs(pos_invoice_map)

def create_merge_logs(pos_invoice_customer_map):
	for customer, invoices in iteritems(pos_invoice_customer_map):
		merge_log = frappe.new_doc('POS Invoice Merge Log')
		merge_log.posting_date = getdate(nowdate())
		merge_log.customer = customer

		merge_log.set('pos_invoices', invoices)
		merge_log.save(ignore_permissions=True)
		merge_log.submit()

