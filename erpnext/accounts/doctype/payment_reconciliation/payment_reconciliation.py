# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

class PaymentReconciliation(Document):
	def get_unreconciled_entries(self):
		self.set('payment_reconciliation_payment', [])
		jve = self.get_jv_entries()
		self.add_payment_entries(jve)

	def get_jv_entries(self):
		self.validation()

		dr_or_cr = "credit" if self.party_type == "Customer" else "debit" 
		
		#Add conditions for debit/credit, sorting by date and amount
		cond = self.from_date and " and t1.posting_date >= '" + self.from_date + "'" or ""
		cond += self.to_date and " and t1.posting_date <= '" + self.to_date + "'" or ""

		if self.minimum_amount:
			cond += (" and ifnull(t2.%s), 0) >= %s") % (dr_or_cr, self.minimum_amount) 
		if self.maximum_amount:
			cond += " and ifnull(t2.%s, 0) <= %s" % (dr_or_cr, self.maximum_amount)

		jve = frappe.db.sql("""
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

		return jve

	def add_payment_entries(self, jve):
		self.set('payment_reconciliation_payments', [])
		for e in jve:
			ent = self.append('payment_reconciliation_payments', {})
			ent.journal_voucher = e.get('voucher_no')
			ent.posting_date = e.get('posting_date')
			ent.amount = flt(e.get('credit' or 'debit'))
			ent.remark = e.get('remark')

	def validation(self):
		self.check_mandatory()

	def check_mandatory(self):
		pass
