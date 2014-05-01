# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import flt

from frappe import msgprint, _

from frappe.model.document import Document

class PaymenttoInvoiceMatchingTool(Document):
	def get_voucher_details(self):
		total_amount = frappe.db.sql("""select sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))
			from `tabGL Entry`
			where voucher_type = %s and voucher_no = %s
				and account = %s and ifnull(against_voucher, '') != voucher_no""",
			(self.voucher_type, self.voucher_no, self.account))

		self.total_amount = total_amount and flt(total_amount[0][0]) or 0

		reconciled_payment = frappe.db.sql("""
			select abs(sum(ifnull(debit, 0)) - sum(ifnull(credit, 0)))
			from `tabGL Entry`
			where against_voucher_type = %s and against_voucher = %s and account = %s
		""", (self.voucher_type, self.voucher_no, self.account))

		reconciled_payment = reconciled_payment and flt(reconciled_payment[0][0]) or 0
		self.unmatched_amount = self.total_amount - reconciled_payment

	def get_against_entries(self):
		self.set('against_entries', [])
		gle = self.get_gl_entries()
		self.create_against_entries_table(gle)

	def get_gl_entries(self):
		self.validate_mandatory()

		dr_or_cr = "credit" if self.total_amount > 0 else "debit"

		cond = self.from_date and " and t1.posting_date >= '" + self.from_date + "'" or ""
		cond += self.to_date and " and t1.posting_date <= '" + self.to_date + "'" or ""

		if self.amt_greater_than:
			cond += ' and abs(ifnull(t2.debit, 0) - ifnull(t2.credit, 0)) >= ' + self.amt_greater_than
		if self.amt_less_than:
			cond += ' and abs(ifnull(t2.debit, 0) - ifnull(t2.credit, 0)) >= ' + self.amt_less_than

		gle = frappe.db.sql("""
			select
				t1.name as voucher_no, t1.posting_date, t1.total_debit as total_amt,
			 	abs(ifnull(t2.debit, 0) - ifnull(t2.credit, 0)) as unmatched_amount, t1.remark,
			 	t2.against_account, t2.name as voucher_detail_no, t2.is_advance
			from
				`tabJournal Voucher` t1, `tabJournal Voucher Detail` t2
			where
				t1.name = t2.parent and t1.docstatus = 1 and t2.account = %s
				and ifnull(t2.against_voucher, '')='' and ifnull(t2.against_invoice, '')=''
				and ifnull(t2.against_jv, '')='' and t2.%s > 0 and t1.name != %s
				and not exists (select * from `tabJournal Voucher Detail`
					where parent=%s and against_jv = t1.name) %s
			group by t1.name, t2.name """ %	('%s', dr_or_cr, '%s', '%s', cond),
			(self.account, self.voucher_no, self.voucher_no), as_dict=1)

		return gle

	def create_against_entries_table(self, gle):
		adjusted_jv = {}
		for d in gle:
			if not adjusted_jv.has_key(d.get("voucher_no")):
				matched_amount = frappe.db.sql("""
					select
						ifnull(abs(sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))), 0)
					from
						`tabGL Entry`
					where
						account = %s and against_voucher_type = "Journal Voucher"
						and ifnull(against_voucher, '') = %s
				""", (self.account, d.get('voucher_no')))
				matched_amount = matched_amount[0][0] if matched_amount else 0
			else:
				matched_amount = adjusted_jv.get(d.get("voucher_no"))

			if matched_amount < flt(d.get('unmatched_amount')):
				unmatched_amount = flt(d.get('unmatched_amount')) - matched_amount
				adjusted_jv.setdefault(d.get("voucher_no"), 0)
			else:
				unmatched_amount = 0
				adjusted_jv.setdefault(d.get("voucher_no"), matched_amount - flt(d.get('unmatched_amount')))

			if unmatched_amount:
				ch = self.append('against_entries', {})
				ch.voucher_no = d.get('voucher_no')
				ch.posting_date = d.get('posting_date')
				ch.unmatched_amount = unmatched_amount
				ch.total_amt = flt(d.get('total_amt'))
				ch.against_account = d.get('against_account')
				ch.remarks = d.get('remark')
				ch.voucher_detail_no = d.get('voucher_detail_no')
				ch.is_advance = d.get("is_advance")
				ch.original_amount = flt(d.get('unmatched_amount'))

	def validate_mandatory(self):
		for fieldname in ["account", "voucher_type", "voucher_no"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_label("fieldname")))

		if not frappe.db.exists(self.voucher_type, self.voucher_no):
			frappe.throw(_("Voucher No is not valid"))

	def reconcile(self):
		self.validate_mandatory()
		self.validate_allocated_amount()

		dr_or_cr = "credit" if self.total_amount > 0 else "debit"

		lst = []
		for d in self.get('against_entries'):
			if flt(d.allocated_amount) > 0:
				lst.append({
					'voucher_no' : d.voucher_no,
					'voucher_detail_no' : d.voucher_detail_no,
					'against_voucher_type' : self.voucher_type,
					'against_voucher'  : self.voucher_no,
					'account' : self.account,
					'is_advance' : d.is_advance,
					'dr_or_cr' : dr_or_cr,
					'unadjusted_amt' : flt(d.original_amount),
					'allocated_amt' : flt(d.allocated_amount)
				})

		if lst:
			from erpnext.accounts.utils import reconcile_against_document
			reconcile_against_document(lst)
			self.get_voucher_details()
			self.get_against_entries()
			msgprint(_("Successfully allocated"))

	def validate_allocated_amount(self):
		if not self.total_allocated_amount:
			frappe.throw(_("You must allocate amount before reconcile"))
		elif self.total_allocated_amount > self.unmatched_amount:
			frappe.throw(_("Total Allocated Amount can not be greater than unmatched amount"))

def get_voucher_nos(doctype, txt, searchfield, start, page_len, filters):
	non_reconclied_entries = []
	entries = frappe.db.sql("""
		select
			voucher_no, posting_date, ifnull(abs(sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))), 0) as amount
		from
			`tabGL Entry`
		where
			account = %s and voucher_type = %s and voucher_no like %s
			and ifnull(against_voucher, '') = ''
		group by voucher_no
	""", (filters["account"], filters["voucher_type"], "%%%s%%" % txt), as_dict=True)

	for d in entries:
		adjusted_amount = frappe.db.sql("""
			select
				ifnull(abs(sum(ifnull(debit, 0)) - sum(ifnull(credit, 0))), 0)
			from
				`tabGL Entry`
			where
				account = %s and against_voucher_type = %s and ifnull(against_voucher, '') = %s
		""", (filters["account"], filters["voucher_type"], d.voucher_no))
		adjusted_amount = adjusted_amount[0][0] if adjusted_amount else 0

		if d.amount > adjusted_amount:
			non_reconclied_entries.append([d.voucher_no, d.posting_date, d.amount])

	return non_reconclied_entries
