# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

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

		outstanding_voucher_list = self.outstanding_voucher_list(amount_query, party_name)

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
				}), (party_name, d.voucher_type, d.voucher_no))
				
			payment_amount = -1*payment_amount[0][0] if payment_amount else 0
				
			if d.invoice_amount > payment_amount:
				
				outstanding_vouchers.append({
					'voucher_no': d.voucher_no, 
					'voucher_type': d.voucher_type, 
					'posting_date': d.posting_date, 
					'invoice_amount': flt(d.invoice_amount), 
					'outstanding_amount': d.invoice_amount - payment_amount})
								
				outstanding_vouchers.append(order_list)			

		else:
			pass

	def outstanding_vouchers_list(self, amount_query, party_name):
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
			}), self.account_head, as_dict = True)

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
		pass

	def filter_vouchers(self):
		pass

	def make_journal_voucher(self):
		pass

	def check_mandatory_to_fetch(self):

		party_field_value_check = "customer" if self.party_type == "Customer" else "supplier"

		for fieldname in ["party_type", party_field_value_check, "received_or_paid"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} field first").format(self.meta.get_label(fieldname)))