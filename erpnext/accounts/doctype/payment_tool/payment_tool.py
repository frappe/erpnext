# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

from frappe.model.mapper import get_mapped_doc

class PaymentTool(Document):
	def get_outstanding_vouchers(self):
		self.check_mandatory_to_fetch()

		if recieved_or_paid == "Recieved":

			if self.party_type == "Customer":
				amount_query = "ifnull(debit, 0) - ifnull(credit, 0)"
				party_name = self.customer
				order_list = self.sales_order_list(amount_query, party_name)
			else:
				amount_query = "ifnull(credit, 0) - ifnull(debit, 0)"
				party_name = self.supplier
				order_list = self.purchase_order_list(amount_query, party_name)

			account_name = self.get_account_name(party_name)
			all_outstanding_vouchers = self.outstanding_voucher_list(amount_query, account_name)

			if len(order_list):		
				all_outstanding_vouchers.append(order_list)

		else:
			pass

		self.add_outstanding_vouchers(all_outstanding_vouchers)

	def outstanding_voucher_list(self, amount_query, account_name):
		all_outstanding_vouchers = []

		outstanding_voucher_list = frappe.db.sql("""
			select
				voucher_no, voucher_type, posting_date, 
				ifnull(sum({amount_query}), 0) as invoice_amount
			from
				`tabGL Entry`
			where
				account = %s and {amount_query} > 0
			group by voucher_type, voucher_no			 
			""".format(**{
			"amount_query": amount_query
			}), account_name, as_dict = True)

		for d in outstanding_voucher_list:
			payment_amount = frappe.db.sql("""
				select ifnull(sum(ifnull({amount_query}, 0)), 0)
				from
					`tabGL Entry`
				where
					account = %s and {amount_query} < 0 
					and against_voucher_type = %s and ifnull(against_voucher, '') = %s
				""".format(**{
				"amount_query": amount_query
				}), (account_name, d.voucher_type, d.voucher_no))
				
			payment_amount = -1*payment_amount[0][0] if payment_amount else 0
				
			if d.invoice_amount > payment_amount:
				
				all_outstanding_vouchers.append({
					'voucher_no': d.voucher_no, 
					'voucher_type': d.voucher_type, 
					'posting_date': d.posting_date, 
					'invoice_amount': flt(d.invoice_amount), 
					'outstanding_amount': d.invoice_amount - payment_amount})

		return all_outstanding_vouchers

	def sales_order_list(self, amount_query, party_name):
		sales_order_list = frappe.db.sql("""
			select
				voucher_no, voucher_type, posting_date, 
				ifnull(sum({amount_query}), 0) as invoice_amount
			from
				`tabGL Entry`
			where
				customer = %s and advance_paid > grand_total
			group by voucher_type, voucher_no			 
			""".format(**{
			"amount_query": amount_query
			}), (party_type_name), as_dict = True)

	def purchase_order_list(self, amount_query, party_name):
		purchase_order_list = []

		order_list = frappe.db.sql("""
			select
				name as voucher_no, ifnull(grand_total, 0) as invoice_amount,
				ifnull(advance_paid, 0), transaction_date as posting_date
			from
				`tabPurchase Order`
			where
				customer = %(party_name)s 
				and ifnull(grand_total, 0) > ifnull(advance_paid, 0)
			group by voucher_no			 
			""".format(**{
			"amount_query": amount_query
			}), {
				"party_name": party_name
			}, as_dict = True)

		for d in order_list:
			purchase_order_list.append({
				'voucher_no': d.voucher_no, 
				'voucher_type': "Sales Order", 
				'posting_date': d.posting_date, 
				'invoice_amount': flt(d.invoice_amount), 
				'outstanding_amount': flt(d.invoice_amount) - flt(d.advance_paid)
				})

		return purchase_order_list

	def add_outstanding_vouchers(self, all_outstanding_vouchers):
		self.set('outstanding_vouchers', [])
		print all_outstanding_vouchers
		for e in all_outstanding_vouchers:
			ent = self.append('outstanding_vouchers', {})
			ent.against_voucher_type = e.get('voucher_type')
			ent.against_voucher_no = e.get('voucher_no')
			ent.total_amount = e.get('invoice_amount')
			ent.outstanding_amount = e.get('outstanding_amount')

	def filter_vouchers(self):
		pass

	def make_journal_voucher(self):
		print True

	def check_mandatory_to_fetch(self):

		party_field_value_check = "customer" if self.party_type == "Customer" else "supplier"

		for fieldname in ["party_type", party_field_value_check, "received_or_paid"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} field first").format(self.meta.get_label(fieldname)))