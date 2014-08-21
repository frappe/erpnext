# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

class PaymentReconciliation(Document):
	def get_unreconciled_entries(self):
		self.get_jv_entries()
		self.get_invoice_entries()

	def get_jv_entries(self):
		self.check_mandatory_to_fetch()
		dr_or_cr = "credit" if self.party_type == "Customer" else "debit"

		cond = self.check_condition(dr_or_cr)

		bank_account_condition = "t2.against_account like %(bank_cash_account)s" \
				if self.bank_cash_account else "1=1"

		jv_entries = frappe.db.sql("""
			select
				t1.name as voucher_no, t1.posting_date, t1.remark, t2.account,
				t2.name as voucher_detail_no, {dr_or_cr} as payment_amount, t2.is_advance
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
				and t2.account = %(party_account)s and {dr_or_cr} > 0
				and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')=''
				and ifnull(t2.against_jv, '')='' {cond}
				and (CASE
					WHEN t1.voucher_type in ('Debit Note', 'Credit Note')
					THEN 1=1
					ELSE {bank_account_condition}
				END)
			""".format(**{
				"dr_or_cr": dr_or_cr,
				"cond": cond,
				"bank_account_condition": bank_account_condition,
			}), {
				"party_account": self.party_account,
				"bank_cash_account": "%%%s%%" % self.bank_cash_account
			}, as_dict=1)

		self.add_payment_entries(jv_entries)

	def add_payment_entries(self, jv_entries):
		self.set('payment_reconciliation_payments', [])
		for e in jv_entries:
			ent = self.append('payment_reconciliation_payments', {})
			ent.journal_voucher = e.get('voucher_no')
			ent.posting_date = e.get('posting_date')
			ent.amount = flt(e.get('payment_amount'))
			ent.remark = e.get('remark')
			ent.voucher_detail_number = e.get('voucher_detail_no')
			ent.is_advance = e.get('is_advance')

	def get_invoice_entries(self):
		#Fetch JVs, Sales and Purchase Invoices for 'payment_reconciliation_invoices' to reconcile against
		non_reconciled_invoices = []
		dr_or_cr = "debit" if self.party_type == "Customer" else "credit"
		cond = self.check_condition(dr_or_cr)

		invoice_list = frappe.db.sql("""
			select
				voucher_no, voucher_type, posting_date,
				ifnull(sum({dr_or_cr}), 0) as invoice_amount
			from
				`tabGL Entry`
			where
				account = %s and {dr_or_cr} > 0 {cond}
			group by voucher_type, voucher_no
		""".format(**{
			"cond": cond,
			"dr_or_cr": dr_or_cr
		}), (self.party_account), as_dict=True)

		for d in invoice_list:
			payment_amount = frappe.db.sql("""
				select
					ifnull(sum(ifnull({0}, 0)), 0)
				from
					`tabGL Entry`
				where
					account = %s and {0} > 0
					and against_voucher_type = %s and ifnull(against_voucher, '') = %s
			""".format("credit" if self.party_type == "Customer" else "debit"),
			(self.party_account, d.voucher_type, d.voucher_no))

			payment_amount = payment_amount[0][0] if payment_amount else 0

			if d.invoice_amount > payment_amount:
				non_reconciled_invoices.append({
					'voucher_no': d.voucher_no,
					'voucher_type': d.voucher_type,
					'posting_date': d.posting_date,
					'invoice_amount': flt(d.invoice_amount),
					'outstanding_amount': d.invoice_amount - payment_amount})

		self.add_invoice_entries(non_reconciled_invoices)

	def add_invoice_entries(self, non_reconciled_invoices):
		#Populate 'payment_reconciliation_invoices' with JVs and Invoices to reconcile against
		self.set('payment_reconciliation_invoices', [])

		for e in non_reconciled_invoices:
			ent = self.append('payment_reconciliation_invoices', {})
			ent.invoice_type = e.get('voucher_type')
			ent.invoice_number = e.get('voucher_no')
			ent.invoice_date = e.get('posting_date')
			ent.amount = flt(e.get('invoice_amount'))
			ent.outstanding_amount = e.get('outstanding_amount')

	def reconcile(self, args):
		self.get_invoice_entries()
		self.validate_invoice()
		dr_or_cr = "credit" if self.party_type == "Customer" else "debit"
		lst = []
		for e in self.get('payment_reconciliation_payments'):
			if e.invoice_type and e.invoice_number:
				lst.append({
					'voucher_no' : e.journal_voucher,
					'voucher_detail_no' : e.voucher_detail_number,
					'against_voucher_type' : e.invoice_type,
					'against_voucher'  : e.invoice_number,
					'account' : self.party_account,
					'is_advance' : e.is_advance,
					'dr_or_cr' : dr_or_cr,
					'unadjusted_amt' : flt(e.amount),
					'allocated_amt' : flt(e.amount)
				})

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)
			msgprint(_("Successfully Reconciled"))
			self.get_unreconciled_entries()

	def check_mandatory_to_fetch(self):
		for fieldname in ["company", "party_account"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_label(fieldname)))


	def validate_invoice(self):
		if not self.get("payment_reconciliation_invoices"):
			frappe.throw(_("No records found in the Invoice table"))

		if not self.get("payment_reconciliation_payments"):
			frappe.throw(_("No records found in the Payment table"))

		unreconciled_invoices = frappe._dict()
		for d in self.get("payment_reconciliation_invoices"):
			unreconciled_invoices.setdefault(d.invoice_type, {}).setdefault(d.invoice_number, d.outstanding_amount)

		invoices_to_reconcile = []
		for p in self.get("payment_reconciliation_payments"):
			if p.invoice_type and p.invoice_number:
				invoices_to_reconcile.append(p.invoice_number)

				if p.invoice_number not in unreconciled_invoices.get(p.invoice_type, {}):
					frappe.throw(_("{0}: {1} not found in Invoice Details table")
						.format(p.invoice_type, p.invoice_number))

				if p.amount > unreconciled_invoices.get(p.invoice_type, {}).get(p.invoice_number):
					frappe.throw(_("Row {0}: Payment amount must be less than or equals to invoice outstanding amount. Please refer Note below.").format(p.idx))

		if not invoices_to_reconcile:
			frappe.throw(_("Please select Invoice Type and Invoice Number in atleast one row"))

	def check_condition(self, dr_or_cr):
		cond = self.from_date and " and posting_date >= '" + self.from_date + "'" or ""
		cond += self.to_date and " and posting_date <= '" + self.to_date + "'" or ""

		if self.minimum_amount:
			cond += " and {0} >= %s".format(dr_or_cr) % self.minimum_amount
		if self.maximum_amount:
			cond += " and {0} <= %s".format(dr_or_cr) % self.maximum_amount

		return cond
