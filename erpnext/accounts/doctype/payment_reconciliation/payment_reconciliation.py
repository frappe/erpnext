# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

class PaymentReconciliation(Document):
	def get_unreconciled_entries(self):
		jv_entries = self.get_jv_entries()
		self.add_payment_entries(jv_entries)
		invoice_entries = self.get_invoice_entries()
		
		self.add_invoice_entries(invoice_entries)

	def get_jv_entries(self):
		self.check_mandatory()

		dr_or_cr = "credit" if self.party_type == "Customer" else "debit" 

		cond = self.check_condition(dr_or_cr)

		jv_entries = frappe.db.sql("""
			select
				t1.name as voucher_no, t1.posting_date, t1.remark, t2.account, 
				t2.name as voucher_detail_no,  t2.%s, t2.is_advance
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t1.name = t2.parent and t1.docstatus = 1 and t2.account = %s 
				and t2.%s > 0 and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')='' 
				and ifnull(t2.against_jv, '')='' %s
			group by t1.name, t2.name """ % (dr_or_cr, '%s', dr_or_cr, cond), (self.party_account), 
			as_dict = True)
		return jv_entries

	def add_payment_entries(self, jv_entries):
		self.set('payment_reconciliation_payments', [])
		for e in jv_entries:
			ent = self.append('payment_reconciliation_payments', {})
			ent.journal_voucher = e.get('voucher_no')
			ent.posting_date = e.get('posting_date')
			ent.amount = flt(e.get('credit')) or flt(e.get('debit'))
			ent.remark = e.get('remark')
			ent.voucher_detail_number = e.get('voucher_detail_no')

	def get_invoice_entries(self):
		#Fetch JVs, Sales and Purchase Invoices for 'payment_reconciliation_invoices' to reconcile against
		non_reconciled_invoices = []
		self.check_mandatory()

		dr_or_cr = "debit" if self.party_type == "Customer" else "credit"

		cond = self.check_condition(dr_or_cr)

		invoice_list = frappe.db.sql("""
			select
				voucher_no, voucher_type, posting_date, ifnull(sum(ifnull(%s, 0)), 0) as amount
			from
				`tabGL Entry`
			where
				account = %s and ifnull(%s, 0) > 0 %s
			group by voucher_no, voucher_type""" % (dr_or_cr, "%s", 
				dr_or_cr, cond), (self.party_account), as_dict=True)

		for d in invoice_list:
			payment_amount = frappe.db.sql("""
				select
					ifnull(sum(ifnull(%s, 0)), 0)
				from
					`tabGL Entry`
				where
					account = %s and against_voucher_type = %s and ifnull(against_voucher, '') = %s""",
					(("credit" if self.party_type == "Customer" else "debit"), self.party_account, 
						d.voucher_type, d.voucher_no))  
			
			payment_amount = payment_amount[0][0] if payment_amount else 0

			if d.amount > payment_amount:
				non_reconciled_invoices.append({'voucher_no': d.voucher_no, 
					'voucher_type': d.voucher_type, 
					'posting_date': d.posting_date, 
					'amount': flt(d.amount), 
					'outstanding_amount': d.amount - payment_amount})

			return non_reconciled_invoices


	def add_invoice_entries(self, non_reconciled_invoices):
		#Populate 'payment_reconciliation_invoices' with JVs and Invoices to reconcile against
		self.set('payment_reconciliation_invoices', [])
		if not non_reconciled_invoices:
			return
		for e in non_reconciled_invoices:
			ent = self.append('payment_reconciliation_invoices', {})
			ent.invoice_type = e.get('voucher_type')
			ent.invoice_number = e.get('voucher_no')
			ent.invoice_date = e.get('posting_date')
			ent.amount = flt(e.get('amount'))
			ent.outstanding_amount = e.get('outstanding_amount')

	def check_mandatory(self):
		pass

	def check_condition(self, dr_or_cr):
		cond = self.from_date and " and posting_date >= '" + self.from_date + "'" or ""
		cond += self.to_date and " and posting_date <= '" + self.to_date + "'" or ""

		if self.minimum_amount:
			cond += (" and ifnull(%s), 0) >= %s") % (dr_or_cr, self.minimum_amount) 
		if self.maximum_amount:
			cond += " and ifnull(%s, 0) <= %s" % (dr_or_cr, self.maximum_amount)

		return cond