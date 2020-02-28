# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cint, flt, add_months, today, date_diff, getdate, add_days, cstr, nowdate
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc

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
		pos_invoices_name = [d.pos_invoice for d in self.pos_invoices]
		pos_invoices_data = frappe.db.get_all('POS Invoice', 
			filters={ "name": ["in", pos_invoices_name]}, fields=[
				"name", "is_return", "redeem_loyalty_points", "loyalty_redemption_account", 
				"loyalty_redemption_cost_center", "loyalty_points", "loyalty_amount"
			])
		

		sales_invoice = self.process_merging_into_sales_invoice(pos_invoices_data)

		has_pos_credit_note = any([d.is_return == 1 for d in pos_invoices_data])
		if has_pos_credit_note:
			credit_note = self.process_merging_into_credit_note(pos_invoices_data)
		else:
			credit_note = ""

		self.save() # save consolidated_sales_invoice & consolidated_credit_note

		self.update_pos_invoices(sales_invoice, credit_note)

	def process_merging_into_sales_invoice(self, data):
		sales_invoice = self.get_new_sales_invoice()

		for doc in data:
			if not doc.is_return:
				loyalty_points_redeemed = 0
				loyalty_amount = 0
				if doc.redeem_loyalty_points:
					sales_invoice.redeem_loyalty_points = True
					sales_invoice.loyalty_redemption_account = doc.loyalty_redemption_account
					sales_invoice.loyalty_redemption_cost_center = doc.loyalty_redemption_cost_center
					loyalty_points_redeemed += doc.loyalty_points
					loyalty_amount += doc.loyalty_amount

				sales_invoice = get_mapped_doc("POS Invoice", doc.name, {
					"POS Invoice": {
						"doctype": "Sales Invoice",
						"validation": {
							"docstatus": ["=", 1]
						}
					},
					"POS Invoice Item": {
						"doctype": "Sales Invoice Item",
					}
				}, sales_invoice)
		if sales_invoice.redeem_loyalty_points:
			sales_invoice.loyalty_points = loyalty_points_redeemed
			sales_invoice.loyalty_amount = loyalty_amount

		sales_invoice.save()
		sales_invoice.submit()
		self.consolidated_invoice = sales_invoice.name

		return sales_invoice.name

	def process_merging_into_credit_note(self, data):
		credit_note = self.get_new_sales_invoice()
		credit_note.is_return = 1

		for doc in data:
			if doc.is_return:
				loyalty_points_redeemed = 0
				loyalty_amount = 0
				if doc.redeem_loyalty_points:
					credit_note.redeem_loyalty_points = True
					credit_note.loyalty_redemption_account = doc.loyalty_redemption_account
					credit_note.loyalty_redemption_cost_center = doc.loyalty_redemption_cost_center
					loyalty_points_redeemed += doc.loyalty_points
					loyalty_amount += doc.loyalty_amount

				credit_note = get_mapped_doc("POS Invoice", doc.name, {
					"POS Invoice": {
						"doctype": "Sales Invoice",
						"validation": {
							"docstatus": ["=", 1]
						}
					},
					"POS Invoice Item": {
						"doctype": "Sales Invoice Item",
					}
				}, credit_note)
		if credit_note.redeem_loyalty_points:
			credit_note.loyalty_points = loyalty_points_redeemed
			credit_note.loyalty_amount = loyalty_amount

		credit_note.return_against = self.consolidated_invoice
		credit_note.save()
		credit_note.submit()
		self.consolidated_credit_note = credit_note.name

		return credit_note.name
	
	def get_new_sales_invoice(self):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = self.customer
		sales_invoice.is_pos = 1
		sales_invoice.is_consolidated = 1
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
		fields=["'name' as pos_invoice", 'posting_date', 'grand_total', 'customer'])
	
	# pos_invoice_customer_map = { 'Customer 1': [{}, {}, {}], 'Custoemr 2' : [{}] }
	pos_invoice_customer_map = {}
	for invoice in self.pos_invoices:
		customer = invoice.get('customer')
		pos_invoice_customer_map.setdefault(customer, [])
		pos_invoice_customer_map[customer].append(invoice)
	
	return pos_invoice_customer_map

def auto_merge_pos_invoices():
	pos_invoice_map = get_all_invoices()
	create_merge_logs(pos_invoice_map)

def create_merge_logs(pos_invoice_customer_map):
	for customer, invoices in iteritems(pos_invoice_customer_map):
		merge_log = frappe.new_doc('POS Invoice Merge Log')
		merge_log.posting_date = getdate(nowdate())
		merge_log.customer = customer

		refs = []
		for d in invoices:
			refs.append(d)

		merge_log.set('pos_invoices', refs)
		merge_log.save()
		merge_log.submit()

