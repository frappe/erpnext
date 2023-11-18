# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.model.document import Document
from frappe.query_builder import Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt, fmt_money, get_link_to_form, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	is_any_doc_running,
)
from erpnext.accounts.utils import (
	QueryPaymentLedger,
	create_gain_loss_journal,
	get_outstanding_invoices,
	reconcile_against_document,
)
from erpnext.controllers.accounts_controller import get_advance_payment_entries_for_regional


class PaymentReconciliation(Document):
	def __init__(self, *args, **kwargs):
		super(PaymentReconciliation, self).__init__(*args, **kwargs)
		self.common_filter_conditions = []
		self.accounting_dimension_filter_conditions = []
		self.ple_posting_date_filter = []

	def load_from_db(self):
		# 'modified' attribute is required for `run_doc_method` to work properly.
		doc_dict = frappe._dict(
			{
				"modified": None,
				"company": None,
				"party": None,
				"party_type": None,
				"receivable_payable_account": None,
				"default_advance_account": None,
				"from_invoice_date": None,
				"to_invoice_date": None,
				"invoice_limit": 50,
				"from_payment_date": None,
				"to_payment_date": None,
				"payment_limit": 50,
				"minimum_invoice_amount": None,
				"minimum_payment_amount": None,
				"maximum_invoice_amount": None,
				"maximum_payment_amount": None,
				"bank_cash_account": None,
				"cost_center": None,
				"payment_name": None,
				"invoice_name": None,
			}
		)
		super(Document, self).__init__(doc_dict)

	def save(self):
		return

	@staticmethod
	def get_list(args):
		pass

	@staticmethod
	def get_count(args):
		pass

	@staticmethod
	def get_stats(args):
		pass

	def db_insert(self, *args, **kwargs):
		pass

	def db_update(self, *args, **kwargs):
		pass

	def delete(self):
		pass

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
		if self.payment_name:
			condition += "name like '%%{0}%%'".format(self.payment_name)

		payment_entries = get_advance_payment_entries_for_regional(
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

		if self.payment_name:
			condition += f" and t1.name like '%%{self.payment_name}%%'"

		if self.get("cost_center"):
			condition += f" and t2.cost_center = '{self.cost_center}' "

		dr_or_cr = (
			"credit_in_account_currency"
			if erpnext.get_party_account_type(self.party_type) == "Receivable"
			else "debit_in_account_currency"
		)

		bank_account_condition = (
			"t2.against_account like %(bank_cash_account)s" if self.bank_cash_account else "1=1"
		)

		limit = f"limit {self.payment_limit}" if self.payment_limit else " "

		# nosemgrep
		journal_entries = frappe.db.sql(
			"""
			select
				"Journal Entry" as reference_type, t1.name as reference_name,
				t1.posting_date, t1.remark as remarks, t2.name as reference_row,
				{dr_or_cr} as amount, t2.is_advance, t2.exchange_rate,
				t2.account_currency as currency, t2.cost_center as cost_center
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
			{limit}
			""".format(
				**{
					"dr_or_cr": dr_or_cr,
					"bank_account_condition": bank_account_condition,
					"condition": condition,
					"limit": limit,
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

	def get_return_invoices(self):
		voucher_type = "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"
		doc = qb.DocType(voucher_type)

		conditions = []
		conditions.append(doc.docstatus == 1)
		conditions.append(doc[frappe.scrub(self.party_type)] == self.party)
		conditions.append(doc.is_return == 1)

		if self.payment_name:
			conditions.append(doc.name.like(f"%{self.payment_name}%"))

		self.return_invoices_query = (
			qb.from_(doc)
			.select(
				ConstantColumn(voucher_type).as_("voucher_type"),
				doc.name.as_("voucher_no"),
				doc.return_against,
			)
			.where(Criterion.all(conditions))
		)
		if self.payment_limit:
			self.return_invoices_query = self.return_invoices_query.limit(self.payment_limit)

		self.return_invoices = self.return_invoices_query.run(as_dict=True)

	def get_dr_or_cr_notes(self):

		self.build_qb_filter_conditions(get_return_invoices=True)

		ple = qb.DocType("Payment Ledger Entry")

		if erpnext.get_party_account_type(self.party_type) == "Receivable":
			self.common_filter_conditions.append(ple.account_type == "Receivable")
		else:
			self.common_filter_conditions.append(ple.account_type == "Payable")
		self.common_filter_conditions.append(ple.account == self.receivable_payable_account)

		self.get_return_invoices()
		return_invoices = [
			x for x in self.return_invoices if x.return_against == None or x.return_against == ""
		]

		outstanding_dr_or_cr = []
		if return_invoices:
			ple_query = QueryPaymentLedger()
			return_outstanding = ple_query.get_voucher_outstandings(
				vouchers=return_invoices,
				common_filter=self.common_filter_conditions,
				posting_date=self.ple_posting_date_filter,
				min_outstanding=-(self.minimum_payment_amount) if self.minimum_payment_amount else None,
				max_outstanding=-(self.maximum_payment_amount) if self.maximum_payment_amount else None,
				get_payments=True,
			)

			for inv in return_outstanding:
				if inv.outstanding != 0:
					outstanding_dr_or_cr.append(
						frappe._dict(
							{
								"reference_type": inv.voucher_type,
								"reference_name": inv.voucher_no,
								"amount": -(inv.outstanding_in_account_currency),
								"posting_date": inv.posting_date,
								"currency": inv.currency,
								"cost_center": inv.cost_center,
							}
						)
					)
		return outstanding_dr_or_cr

	def add_payment_entries(self, non_reconciled_payments):
		self.set("payments", [])

		for payment in non_reconciled_payments:
			row = self.append("payments", {})
			row.update(payment)

	def get_invoice_entries(self):
		# Fetch JVs, Sales and Purchase Invoices for 'invoices' to reconcile against

		self.build_qb_filter_conditions(get_invoices=True)

		non_reconciled_invoices = get_outstanding_invoices(
			self.party_type,
			self.party,
			self.receivable_payable_account,
			common_filter=self.common_filter_conditions,
			posting_date=self.ple_posting_date_filter,
			min_outstanding=self.minimum_invoice_amount if self.minimum_invoice_amount else None,
			max_outstanding=self.maximum_invoice_amount if self.maximum_invoice_amount else None,
			accounting_dimensions=self.accounting_dimension_filter_conditions,
			limit=self.invoice_limit,
			voucher_no=self.invoice_name,
		)

		cr_dr_notes = (
			[x.voucher_no for x in self.return_invoices]
			if self.party_type in ["Customer", "Supplier"]
			else []
		)
		# Filter out cr/dr notes from outstanding invoices list
		# Happens when non-standalone cr/dr notes are linked with another invoice through journal entry
		non_reconciled_invoices = [x for x in non_reconciled_invoices if x.voucher_no not in cr_dr_notes]

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

	def get_difference_amount(self, payment_entry, invoice, allocated_amount):
		difference_amount = 0
		if frappe.get_cached_value(
			"Account", self.receivable_payable_account, "account_currency"
		) != frappe.get_cached_value("Company", self.company, "default_currency"):
			if invoice.get("exchange_rate") and payment_entry.get("exchange_rate", 1) != invoice.get(
				"exchange_rate", 1
			):
				allocated_amount_in_ref_rate = payment_entry.get("exchange_rate", 1) * allocated_amount
				allocated_amount_in_inv_rate = invoice.get("exchange_rate", 1) * allocated_amount
				difference_amount = allocated_amount_in_ref_rate - allocated_amount_in_inv_rate

		return difference_amount

	@frappe.whitelist()
	def is_auto_process_enabled(self):
		return frappe.db.get_single_value("Accounts Settings", "auto_reconcile_payments")

	@frappe.whitelist()
	def calculate_difference_on_allocation_change(self, payment_entry, invoice, allocated_amount):
		invoice_exchange_map = self.get_invoice_exchange_map(invoice, payment_entry)
		invoice[0]["exchange_rate"] = invoice_exchange_map.get(invoice[0].get("invoice_number"))
		if payment_entry[0].get("reference_type") in ["Sales Invoice", "Purchase Invoice"]:
			payment_entry[0]["exchange_rate"] = invoice_exchange_map.get(
				payment_entry[0].get("reference_name")
			)

		new_difference_amount = self.get_difference_amount(
			payment_entry[0], invoice[0], allocated_amount
		)
		return new_difference_amount

	@frappe.whitelist()
	def allocate_entries(self, args):
		self.validate_entries()

		invoice_exchange_map = self.get_invoice_exchange_map(args.get("invoices"), args.get("payments"))
		default_exchange_gain_loss_account = frappe.get_cached_value(
			"Company", self.company, "exchange_gain_loss_account"
		)

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

				inv["exchange_rate"] = invoice_exchange_map.get(inv.get("invoice_number"))
				if pay.get("reference_type") in ["Sales Invoice", "Purchase Invoice"]:
					pay["exchange_rate"] = invoice_exchange_map.get(pay.get("reference_name"))

				res.difference_amount = self.get_difference_amount(pay, inv, res["allocated_amount"])
				res.difference_account = default_exchange_gain_loss_account
				res.exchange_rate = inv.get("exchange_rate")
				res.update({"gain_loss_posting_date": pay.get("posting_date")})

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
				"currency": inv.get("currency"),
				"cost_center": pay.get("cost_center"),
			}
		)

	def reconcile_allocations(self, skip_ref_details_update_for_pe=False):
		adjust_allocations_for_taxes(self)
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

				payment_details = self.get_payment_details(row, dr_or_cr)
				reconciled_entry.append(payment_details)

		if entry_list:
			reconcile_against_document(entry_list, skip_ref_details_update_for_pe)

		if dr_or_cr_notes:
			reconcile_dr_cr_note(dr_or_cr_notes, self.company)

	@frappe.whitelist()
	def reconcile(self):
		if frappe.db.get_single_value("Accounts Settings", "auto_reconcile_payments"):
			running_doc = is_any_doc_running(
				dict(
					company=self.company,
					party_type=self.party_type,
					party=self.party,
					receivable_payable_account=self.receivable_payable_account,
				)
			)

			if running_doc:
				frappe.throw(
					_("A Reconciliation Job {0} is running for the same filters. Cannot reconcile now").format(
						get_link_to_form("Auto Reconcile", running_doc)
					)
				)
				return

		self.validate_allocation()
		self.reconcile_allocations()
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
				"exchange_rate": row.get("exchange_rate"),
				"party_type": self.party_type,
				"party": self.party,
				"is_advance": row.get("is_advance"),
				"dr_or_cr": dr_or_cr,
				"unreconciled_amount": flt(row.get("unreconciled_amount")),
				"unadjusted_amount": flt(row.get("amount")),
				"allocated_amount": flt(row.get("allocated_amount")),
				"difference_amount": flt(row.get("difference_amount")),
				"difference_account": row.get("difference_account"),
				"difference_posting_date": row.get("gain_loss_posting_date"),
				"cost_center": row.get("cost_center"),
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

	def get_invoice_exchange_map(self, invoices, payments):
		sales_invoices = [
			d.get("invoice_number") for d in invoices if d.get("invoice_type") == "Sales Invoice"
		]

		sales_invoices.extend(
			[d.get("reference_name") for d in payments if d.get("reference_type") == "Sales Invoice"]
		)
		purchase_invoices = [
			d.get("invoice_number") for d in invoices if d.get("invoice_type") == "Purchase Invoice"
		]
		purchase_invoices.extend(
			[d.get("reference_name") for d in payments if d.get("reference_type") == "Purchase Invoice"]
		)

		invoice_exchange_map = frappe._dict()

		if sales_invoices:
			sales_invoice_map = frappe._dict(
				frappe.db.get_all(
					"Sales Invoice",
					filters={"name": ("in", sales_invoices)},
					fields=["name", "conversion_rate"],
					as_list=1,
				)
			)

			invoice_exchange_map.update(sales_invoice_map)

		if purchase_invoices:
			purchase_invoice_map = frappe._dict(
				frappe.db.get_all(
					"Purchase Invoice",
					filters={"name": ("in", purchase_invoices)},
					fields=["name", "conversion_rate"],
					as_list=1,
				)
			)

			invoice_exchange_map.update(purchase_invoice_map)

		return invoice_exchange_map

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

	def build_qb_filter_conditions(self, get_invoices=False, get_return_invoices=False):
		self.common_filter_conditions.clear()
		self.accounting_dimension_filter_conditions.clear()
		self.ple_posting_date_filter.clear()
		ple = qb.DocType("Payment Ledger Entry")

		self.common_filter_conditions.append(ple.company == self.company)

		if self.get("cost_center") and (get_invoices or get_return_invoices):
			self.accounting_dimension_filter_conditions.append(ple.cost_center == self.cost_center)

		if get_invoices:
			if self.from_invoice_date:
				self.ple_posting_date_filter.append(ple.posting_date.gte(self.from_invoice_date))
			if self.to_invoice_date:
				self.ple_posting_date_filter.append(ple.posting_date.lte(self.to_invoice_date))

		elif get_return_invoices:
			if self.from_payment_date:
				self.ple_posting_date_filter.append(ple.posting_date.gte(self.from_payment_date))
			if self.to_payment_date:
				self.ple_posting_date_filter.append(ple.posting_date.lte(self.to_payment_date))

	def get_conditions(self, get_payments=False):
		condition = " and company = '{0}' ".format(self.company)

		if self.get("cost_center") and get_payments:
			condition = " and cost_center = '{0}' ".format(self.cost_center)

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
						"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} against {inv.against_voucher}",
						"exchange_rate": inv.exchange_rate,
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
						"cost_center": inv.cost_center or erpnext.get_default_cost_center(company),
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} from {inv.voucher_no}",
						"exchange_rate": inv.exchange_rate,
					},
				],
			}
		)

		jv.flags.ignore_mandatory = True
		jv.flags.skip_remarks_creation = True
		jv.flags.ignore_exchange_rate = True
		jv.is_system_generated = True
		jv.remark = None
		jv.submit()

		if inv.difference_amount != 0:
			# make gain/loss journal
			if inv.party_type == "Customer":
				dr_or_cr = "credit" if inv.difference_amount < 0 else "debit"
			else:
				dr_or_cr = "debit" if inv.difference_amount < 0 else "credit"

			reverse_dr_or_cr = "debit" if dr_or_cr == "credit" else "credit"

			create_gain_loss_journal(
				company,
				today(),
				inv.party_type,
				inv.party,
				inv.account,
				inv.difference_account,
				inv.difference_amount,
				dr_or_cr,
				reverse_dr_or_cr,
				inv.voucher_type,
				inv.voucher_no,
				None,
				inv.against_voucher_type,
				inv.against_voucher,
				None,
				inv.cost_center,
			)


@erpnext.allow_regional
def adjust_allocations_for_taxes(doc):
	pass
