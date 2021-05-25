# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import flt, today
from frappe import msgprint, _
from frappe.model.document import Document
from erpnext.accounts.utils import (get_outstanding_invoices,
	update_reference_in_payment_entry, reconcile_against_document)
from erpnext.controllers.accounts_controller import get_advance_payment_entries

class PaymentReconciliation(Document):
	@frappe.whitelist()
	def get_unreconciled_entries(self):
		self.get_nonreconciled_payment_entries()
		self.get_invoice_entries()

	def get_nonreconciled_payment_entries(self):
		self.check_mandatory_to_fetch()

		payment_entries = self.get_payment_entries()
		journal_entries = self.get_jv_entries()

		if self.party_type in ["Customer", "Supplier"]:
			dr_or_cr_notes = self.get_dr_or_cr_notes()
		else:
			dr_or_cr_notes = []

		self.add_payment_entries(payment_entries + journal_entries + dr_or_cr_notes)

	def get_payment_entries(self):
		order_doctype = "Sales Order" if self.party_type=="Customer" else "Purchase Order"
		payment_entries = get_advance_payment_entries(self.party_type, self.party,
			self.receivable_payable_account, order_doctype, against_all_orders=True, limit=self.limit)

		return payment_entries

	def get_jv_entries(self):
		dr_or_cr = ("credit_in_account_currency" if erpnext.get_party_account_type(self.party_type) == 'Receivable'
			else "debit_in_account_currency")

		bank_account_condition = "t2.against_account like %(bank_cash_account)s" \
				if self.bank_cash_account else "1=1"

		limit_cond = "limit %s" % self.limit if self.limit else ""

		journal_entries = frappe.db.sql("""
			select
				"Journal Entry" as reference_type, t1.name as reference_name,
				t1.posting_date, t1.remark as remarks, t2.name as reference_row,
				{dr_or_cr} as amount, t2.is_advance,
				t2.account_currency as currency
			from
				`tabJournal Entry` t1, `tabJournal Entry Account` t2
			where
				t1.name = t2.parent and t1.docstatus = 1 and t2.docstatus = 1
				and t2.party_type = %(party_type)s and t2.party = %(party)s
				and t2.account = %(account)s and {dr_or_cr} > 0
				and (t2.reference_type is null or t2.reference_type = '' or
					(t2.reference_type in ('Sales Order', 'Purchase Order')
						and t2.reference_name is not null and t2.reference_name != ''))
				and (CASE
					WHEN t1.voucher_type in ('Debit Note', 'Credit Note')
					THEN 1=1
					ELSE {bank_account_condition}
				END)
			order by t1.posting_date {limit_cond}
			""".format(**{
				"dr_or_cr": dr_or_cr,
				"bank_account_condition": bank_account_condition,
				"limit_cond": limit_cond
			}), {
				"party_type": self.party_type,
				"party": self.party,
				"account": self.receivable_payable_account,
				"bank_cash_account": "%%%s%%" % self.bank_cash_account
			}, as_dict=1)

		return list(journal_entries)

	def get_dr_or_cr_notes(self):
		dr_or_cr = ("credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == 'Receivable' else "debit_in_account_currency")

		reconciled_dr_or_cr =  ("debit_in_account_currency"
			if dr_or_cr == "credit_in_account_currency" else "credit_in_account_currency")

		voucher_type = ('Sales Invoice'
			if self.party_type == 'Customer' else "Purchase Invoice")

		return frappe.db.sql(""" SELECT doc.name as reference_name, %(voucher_type)s as reference_type,
				(sum(gl.{dr_or_cr}) - sum(gl.{reconciled_dr_or_cr})) as amount,
				account_currency as currency
			FROM `tab{doc}` doc, `tabGL Entry` gl
			WHERE
				(doc.name = gl.against_voucher or doc.name = gl.voucher_no)
				and doc.{party_type_field} = %(party)s
				and doc.is_return = 1 and ifnull(doc.return_against, "") = ""
				and gl.against_voucher_type = %(voucher_type)s
				and doc.docstatus = 1 and gl.party = %(party)s
				and gl.party_type = %(party_type)s and gl.account = %(account)s
				and gl.is_cancelled = 0
			GROUP BY doc.name
			Having
				amount > 0
		""".format(
			doc=voucher_type,
			dr_or_cr=dr_or_cr,
			reconciled_dr_or_cr=reconciled_dr_or_cr,
			party_type_field=frappe.scrub(self.party_type)),
			{
				'party': self.party,
				'party_type': self.party_type,
				'voucher_type': voucher_type,
				'account': self.receivable_payable_account
			}, as_dict=1)

	def add_payment_entries(self, entries):
		self.set('payments', [])
		for e in entries:
			row = self.append('payments', {})
			row.update(e)

	def get_invoice_entries(self):
		#Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

		condition = self.check_condition()

		non_reconciled_invoices = get_outstanding_invoices(self.party_type, self.party,
			self.receivable_payable_account, condition=condition)

		if self.limit:
			non_reconciled_invoices = non_reconciled_invoices[:self.limit]

		self.add_invoice_entries(non_reconciled_invoices)

	def add_invoice_entries(self, non_reconciled_invoices):
		#Populate 'invoices' with JVs and Invoices to reconcile against
		self.set('invoices', [])

		for e in non_reconciled_invoices:
			ent = self.append('invoices', {})
			ent.invoice_type = e.get('voucher_type')
			ent.invoice_number = e.get('voucher_no')
			ent.invoice_date = e.get('posting_date')
			ent.amount = flt(e.get('invoice_amount'))
			ent.currency = e.get('currency')
			ent.outstanding_amount = e.get('outstanding_amount')

	@frappe.whitelist()
	def reconcile(self, args):
		for e in self.get('payments'):
			e.invoice_type = None
			if e.invoice_number and " | " in e.invoice_number:
				e.invoice_type, e.invoice_number = e.invoice_number.split(" | ")

		self.get_invoice_entries()
		self.validate_invoice()
		dr_or_cr = ("credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == 'Receivable' else "debit_in_account_currency")

		lst = []
		dr_or_cr_notes = []
		for e in self.get('payments'):
			reconciled_entry = []
			if e.invoice_number and e.allocated_amount:
				if e.reference_type in ['Sales Invoice', 'Purchase Invoice']:
					reconciled_entry = dr_or_cr_notes
				else:
					reconciled_entry = lst

				reconciled_entry.append(self.get_payment_details(e, dr_or_cr))

		if lst:
			reconcile_against_document(lst)

		if dr_or_cr_notes:
			reconcile_dr_cr_note(dr_or_cr_notes, self.company)

		msgprint(_("Successfully Reconciled"))
		self.get_unreconciled_entries()

	def get_payment_details(self, row, dr_or_cr):
		return frappe._dict({
			'voucher_type': row.reference_type,
			'voucher_no' : row.reference_name,
			'voucher_detail_no' : row.reference_row,
			'against_voucher_type' : row.invoice_type,
			'against_voucher'  : row.invoice_number,
			'account' : self.receivable_payable_account,
			'party_type': self.party_type,
			'party': self.party,
			'is_advance' : row.is_advance,
			'dr_or_cr' : dr_or_cr,
			'unadjusted_amount' : flt(row.amount),
			'allocated_amount' : flt(row.allocated_amount),
			'difference_amount': row.difference_amount,
			'difference_account': row.difference_account
		})

	@frappe.whitelist()
	def get_difference_amount(self, child_row):
		if child_row.get("reference_type") != 'Payment Entry': return

		child_row = frappe._dict(child_row)

		if child_row.invoice_number and " | " in child_row.invoice_number:
			child_row.invoice_type, child_row.invoice_number = child_row.invoice_number.split(" | ")

		dr_or_cr = ("credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == 'Receivable' else "debit_in_account_currency")

		row = self.get_payment_details(child_row, dr_or_cr)

		doc = frappe.get_doc(row.voucher_type, row.voucher_no)
		update_reference_in_payment_entry(row, doc, do_not_save=True)

		return doc.difference_amount

	def check_mandatory_to_fetch(self):
		for fieldname in ["company", "party_type", "party", "receivable_payable_account"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_label(fieldname)))

	def validate_invoice(self):
		if not self.get("invoices"):
			frappe.throw(_("No records found in the Invoice table"))

		if not self.get("payments"):
			frappe.throw(_("No records found in the Payment table"))

		unreconciled_invoices = frappe._dict()
		for d in self.get("invoices"):
			unreconciled_invoices.setdefault(d.invoice_type, {}).setdefault(d.invoice_number, d.outstanding_amount)

		invoices_to_reconcile = []
		for p in self.get("payments"):
			if p.invoice_type and p.invoice_number and p.allocated_amount:
				invoices_to_reconcile.append(p.invoice_number)

				if p.invoice_number not in unreconciled_invoices.get(p.invoice_type, {}):
					frappe.throw(_("{0}: {1} not found in Invoice Details table")
						.format(p.invoice_type, p.invoice_number))

				if flt(p.allocated_amount) > flt(p.amount):
					frappe.throw(_("Row {0}: Allocated amount {1} must be less than or equals to Payment Entry amount {2}")
						.format(p.idx, p.allocated_amount, p.amount))

				invoice_outstanding = unreconciled_invoices.get(p.invoice_type, {}).get(p.invoice_number)
				if flt(p.allocated_amount) - invoice_outstanding > 0.009:
					frappe.throw(_("Row {0}: Allocated amount {1} must be less than or equals to invoice outstanding amount {2}")
						.format(p.idx, p.allocated_amount, invoice_outstanding))

		if not invoices_to_reconcile:
			frappe.throw(_("Please select Allocated Amount, Invoice Type and Invoice Number in atleast one row"))

	def check_condition(self):
		cond = " and posting_date >= {0}".format(frappe.db.escape(self.from_date)) if self.from_date else ""
		cond += " and posting_date <= {0}".format(frappe.db.escape(self.to_date)) if self.to_date else ""
		dr_or_cr = ("debit_in_account_currency" if erpnext.get_party_account_type(self.party_type) == 'Receivable'
			else "credit_in_account_currency")

		if self.minimum_amount:
			cond += " and `{0}` >= {1}".format(dr_or_cr, flt(self.minimum_amount))
		if self.maximum_amount:
			cond += " and `{0}` <= {1}".format(dr_or_cr, flt(self.maximum_amount))

		return cond

def reconcile_dr_cr_note(dr_cr_notes, company):
	for d in dr_cr_notes:
		voucher_type = ('Credit Note'
			if d.voucher_type == 'Sales Invoice' else 'Debit Note')

		reconcile_dr_or_cr = ('debit_in_account_currency'
			if d.dr_or_cr == 'credit_in_account_currency' else 'credit_in_account_currency')

		company_currency = erpnext.get_company_currency(company)

		jv = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": voucher_type,
			"posting_date": today(),
			"company": company,
			"multi_currency": 1 if d.currency != company_currency else 0,
			"accounts": [
				{
					'account': d.account,
					'party': d.party,
					'party_type': d.party_type,
					d.dr_or_cr: abs(d.allocated_amount),
					'reference_type': d.against_voucher_type,
					'reference_name': d.against_voucher,
					'cost_center': erpnext.get_default_cost_center(company)
				},
				{
					'account': d.account,
					'party': d.party,
					'party_type': d.party_type,
					reconcile_dr_or_cr: (abs(d.allocated_amount)
						if abs(d.unadjusted_amount) > abs(d.allocated_amount) else abs(d.unadjusted_amount)),
					'reference_type': d.voucher_type,
					'reference_name': d.voucher_no,
					'cost_center': erpnext.get_default_cost_center(company)
				}
			]
		})

		jv.submit()