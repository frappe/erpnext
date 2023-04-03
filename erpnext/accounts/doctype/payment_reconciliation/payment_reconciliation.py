# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate, nowdate, today

import erpnext
from erpnext.accounts.utils import (
	get_outstanding_invoices,
	reconcile_against_document,
	update_reference_in_payment_entry,
)
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

		non_reconciled_payments = payment_entries + journal_entries + dr_or_cr_notes

		if self.payment_limit:
			non_reconciled_payments = non_reconciled_payments[: self.payment_limit]

		non_reconciled_payments = sorted(
			non_reconciled_payments, key=lambda k: k["posting_date"] or getdate(nowdate())
		)

		self.add_payment_entries(non_reconciled_payments)

	def get_payment_entries(self):
		order_doctype = "Sales Order" if self.party_type == "Customer" else "Purchase Order"
		condition = self.get_conditions(get_payments=True)

		if self.get("cost_center"):
			condition += " and cost_center = '{0}' ".format(self.cost_center)

		payment_entries = get_advance_payment_entries(
			self.party_type,
			self.party,
			self.receivable_payable_account,
			order_doctype,
			against_all_orders=True,
			limit=self.payment_limit,
			condition=condition,
		)

		return payment_entries

	def get_jv_entries(self):
		condition = self.get_conditions()

		if self.get("cost_center"):
			condition += " and t2.cost_center = '{0}' ".format(self.cost_center)

		dr_or_cr = (
			"credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == "Receivable"
			else "debit_in_account_currency"
		)

		bank_account_condition = (
			"t2.against_account like %(bank_cash_account)s" if self.bank_cash_account else "1=1"
		)

		journal_entries = frappe.db.sql(
			"""
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
				and t2.account = %(account)s and {dr_or_cr} > 0 {condition}
				and (t2.reference_type is null or t2.reference_type = '' or
					(t2.reference_type in ('Sales Order', 'Purchase Order')
						and t2.reference_name is not null and t2.reference_name != ''))
				and (CASE
					WHEN t1.voucher_type in ('Debit Note', 'Credit Note')
					THEN 1=1
					ELSE {bank_account_condition}
				END)
			order by t1.posting_date
			""".format(
				**{
					"dr_or_cr": dr_or_cr,
					"bank_account_condition": bank_account_condition,
					"condition": condition,
				}
			),
			{
				"party_type": self.party_type,
				"party": self.party,
				"account": self.receivable_payable_account,
				"bank_cash_account": "%%%s%%" % self.bank_cash_account,
			},
			as_dict=1,
		)

		return list(journal_entries)

	def get_dr_or_cr_notes(self):
		gl = qb.DocType("GL Entry")

		voucher_type = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
		doc = qb.DocType(voucher_type)

		# build conditions
		sub_query_conditions = []
		conditions = []
		sub_query_conditions.append(doc.company == self.company)

		if self.get("from_payment_date"):
			sub_query_conditions.append(doc.posting_date.gte(self.from_payment_date))

		if self.get("to_payment_date"):
			sub_query_conditions.append(doc.posting_date.lte(self.to_payment_date))

		if self.get("cost_center"):
			sub_query_conditions.append(doc.cost_center == self.cost_center)

		dr_or_cr = (
			gl["credit_in_account_currency"]
			if erpnext.get_party_account_type(self.party_type) == "Receivable"
			else gl["debit_in_account_currency"]
		)

		reconciled_dr_or_cr = (
			gl["debit_in_account_currency"]
			if dr_or_cr.name == "credit_in_account_currency"
			else gl["credit_in_account_currency"]
		)

		having_clause = qb.Field("amount") > 0

		if self.minimum_payment_amount:
			having_clause = qb.Field("amount") >= self.minimum_payment_amount
		if self.maximum_payment_amount:
			having_clause = having_clause & qb.Field("amount") <= self.maximum_payment_amount

		sub_query = (
			qb.from_(doc)
			.select(doc.name)
			.where(Criterion.all(sub_query_conditions))
			.where(
				(doc.docstatus == 1)
				& (doc.is_return == 1)
				& ((doc.return_against == "") | (doc.return_against.isnull()))
			)
		)

		query = (
			qb.from_(gl)
			.select(
				gl.against_voucher_type.as_("reference_type"),
				gl.against_voucher.as_("reference_name"),
				(Sum(dr_or_cr) - Sum(reconciled_dr_or_cr)).as_("amount"),
				gl.posting_date,
				gl.account_currency.as_("currency"),
			)
			.where(
				(gl.against_voucher.isin(sub_query))
				& (gl.against_voucher_type == voucher_type)
				& (gl.is_cancelled == 0)
				& (gl.account == self.receivable_payable_account)
				& (gl.party_type == self.party_type)
				& (gl.party == self.party)
			)
			.where(Criterion.all(conditions))
			.groupby(gl.against_voucher)
			.having(having_clause)
		)
		dr_cr_notes = query.run(as_dict=True)
		return dr_cr_notes

	def add_payment_entries(self, non_reconciled_payments):
		self.set("payments", [])

		for payment in non_reconciled_payments:
			row = self.append("payments", {})
			row.update(payment)

	def get_invoice_entries(self):
		# Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

		condition = self.get_conditions(get_invoices=True)

		if self.get("cost_center"):
			condition += " and cost_center = '{0}' ".format(self.cost_center)

		non_reconciled_invoices = get_outstanding_invoices(
			self.party_type, self.party, self.receivable_payable_account, self.company, condition=condition
		)

		if self.invoice_limit:
			non_reconciled_invoices = non_reconciled_invoices[: self.invoice_limit]

		self.add_invoice_entries(non_reconciled_invoices)

	def add_invoice_entries(self, non_reconciled_invoices):
		# Populate 'invoices' with JVs and Invoices to reconcile against
		self.set("invoices", [])

		for entry in non_reconciled_invoices:
			inv = self.append("invoices", {})
			inv.invoice_type = entry.get("voucher_type")
			inv.invoice_number = entry.get("voucher_no")
			inv.invoice_date = entry.get("posting_date")
			inv.amount = flt(entry.get("invoice_amount"))
			inv.currency = entry.get("currency")
			inv.outstanding_amount = flt(entry.get("outstanding_amount"))

	def get_difference_amount(self, allocated_entry):
		if allocated_entry.get("reference_type") != "Payment Entry":
			return

		dr_or_cr = (
			"credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == "Receivable"
			else "debit_in_account_currency"
		)

		row = self.get_payment_details(allocated_entry, dr_or_cr)

		doc = frappe.get_doc(allocated_entry.reference_type, allocated_entry.reference_name)
		update_reference_in_payment_entry(row, doc, do_not_save=True)

		return doc.difference_amount

	@frappe.whitelist()
	def allocate_entries(self, args):
		self.validate_entries()
		entries = []
		for pay in args.get("payments"):
			pay.update({"unreconciled_amount": pay.get("amount")})
			for inv in args.get("invoices"):
				if pay.get("amount") >= inv.get("outstanding_amount"):
					res = self.get_allocated_entry(pay, inv, inv["outstanding_amount"])
					pay["amount"] = flt(pay.get("amount")) - flt(inv.get("outstanding_amount"))
					inv["outstanding_amount"] = 0
				else:
					res = self.get_allocated_entry(pay, inv, pay["amount"])
					inv["outstanding_amount"] = flt(inv.get("outstanding_amount")) - flt(pay.get("amount"))
					pay["amount"] = 0

				res.difference_amount = self.get_difference_amount(res)

				if pay.get("amount") == 0:
					entries.append(res)
					break
				elif inv.get("outstanding_amount") == 0:
					entries.append(res)
					continue

			else:
				break

		self.set("allocation", [])
		for entry in entries:
			if entry["allocated_amount"] != 0:
				row = self.append("allocation", {})
				row.update(entry)

	def get_allocated_entry(self, pay, inv, allocated_amount):
		return frappe._dict(
			{
				"reference_type": pay.get("reference_type"),
				"reference_name": pay.get("reference_name"),
				"reference_row": pay.get("reference_row"),
				"invoice_type": inv.get("invoice_type"),
				"invoice_number": inv.get("invoice_number"),
				"unreconciled_amount": pay.get("unreconciled_amount"),
				"amount": pay.get("amount"),
				"allocated_amount": allocated_amount,
				"difference_amount": pay.get("difference_amount"),
			}
		)

	@frappe.whitelist()
	def reconcile(self):
		self.validate_allocation()
		dr_or_cr = (
			"credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == "Receivable"
			else "debit_in_account_currency"
		)

		entry_list = []
		dr_or_cr_notes = []
		for row in self.get("allocation"):
			reconciled_entry = []
			if row.invoice_number and row.allocated_amount:
				if row.reference_type in ["Sales Invoice", "Purchase Invoice"]:
					reconciled_entry = dr_or_cr_notes
				else:
					reconciled_entry = entry_list

				reconciled_entry.append(self.get_payment_details(row, dr_or_cr))

		if entry_list:
			reconcile_against_document(entry_list)

		if dr_or_cr_notes:
			reconcile_dr_cr_note(dr_or_cr_notes, self.company)

		msgprint(_("Successfully Reconciled"))
		self.get_unreconciled_entries()

	def get_payment_details(self, row, dr_or_cr):
		return frappe._dict(
			{
				"voucher_type": row.get("reference_type"),
				"voucher_no": row.get("reference_name"),
				"voucher_detail_no": row.get("reference_row"),
				"against_voucher_type": row.get("invoice_type"),
				"against_voucher": row.get("invoice_number"),
				"account": self.receivable_payable_account,
				"party_type": self.party_type,
				"party": self.party,
				"is_advance": row.get("is_advance"),
				"dr_or_cr": dr_or_cr,
				"unreconciled_amount": flt(row.get("unreconciled_amount")),
				"unadjusted_amount": flt(row.get("amount")),
				"allocated_amount": flt(row.get("allocated_amount")),
				"difference_amount": flt(row.get("difference_amount")),
				"difference_account": row.get("difference_account"),
			}
		)

	def check_mandatory_to_fetch(self):
		for fieldname in ["company", "party_type", "party", "receivable_payable_account"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_label(fieldname)))

	def validate_entries(self):
		if not self.get("invoices"):
			frappe.throw(_("No records found in the Invoices table"))

		if not self.get("payments"):
			frappe.throw(_("No records found in the Payments table"))

	def validate_allocation(self):
		unreconciled_invoices = frappe._dict()

		for inv in self.get("invoices"):
			unreconciled_invoices.setdefault(inv.invoice_type, {}).setdefault(
				inv.invoice_number, inv.outstanding_amount
			)

		invoices_to_reconcile = []
		for row in self.get("allocation"):
			if row.invoice_type and row.invoice_number and row.allocated_amount:
				invoices_to_reconcile.append(row.invoice_number)

				if flt(row.amount) - flt(row.allocated_amount) < 0:
					frappe.throw(
						_(
							"Row {0}: Allocated amount {1} must be less than or equal to remaining payment amount {2}"
						).format(row.idx, row.allocated_amount, row.amount)
					)

				invoice_outstanding = unreconciled_invoices.get(row.invoice_type, {}).get(row.invoice_number)
				if flt(row.allocated_amount) - invoice_outstanding > 0.009:
					frappe.throw(
						_(
							"Row {0}: Allocated amount {1} must be less than or equal to invoice outstanding amount {2}"
						).format(row.idx, row.allocated_amount, invoice_outstanding)
					)

		if not invoices_to_reconcile:
			frappe.throw(_("No records found in Allocation table"))

	def get_conditions(self, get_invoices=False, get_payments=False):
		condition = " and company = '{0}' ".format(self.company)

		if get_invoices:
			condition += (
				" and posting_date >= {0}".format(frappe.db.escape(self.from_invoice_date))
				if self.from_invoice_date
				else ""
			)
			condition += (
				" and posting_date <= {0}".format(frappe.db.escape(self.to_invoice_date))
				if self.to_invoice_date
				else ""
			)
			dr_or_cr = (
				"debit_in_account_currency"
				if erpnext.get_party_account_type(self.party_type) == "Receivable"
				else "credit_in_account_currency"
			)

			if self.minimum_invoice_amount:
				condition += " and {dr_or_cr} >= {amount}".format(
					dr_or_cr=dr_or_cr, amount=flt(self.minimum_invoice_amount)
				)
			if self.maximum_invoice_amount:
				condition += " and {dr_or_cr} <= {amount}".format(
					dr_or_cr=dr_or_cr, amount=flt(self.maximum_invoice_amount)
				)
		elif get_payments:
			condition += (
				" and posting_date >= {0}".format(frappe.db.escape(self.from_payment_date))
				if self.from_payment_date
				else ""
			)
			condition += (
				" and posting_date <= {0}".format(frappe.db.escape(self.to_payment_date))
				if self.to_payment_date
				else ""
			)

			if self.minimum_payment_amount:
				condition += (
					" and unallocated_amount >= {0}".format(flt(self.minimum_payment_amount))
					if get_payments
					else " and total_debit >= {0}".format(flt(self.minimum_payment_amount))
				)
			if self.maximum_payment_amount:
				condition += (
					" and unallocated_amount <= {0}".format(flt(self.maximum_payment_amount))
					if get_payments
					else " and total_debit <= {0}".format(flt(self.maximum_payment_amount))
				)

		return condition


def reconcile_dr_cr_note(dr_cr_notes, company):
	for inv in dr_cr_notes:
		voucher_type = "Credit Note" if inv.voucher_type == "Sales Invoice" else "Debit Note"

		reconcile_dr_or_cr = (
			"debit_in_account_currency"
			if inv.dr_or_cr == "credit_in_account_currency"
			else "credit_in_account_currency"
		)

		company_currency = erpnext.get_company_currency(company)

		jv = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": voucher_type,
				"posting_date": today(),
				"company": company,
				"multi_currency": 1 if inv.currency != company_currency else 0,
				"accounts": [
					{
						"account": inv.account,
						"party": inv.party,
						"party_type": inv.party_type,
						inv.dr_or_cr: abs(inv.allocated_amount),
						"reference_type": inv.against_voucher_type,
						"reference_name": inv.against_voucher,
						"cost_center": erpnext.get_default_cost_center(company),
					},
					{
						"account": inv.account,
						"party": inv.party,
						"party_type": inv.party_type,
						reconcile_dr_or_cr: (
							abs(inv.allocated_amount)
							if abs(inv.unadjusted_amount) > abs(inv.allocated_amount)
							else abs(inv.unadjusted_amount)
						),
						"reference_type": inv.voucher_type,
						"reference_name": inv.voucher_no,
						"cost_center": erpnext.get_default_cost_center(company),
					},
				],
			}
		)
		jv.flags.ignore_mandatory = True
		jv.submit()
