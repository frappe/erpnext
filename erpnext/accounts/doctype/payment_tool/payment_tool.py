# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt, cint

from frappe import msgprint, _

from frappe.model.document import Document

from frappe.model.mapper import get_mapped_doc

class PaymentTool(Document):
	def get_outstanding_vouchers(self):
		self.check_mandatory_to_fetch()

		if self.party_type == "Customer" and self.received_or_paid == "Received":
			amount_query = "ifnull(debit, 0) - ifnull(credit, 0)"
			order_list = self.sales_order_list(self.customer)
		
		elif self.party_type == "Supplier" and self.received_or_paid == "Paid":
			amount_query = "ifnull(credit, 0) - ifnull(debit, 0)"
			order_list = self.purchase_order_list(self.supplier)
		else:
			frappe.throw(_("Please enter the Against Invoice details manually to create JV"))

		account_name = self.get_account_name(self.customer if self.customer else self.supplier)
		all_outstanding_vouchers = self.outstanding_voucher_list(amount_query, account_name)

		if len(order_list):		
			all_outstanding_vouchers.extend(order_list)

		self.add_outstanding_vouchers(all_outstanding_vouchers)
		self.account_name = account_name

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
					'outstanding_amount': d.invoice_amount - payment_amount
					})

		return all_outstanding_vouchers

	def sales_order_list(self, party_name):
		sales_order_list = []

		order_list = frappe.db.sql("""
			select
				name as voucher_no, ifnull(grand_total, 0) as invoice_amount,
				ifnull(advance_paid, 0), transaction_date as posting_date
			from
				`tabSales Order`
			where
				customer = %s 
				and docstatus = 1
				and ifnull(grand_total, 0) > ifnull(advance_paid, 0)
			group by voucher_no			 
			""", party_name, as_dict = True)

		for d in order_list:
			sales_order_list.append({
				'voucher_no': d.voucher_no, 
				'voucher_type': "Sales Order", 
				'posting_date': d.posting_date, 
				'invoice_amount': flt(d.invoice_amount), 
				'outstanding_amount': flt(d.invoice_amount) - flt(d.advance_paid)
				})

		return sales_order_list

	def purchase_order_list(self, party_name):
		purchase_order_list = []

		order_list = frappe.db.sql("""
			select
				name as voucher_no, ifnull(grand_total, 0) as invoice_amount,
				ifnull(advance_paid, 0), transaction_date as posting_date
			from
				`tabPurchase Order`
			where
				supplier = %s 
				and docstatus = 1
				and ifnull(grand_total, 0) > ifnull(advance_paid, 0)
			group by voucher_no			 
			""", party_name, as_dict = True)

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
		self.set('payment_tool_voucher_details', [])

		for e in all_outstanding_vouchers:
			ent = self.append('payment_tool_voucher_details', {})
			ent.against_voucher_type = e.get('voucher_type')
			ent.against_voucher_no = e.get('voucher_no')
			ent.total_amount = e.get('invoice_amount')
			ent.outstanding_amount = e.get('outstanding_amount')

	def get_account_name(self, party_name):
		account_name = frappe.db.get_value("Account", {"account_name": party_name, 
			"master_type": self.party_type}, fieldname = "name")
		return account_name

	def check_mandatory_to_fetch(self):

		party_field_value_check = "customer" if self.party_type == "Customer" else "supplier"

		for fieldname in ["party_type", party_field_value_check, "received_or_paid"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} field first").format(self.meta.get_label(fieldname)))


	def make_journal_voucher(self):

		total_payment_amount = 0.00
		invoice_voucher_type = {'Sales Invoice': 'against_invoice', 
								'Purchase Invoice': 'against_voucher',
								'Journal Voucher': 'against_jv',
								'Sales Order': 'against_sales_order',
								'Purchase Order': 'against_purchase_order',
								}
		
		jv = frappe.new_doc('Journal Voucher')
		jv.voucher_type = 'Journal Entry'
		jv.company = self.company
		jv.cheque_no = self.reference_no
		jv.cheque_date = self.reference_date

		for v in self.get("payment_tool_voucher_details"):
			d1 = jv.append("entries")
			d1.account = self.account_name

			d1.set("debit" if self.received_or_paid=="Paid" else "credit", flt(v.payment_amount))
			d1.set(invoice_voucher_type.get(v.against_voucher_type), v.against_voucher_no)
			d1.set('is_advance', 'Yes' if v.against_voucher_type == 'Sales Order' or
				v.against_voucher_type == 'Purchase Order' else 'No')
			total_payment_amount = flt(total_payment_amount) + flt(d1.debit) - flt(d1.credit)

		d2 = jv.append("entries")
		d2.account = self.payment_account
		d2.set('debit' if total_payment_amount < 0 else 'credit', abs(total_payment_amount))

		return jv