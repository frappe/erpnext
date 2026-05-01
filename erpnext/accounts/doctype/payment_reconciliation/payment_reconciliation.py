# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.permissions import get_user_permissions
from frappe.query_builder import Case, Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.utils import flt, fmt_money, get_link_to_form, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	is_any_doc_running,
)
from erpnext.accounts.services.exchange_gain_loss import get_exchange_gain_loss_account
from erpnext.accounts.utils import (
	QueryPaymentLedger,
	create_gain_loss_journal,
	reconcile_against_document,
)


class Classifier:
	"""Classifies a PLE/voucher row as Receivable or Payable based on account direction.

	The rule is universal across all voucher types (Sales Invoice, Purchase Invoice,
	Payment Entry, Journal Entry) and across regular vs return/advance variants:

	    Receivable account + positive amount  →  Receivable  (owed to us)
	    Receivable account + negative amount  →  Payable     (we owe back)
	    Payable    account + positive amount  →  Payable     (we owe)
	    Payable    account + negative amount  →  Receivable  (owed back to us)

	Worked cases:
	    Sales Invoice (regular):       Receivable account, +ve  →  Receivable
	    Sales Invoice (return / CN):   Receivable account, -ve  →  Payable
	    Purchase Invoice (regular):    Payable    account, +ve  →  Payable
	    Purchase Invoice (return / DN):Payable    account, -ve  →  Receivable
	    Payment Entry (Receive):       Receivable account, -ve  →  Payable
	    Payment Entry (Pay):           Payable    account, -ve  →  Receivable
	    Journal Entry Dr to party:     party account,      +ve  →  Receivable
	    Journal Entry Cr to party:     party account,      -ve  →  Payable

	"""

	RECEIVABLE = "Receivable"
	PAYABLE = "Payable"

	@staticmethod
	def classify(account_type: str, amount: float) -> str:
		"""Return "Receivable" or "Payable" for an entry.

		Args:
		        account_type: Account doctype's `account_type`. Must be "Receivable" or "Payable".
		        amount: PLE amount (signed; positive = balance in the account's natural direction).
		"""
		if account_type not in (Classifier.RECEIVABLE, Classifier.PAYABLE):
			frappe.throw(_("Unsupported account type {0}").format(account_type))

		if not amount:
			frappe.throw(_("Cannot classify entry with zero amount."))

		positive = amount > 0
		if account_type == Classifier.RECEIVABLE:
			return Classifier.RECEIVABLE if positive else Classifier.PAYABLE
		else:  # Payable
			return Classifier.PAYABLE if positive else Classifier.RECEIVABLE

	@staticmethod
	def is_receivable(account_type: str, amount: float) -> bool:
		return Classifier.classify(account_type, amount) == Classifier.RECEIVABLE

	@staticmethod
	def is_payable(account_type: str, amount: float) -> bool:
		return Classifier.classify(account_type, amount) == Classifier.PAYABLE


class OpenBalanceFetcher:
	"""
	Two-query fetcher for all open (unallocated) party balances.

	    Query 1 (PLE via QueryPaymentLedger):  SI / PI / PE / CN / DN
	        WHERE against_voucher_type != 'Journal Entry'
	        Returns rows of either sign.

	    Query 2 (Journal Entry Account direct):  JE party rows
	        Returns one row per unallocated JEA row, with PLE-direction signed amount.

	After fetch, `_enrich_voucher_metadata` attached additional fields
	"""

	def __init__(self, pr):
		self.pr = pr
		self.company = pr.company
		self.party_type = pr.party_type
		self.party = pr.party
		self.dimensions = pr.dimensions

	def fetch(self):
		accounts = self._get_party_accounts()
		if not accounts:
			return []

		rows = self._query_ple_outstanding(accounts) + self._query_je_outstanding(accounts)
		if not rows:
			return []

		self._enrich_voucher_metadata(rows)
		return rows

	def _get_party_accounts(self):
		"""
		If `receivable_payable_account` is set: just that one (single-account mode).
		Otherwise (cross-account mode): query distinct accounts from PLE.
		"""
		accounts = set()
		ple = qb.DocType("Payment Ledger Entry")
		account = qb.DocType("Account")
		rows = (
			qb.from_(ple)
			.inner_join(account)
			.on(ple.account == account.name)
			.select(ple.account)
			.distinct()
			.where(
				(ple.company == self.company)
				& (ple.party_type == self.party_type)
				& (ple.party == self.party)
				& (ple.delinked == 0)
			)
		)

		if self.pr.receivable_payable_account:
			accounts.add(self.pr.receivable_payable_account)
		else:
			natural_root = "Asset" if self.party_type == "Customer" else "Liability"
			normal_accounts = rows.where(account.root_type == natural_root).run(as_dict=True)
			accounts.update([r.account for r in normal_accounts])

		if self.pr.default_advance_account:
			accounts.add(self.pr.default_advance_account)
		else:
			opposite_root = "Liability" if self.party_type == "Customer" else "Asset"
			advance_accounts = rows.where(account.root_type == opposite_root).run(as_dict=True)
			accounts.update([r.account for r in advance_accounts])

		return accounts

	def _build_filters(self, accounts):
		ple = qb.DocType("Payment Ledger Entry")

		common_filter = [
			ple.company == self.company,
			ple.party_type == self.party_type,
			ple.party == self.party,
			ple.account.isin(accounts),
		]
		if self.pr.currency_filter:
			common_filter.append(ple.account_currency == self.pr.currency_filter)

		posting_date_filter = []
		if self.pr.from_date:
			posting_date_filter.append(ple.posting_date.gte(self.pr.from_date))
		if self.pr.to_date:
			posting_date_filter.append(ple.posting_date.lte(self.pr.to_date))

		dimension_filter = []
		for dim in self.dimensions:
			val = self.pr.get(dim.fieldname)
			if val and frappe.db.has_column("Payment Ledger Entry", dim.fieldname):
				dimension_filter.append(ple[dim.fieldname] == val)

		return common_filter, posting_date_filter, dimension_filter

	def _query_ple_outstanding(self, accounts):
		common_filter, posting_date_filter, dimension_filter = self._build_filters(accounts)
		ple = qb.DocType("Payment Ledger Entry")
		common_filter.append(ple.against_voucher_type != "Journal Entry")

		ple_query = QueryPaymentLedger()
		raw = ple_query.get_voucher_outstandings(
			common_filter=common_filter,
			posting_date=posting_date_filter,
			accounting_dimensions=dimension_filter,
			exclude_zero_outstanding=True,
		)
		return [self._project_ple_row(frappe._dict(r)) for r in raw if self._passes_amount_filter(r)]

	def _project_ple_row(self, r):
		"""Project a `QueryPaymentLedger` result row onto the OpenBalance shape."""
		signed = flt(r.outstanding_in_account_currency)
		r.outstanding_amount = signed  # signed; classifier reads sign, downstream uses abs
		r.amount = flt(r.invoice_amount_in_account_currency)
		r.voucher_row = None  # PLE-side rows are voucher-level, not row-level
		return r

	def _passes_amount_filter(self, r):
		"""min/max amount on absolute outstanding"""
		signed = flt(r.get("outstanding_in_account_currency") or r.get("outstanding_amount"))
		if not signed:
			return False

		abs_out = abs(signed)
		min_amt = self.pr.min_amount or None
		max_amt = self.pr.max_amount or None
		if min_amt and abs_out < min_amt:
			return False
		if max_amt and abs_out > max_amt:
			return False

		return True

	def _query_je_outstanding(self, accounts):
		je = qb.DocType("Journal Entry")
		jea = qb.DocType("Journal Entry Account")
		account_dt = qb.DocType("Account")

		party_account_type = erpnext.get_party_account_type(self.party_type)
		if party_account_type == "Receivable":
			# positive amount = Dr balance = debit - credit
			signed_amount = jea.debit_in_account_currency - jea.credit_in_account_currency
		else:
			# positive amount = Cr balance = credit - debit
			signed_amount = jea.credit_in_account_currency - jea.debit_in_account_currency

		conditions = [
			je.docstatus == 1,
			je.company == self.company,
			jea.party_type == self.party_type,
			jea.party == self.party,
			jea.account.isin(accounts),
			(
				(jea.reference_type == "")
				| (jea.reference_type.isnull())
				| (jea.reference_type.isin(("Sales Order", "Purchase Order")))
			),
			signed_amount.ne(0),
		]
		if self.pr.from_date:
			conditions.append(je.posting_date.gte(self.pr.from_date))
		if self.pr.to_date:
			conditions.append(je.posting_date.lte(self.pr.to_date))
		if self.pr.currency_filter:
			conditions.append(jea.account_currency == self.pr.currency_filter)
		if self.pr.min_amount:
			conditions.append(signed_amount.abs().gte(self.pr.min_amount))
		if self.pr.max_amount:
			conditions.append(signed_amount.abs().lte(self.pr.max_amount))
		for dim in self.dimensions:
			val = self.pr.get(dim.fieldname)
			if val and frappe.db.has_column("Journal Entry Account", dim.fieldname):
				conditions.append(jea[dim.fieldname] == val)

		query = (
			qb.from_(je)
			.inner_join(jea)
			.on(jea.parent == je.name)
			.inner_join(account_dt)
			.on(account_dt.name == jea.account)
			.select(
				ConstantColumn("Journal Entry").as_("voucher_type"),
				je.name.as_("voucher_no"),
				jea.name.as_("voucher_row"),
				jea.account,
				account_dt.account_type,
				jea.party_type,
				jea.party,
				je.posting_date,
				ConstantColumn(None).as_("due_date"),
				signed_amount.as_("outstanding_amount"),
				signed_amount.as_("amount"),
				jea.account_currency.as_("currency"),
				jea.exchange_rate,
				jea.is_advance,
				ConstantColumn(0).as_("is_return"),
				jea.cost_center,
				je.remark.as_("remarks"),
			)
			.where(Criterion.all(conditions))
			.orderby(je.posting_date)
		)

		raw = query.run(as_dict=True)
		return [frappe._dict(r) for r in raw]

	def _enrich_voucher_metadata(self, rows):
		"""Adds is_return, is_advance, and exchange_rate etc. to the PLE rows"""
		by_type: dict[str, set[str]] = {}
		for r in rows:
			if r.voucher_type in ("Sales Invoice", "Purchase Invoice", "Payment Entry"):
				by_type.setdefault(r.voucher_type, set()).add(r.voucher_no)

		# is_return + conversion_rate for SI/PI
		invoice_meta: dict[tuple[str, str], tuple[int, float]] = {}
		for vtype in ("Sales Invoice", "Purchase Invoice"):
			if vtype in by_type:
				for v in frappe.db.get_all(
					vtype,
					filters={"name": ("in", list(by_type[vtype]))},
					fields=["name", "is_return", "conversion_rate"],
				):
					invoice_meta[(vtype, v.name)] = (
						int(bool(v.is_return)),
						flt(v.conversion_rate) or 1.0,
					)

		# Advance flag + per-PE exchange_rate
		# PE Receive uses source_exchange_rate (party account currency), PE Pay uses target_exchange_rate.
		pe_meta: dict[str, tuple[int, float]] = {}
		if "Payment Entry" in by_type:
			for p in frappe.db.get_all(
				"Payment Entry",
				filters={"name": ("in", list(by_type["Payment Entry"]))},
				fields=[
					"name",
					"payment_type",
					"book_advance_payments_in_separate_party_account",
					"source_exchange_rate",
					"target_exchange_rate",
				],
			):
				exch = p.source_exchange_rate if p.payment_type == "Receive" else p.target_exchange_rate
				pe_meta[p.name] = (
					int(bool(p.book_advance_payments_in_separate_party_account)),
					flt(exch) or 1.0,
				)

		for r in rows:
			if r.voucher_type in ("Sales Invoice", "Purchase Invoice"):
				is_ret, exch = invoice_meta.get((r.voucher_type, r.voucher_no), (0, 1.0))
				r.is_return = is_ret
				r.is_advance = 0
				r.exchange_rate = exch
			elif r.voucher_type == "Payment Entry":
				adv, exch = pe_meta.get(r.voucher_no, (0, 1.0))
				r.is_return = 0
				r.is_advance = adv
				r.exchange_rate = exch
			elif r.voucher_type == "Journal Entry":
				# JE rows already enriched in _query_je_outstanding.
				continue
			else:
				r.is_return = 0
				r.is_advance = 0
				r.exchange_rate = 1.0


class PaymentReconciliation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.payment_reconciliation_allocation.payment_reconciliation_allocation import (
			PaymentReconciliationAllocation,
		)
		from erpnext.accounts.doctype.payment_reconciliation_entry.payment_reconciliation_entry import (
			PaymentReconciliationEntry,
		)

		allocation: DF.Table[PaymentReconciliationAllocation]
		bank_cash_account: DF.Link | None
		company: DF.Link
		cost_center: DF.Link | None
		currency: DF.Link | None
		currency_filter: DF.Link | None
		default_advance_account: DF.Link | None
		difference_amount: DF.Currency
		from_date: DF.Date | None
		max_amount: DF.Currency
		min_amount: DF.Currency
		party: DF.DynamicLink
		party_type: DF.Link
		project: DF.Link | None
		receivable_payable_account: DF.Link | None
		to_date: DF.Date | None
		to_pay: DF.Table[PaymentReconciliationEntry]
		to_pay_limit: DF.Int
		to_receive: DF.Table[PaymentReconciliationEntry]
		to_receive_limit: DF.Int
		total_invoice_amount: DF.Currency
		total_payment_amount: DF.Currency
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.common_filter_conditions = []
		self.accounting_dimension_filter_conditions = []
		self.ple_posting_date_filter = []
		self.dimensions = get_dimensions(with_cost_center_and_project=True)[0]

	@property
	def user_permissions(self):
		return get_user_permissions(frappe.session.user)

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
				"currency_filter": None,
				"from_date": None,
				"to_date": None,
				"min_amount": None,
				"max_amount": None,
				"to_receive_limit": 50,
				"to_pay_limit": 50,
				"cost_center": None,
				"project": None,
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
		"""Populate `to_receive` and `to_pay` from a single PLE-based query.

		Pipeline:
		    OpenBalanceFetcher.fetch()  →  list[OpenBalance]  (one row per voucher position)
		    Classifier.classify(...)    →  routes each row to to_receive or to_pay
		    _apply_post_filters()       →  per-table voucher_no LIKE + row caps
		"""
		self.set("to_receive", [])
		self.set("to_pay", [])
		self.check_mandatory_to_fetch()

		open_balances = OpenBalanceFetcher(self).fetch()
		self._classify_and_populate(open_balances)
		self._apply_post_filters()

	def _classify_and_populate(self, open_balances):
		open_balances.sort(key=lambda r: r.get("posting_date") or getdate(nowdate()))

		for row in open_balances:
			signed = flt(row.get("outstanding_amount"))
			if not signed:
				continue
			target = Classifier.classify(row.get("account_type"), signed)
			table = "to_receive" if target == Classifier.RECEIVABLE else "to_pay"

			self.append(
				table,
				{
					**row,
					"amount": abs(signed),
					"outstanding_amount": abs(signed),
					"exchange_rate": flt(row.get("exchange_rate")) or 1.0,
				},
			)

	def _apply_post_filters(self):
		if self.to_receive_limit and len(self.to_receive) > self.to_receive_limit:
			self.to_receive = self.to_receive[: self.to_receive_limit]
		if self.to_pay_limit and len(self.to_pay) > self.to_pay_limit:
			self.to_pay = self.to_pay[: self.to_pay_limit]

	def get_difference_amount(self, payment_entry, invoice, allocated_amount):
		party_account_defaults = frappe.get_cached_value(
			"Account", self.receivable_payable_account, ["account_type", "account_currency"], as_dict=True
		)
		allocated_amount_precision = get_field_precision(
			frappe.get_meta("Payment Reconciliation Allocation").get_field("allocated_amount")
		)
		difference_amount_precision = get_field_precision(
			frappe.get_meta("Payment Reconciliation Allocation").get_field("difference_amount")
		)
		difference_amount = 0
		if party_account_defaults.get("account_currency") != frappe.get_cached_value(
			"Company", self.company, "default_currency"
		):
			if invoice.get("exchange_rate") and payment_entry.get("exchange_rate", 1) != invoice.get(
				"exchange_rate", 1
			):
				allocated_amount_in_ref_rate = flt(
					payment_entry.get("exchange_rate", 1) * flt(allocated_amount, allocated_amount_precision),
					difference_amount_precision,
				)
				allocated_amount_in_inv_rate = flt(
					invoice.get("exchange_rate", 1) * flt(allocated_amount, allocated_amount_precision),
					difference_amount_precision,
				)

				# Added If clause to handle return Adhoc payments for account type holders ("Payable")
				if party_account_defaults.get("account_type") in ("Payable") and invoice.get(
					"invoice_type"
				) in ["Payment Entry", "Journal Entry"]:
					difference_amount = allocated_amount_in_inv_rate - allocated_amount_in_ref_rate
				else:
					difference_amount = allocated_amount_in_ref_rate - allocated_amount_in_inv_rate

		return difference_amount

	@frappe.whitelist()
	def calculate_difference_on_allocation_change(
		self, payment_entry: list, invoice: list, allocated_amount: float
	):
		invoice_exchange_map = self.get_invoice_exchange_map(invoice, payment_entry)
		invoice[0]["exchange_rate"] = invoice_exchange_map.get(invoice[0].get("invoice_number"))
		if payment_entry[0].get("reference_type") in ["Sales Invoice", "Purchase Invoice"]:
			payment_entry[0]["exchange_rate"] = invoice_exchange_map.get(
				payment_entry[0].get("reference_name")
			)

		new_difference_amount = self.get_difference_amount(payment_entry[0], invoice[0], allocated_amount)
		return new_difference_amount

	@frappe.whitelist()
	def allocate_entries(self, args: dict):
		self.validate_entries()

		exc_gain_loss_posting_date = frappe.db.get_single_value(
			"Accounts Settings", "exchange_gain_loss_posting_date", cache=True
		)
		invoice_exchange_map = self.get_invoice_exchange_map(args.get("invoices"), args.get("payments"))
		account_currency = frappe.get_cached_value(
			"Account", self.receivable_payable_account, "account_currency"
		)
		allocated_amount_precision = get_field_precision(
			frappe.get_meta("Payment Reconciliation Allocation").get_field("allocated_amount"),
			currency=account_currency,
		)

		entries = []
		for pay in args.get("payments"):
			pay.update({"unreconciled_amount": pay.get("amount")})
			for inv in args.get("invoices"):
				if pay.get("amount") >= inv.get("outstanding_amount"):
					res = self.get_allocated_entry(pay, inv, inv["outstanding_amount"])
					pay["amount"] = flt(
						flt(pay.get("amount")) - flt(inv.get("outstanding_amount")),
						allocated_amount_precision,
					)
					inv["outstanding_amount"] = 0
				else:
					res = self.get_allocated_entry(pay, inv, pay["amount"])
					inv["outstanding_amount"] = flt(
						flt(inv.get("outstanding_amount")) - flt(pay.get("amount")),
						allocated_amount_precision,
					)
					pay["amount"] = 0

				inv["exchange_rate"] = invoice_exchange_map.get(inv.get("invoice_number"))
				if pay.get("reference_type") in ["Sales Invoice", "Purchase Invoice"]:
					pay["exchange_rate"] = invoice_exchange_map.get(pay.get("reference_name"))

				res.difference_amount = self.get_difference_amount(pay, inv, res["allocated_amount"])
				is_gain = (
					res.difference_amount > 0 if self.party_type == "Customer" else res.difference_amount < 0
				)
				res.difference_account = get_exchange_gain_loss_account(self.company, is_gain)
				res.exchange_rate = inv.get("exchange_rate")
				res.update({"gain_loss_posting_date": pay.get("posting_date")})
				if not pay.get("is_advance"):
					if exc_gain_loss_posting_date == "Invoice":
						res.update({"gain_loss_posting_date": inv.get("invoice_date")})
					elif exc_gain_loss_posting_date == "Reconciliation Date":
						res.update({"gain_loss_posting_date": nowdate()})

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

	def update_dimension_values_in_allocated_entries(self, res):
		for x in self.dimensions:
			dimension = x.fieldname
			if self.get(dimension):
				res[dimension] = self.get(dimension)
		return res

	def get_allocated_entry(self, pay, inv, allocated_amount):
		res = frappe._dict(
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

		res = self.update_dimension_values_in_allocated_entries(res)
		return res

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
			reconcile_against_document(entry_list, skip_ref_details_update_for_pe, self.dimensions)

		if dr_or_cr_notes:
			reconcile_dr_cr_note(dr_or_cr_notes, self.company, self.dimensions)

	@frappe.whitelist()
	def reconcile(self):
		if frappe.get_single_value("Accounts Settings", "auto_reconcile_payments"):
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
					_(
						"A Reconciliation Job {0} is running for the same filters. Cannot reconcile now"
					).format(get_link_to_form("Auto Reconcile", running_doc))
				)
				return

		self.validate_allocation()
		self.reconcile_allocations()
		msgprint(_("Successfully Reconciled"))

		self.get_unreconciled_entries()

	def get_payment_details(self, row, dr_or_cr):
		payment_details = frappe._dict(
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
				"debit_or_credit_note_posting_date": row.get("debit_or_credit_note_posting_date"),
				"cost_center": row.get("cost_center"),
			}
		)

		for x in self.dimensions:
			if row.get(x.fieldname):
				payment_details[x.fieldname] = row.get(x.fieldname)

		return payment_details

	def check_mandatory_to_fetch(self):
		for fieldname in ["company", "party_type", "party"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_translated_label(fieldname)))

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

		journals = [d.get("invoice_number") for d in invoices if d.get("invoice_type") == "Journal Entry"]
		journals.extend(
			[d.get("reference_name") for d in payments if d.get("reference_type") == "Journal Entry"]
		)
		if journals:
			journals = list(set(journals))
			journals_map = frappe._dict(
				frappe.db.get_all(
					"Journal Entry Account",
					filters={
						"parent": ("in", journals),
						"account": ("in", [self.receivable_payable_account]),
						"party_type": self.party_type,
						"party": self.party,
					},
					fields=[
						"parent as name",
						"exchange_rate",
					],
					as_list=1,
				)
			)
			invoice_exchange_map.update(journals_map)

		payment_entries = [
			d.get("invoice_number") for d in invoices if d.get("invoice_type") == "Payment Entry"
		]
		payment_entries.extend(
			[d.get("reference_name") for d in payments if d.get("reference_type") == "Payment Entry"]
		)
		if payment_entries:
			pe = frappe.qb.DocType("Payment Entry")
			query = (
				frappe.qb.from_(pe)
				.select(
					pe.name,
					Case()
					.when(pe.payment_type == "Receive", pe.source_exchange_rate)
					.else_(pe.target_exchange_rate)
					.as_("exchange_rate"),
				)
				.where(pe.name.isin(payment_entries))
			)
			payment_entries = query.run(as_list=1)
			invoice_exchange_map.update(payment_entries)

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


def reconcile_dr_cr_note(dr_cr_notes, company, active_dimensions=None):
	allocated_amount_precision = get_field_precision(
		frappe.get_meta("Payment Reconciliation Allocation").get_field("allocated_amount")
	)
	for inv in dr_cr_notes:
		if (
			flt(
				abs(frappe.db.get_value(inv.voucher_type, inv.voucher_no, "outstanding_amount"))
				- inv.allocated_amount,
				allocated_amount_precision,
			)
			< 0
		):
			frappe.throw(
				_("{0} has been modified after you pulled it. Please pull it again.").format(inv.voucher_type)
			)

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
				"posting_date": inv.get("debit_or_credit_note_posting_date") or today(),
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
						"exchange_rate": inv.exchange_rate,
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} against {inv.against_voucher}",
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
						"exchange_rate": inv.exchange_rate,
						"user_remark": f"{fmt_money(flt(inv.allocated_amount), currency=company_currency)} from {inv.voucher_no}",
					},
				],
			}
		)

		# Credit Note(JE) will inherit the same dimension values as payment
		dimensions_dict = frappe._dict()
		if active_dimensions:
			for dim in active_dimensions:
				dimensions_dict[dim.fieldname] = inv.get(dim.fieldname)

		jv.accounts[0].update(dimensions_dict)
		jv.accounts[1].update(dimensions_dict)

		jv.flags.ignore_mandatory = True
		jv.flags.ignore_exchange_rate = True
		jv.remark = None
		jv.flags.skip_remarks_creation = True
		jv.is_system_generated = True
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
				inv.difference_posting_date,
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
				dimensions_dict,
			)


@erpnext.allow_regional
def adjust_allocations_for_taxes(doc):
	pass


@frappe.whitelist()
def get_queries_for_dimension_filters(company: str | None = None):
	dimensions_with_filters = []
	for d in get_dimensions()[0]:
		filters = {}
		meta = frappe.get_meta(d.document_type)
		if meta.has_field("company") and company:
			filters.update({"company": company})

		if meta.is_tree:
			filters.update({"is_group": 0})

		dimensions_with_filters.append({"fieldname": d.fieldname, "filters": filters})

	return dimensions_with_filters


@frappe.whitelist()
def is_auto_process_enabled():
	return frappe.get_single_value("Accounts Settings", "auto_reconcile_payments")
