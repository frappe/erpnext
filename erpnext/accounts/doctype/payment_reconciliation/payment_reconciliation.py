# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.model.document import Document
from frappe.model.meta import get_field_precision
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions
from frappe.query_builder import Case, Criterion
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import IfNull
from frappe.utils import flt, get_link_to_form, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation import (
	is_any_doc_running,
)
from erpnext.accounts.services.exchange_gain_loss import get_exchange_gain_loss_account
from erpnext.accounts.utils import (
	CROSS_ACCOUNT_BRIDGE_VOUCHER_TYPE,
	QueryPaymentLedger,
	get_reconciliation_effect_date,
	reconcile_against_document,
)

RECEIVABLE = "Receivable"
PAYABLE = "Payable"
INVOICE_DOCTYPES = ("Sales Invoice", "Purchase Invoice")


def payment_side(party_type) -> str:
	"""Table holding the party's own payments: `to_pay` for receivable parties, else `to_receive`."""
	return "to_pay" if erpnext.get_party_account_type(party_type) == RECEIVABLE else "to_receive"


def amount_precision(currency) -> int:
	"""Decimal places for amounts in this currency."""
	df = frappe.get_meta("Payment Reconciliation Allocation").get_field("allocated_amount")
	return get_field_precision(df, currency=currency)


def is_cash_pair(recv, pay) -> bool:
	"""Neither side is an invoice: a payment settled against a refund."""
	return recv.voucher_type not in INVOICE_DOCTYPES and pay.voucher_type not in INVOICE_DOCTYPES


def classify(account_type: str, amount: float) -> str:
	"""Sort a PLE row into Receivable or Payable by `(account_type, sign)`.

	Receivable+positive or Payable+negative → Receivable; the inverse → Payable.
	"""
	if account_type not in (RECEIVABLE, PAYABLE):
		frappe.throw(_("Unsupported account type {0}").format(account_type))
	if not amount:
		frappe.throw(_("Cannot classify entry with zero amount."))
	if (amount > 0) == (account_type == RECEIVABLE):
		return RECEIVABLE
	return PAYABLE


def _fifo_key(r):
	"""Sort OpenBalance rows: oldest-first, with PE-Reference rows BEFORE
	their PE-self row (PR-E: drain bound PO/SO advances before free balance)."""
	return (
		r.get("posting_date") or getdate(nowdate()),
		r.get("voucher_no") or "",
		0 if r.get("reference_name") else 1,
		r.get("reference_name") or "",
		r.get("voucher_row") or "",
	)


def pick_voucher_side(recv, pay, party_type=None) -> str | None:
	"""Return `"receive"`/`"pay"` — the side owning the `voucher_no` slot in
	`reconcile_against_document` — or `None` if neither side has a mutable voucher
	(pair must be bridged). Priority: PE on the party's natural payment side
	(see `payment_side`), else a JE (`to_pay` preferred).
	"""
	natural = payment_side(party_type).removeprefix("to_")
	side_row = {"receive": recv, "pay": pay}

	if side_row[natural].voucher_type == "Payment Entry":
		return natural
	# `to_pay` preferred preserves legacy split order (JExJE same-account isolation).
	if pay.voucher_type == "Journal Entry":
		return "pay"
	if recv.voucher_type == "Journal Entry":
		return "receive"
	return None


class DimensionFilter:
	"""Dimension conditions from form values and the user's permissions."""

	def __init__(self, pr):
		self.dimensions = pr.dimensions
		self.values = {dim.fieldname: pr.get(dim.fieldname) for dim in pr.dimensions}
		self.user_permissions = get_user_permissions(frappe.session.user)
		self.strict = frappe.get_system_settings("apply_strict_user_permissions")

	def conditions(self, table, doctype):
		conditions = []
		for dim in self.dimensions:
			if not frappe.db.has_column(doctype, dim.fieldname):
				continue
			allowed = get_allowed_docs_for_doctype(self.user_permissions.get(dim.document_type, []), doctype)
			if value := self.values.get(dim.fieldname):
				self._check_allowed(dim.document_type, value, allowed)
				conditions.append(table[dim.fieldname] == value)
			elif allowed:
				conditions.append(self._allowed_condition(table[dim.fieldname], allowed))
		return conditions

	def _check_allowed(self, document_type, value, allowed):
		if allowed and value not in allowed:
			frappe.throw(
				_("You do not have enough permission to access {0}: {1}").format(_(document_type), value),
				frappe.PermissionError,
			)

	def _allowed_condition(self, field, allowed):
		# strict mode hides untagged rows too
		if self.strict:
			return field.isin(allowed)
		return (IfNull(field, "") == "") | field.isin(allowed)


class OpenBalanceFetcher:
	"""
	Pipeline:
	1. fetch PLE rows + JE rows for all party accounts
	2. split each PE's PLE row into a free slice + one slice per PO/SO reference
	3. enrich with is_return / is_advance / exchange_rate
	4. filter by amount (min/max + zero-drop)
	"""

	def __init__(self, pr, vouchers=None):
		self.pr = pr
		self.company = pr.company
		self.party_type = pr.party_type
		self.party = pr.party
		self.dimension_filter = DimensionFilter(pr)
		self.vouchers = vouchers

	def fetch(self):
		accounts = self._get_party_accounts()
		if not accounts:
			return []

		rows = self._query_ple_outstanding(accounts) + self._query_je_outstanding(accounts)
		if not rows:
			return []

		rows = self._split_pe_by_references(rows)
		self._enrich_voucher_metadata(rows)
		return [r for r in rows if self._passes_amount_filter(r) and self._in_date_range(r)]

	def _get_party_accounts(self):
		"""Single-account when `receivable_payable_account` is set; else all
		party accounts from PLE (split by natural / advance root_type)."""
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
			natural_root = "Asset" if payment_side(self.party_type) == "to_pay" else "Liability"
			normal_accounts = rows.where(account.root_type == natural_root).run(as_dict=True)
			accounts.update([r.account for r in normal_accounts])

		if self.pr.default_advance_account:
			accounts.add(self.pr.default_advance_account)
		else:
			opposite_root = "Liability" if payment_side(self.party_type) == "to_pay" else "Asset"
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

		dimension_filter = self.dimension_filter.conditions(ple, "Payment Ledger Entry")
		# payments must also pass Payment Entry's own permissions
		if pe_only := self.dimension_filter.conditions(ple, "Payment Entry"):
			dimension_filter.append((ple.voucher_type != "Payment Entry") | Criterion.all(pe_only))

		return common_filter, posting_date_filter, dimension_filter

	def _query_ple_outstanding(self, accounts):
		common_filter, posting_date_filter, dimension_filter = self._build_filters(accounts)
		ple = qb.DocType("Payment Ledger Entry")
		common_filter.append(ple.against_voucher_type != "Journal Entry")

		vouchers = None
		if self.vouchers is not None:
			vouchers = [
				frappe._dict(voucher_type=vtype, voucher_no=name)
				for vtype, name in self.vouchers
				if vtype != "Journal Entry"
			]
			if not vouchers:
				return []

		ple_query = QueryPaymentLedger()
		raw = ple_query.get_voucher_outstandings(
			vouchers=vouchers,
			common_filter=common_filter,
			posting_date=posting_date_filter,
			accounting_dimensions=dimension_filter,
			exclude_zero_outstanding=True,
		)
		return [self._project_ple_row(frappe._dict(r)) for r in raw]

	def _project_ple_row(self, r):
		r.outstanding_amount = flt(r.outstanding_in_account_currency)
		r.amount = flt(r.invoice_amount_in_account_currency)
		r.voucher_row = None  # PLE rows are voucher-level, not row-level
		return r

	def _passes_amount_filter(self, r):
		signed = flt(r.get("outstanding_amount"))
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

	def _in_date_range(self, r):
		# PE rows carry the PE's own date, the ledger filter can't see it
		posting_date = getdate(r.get("posting_date"))
		if self.pr.from_date and posting_date < getdate(self.pr.from_date):
			return False
		return not (self.pr.to_date and posting_date > getdate(self.pr.to_date))

	def _split_pe_by_references(self, rows):
		"""Split a PE's single PLE row into a free slice (voucher_row=None) plus
		one bound slice per submitted PO/SO reference (voucher_row=PER.name).

		PLE is authoritative for a PE's total open balance — it nets invoice and
		PE↔PE / JE settlements — but it never records PO/SO references (those live
		only in `Payment Entry Reference`), so it over-states the free balance by
		exactly the bound amount. A bound slice's `voucher_row` lets the Allocator
		pass it as `voucher_detail_no` to `update_reference_in_payment_entry` to
		re-point that advance onto an invoice.
		"""
		pe_names = {r.voucher_no for r in rows if r.voucher_type == "Payment Entry"}
		if not pe_names:
			return rows

		refs_by_pe: dict[str, list] = {}
		for ref in self._fetch_po_so_references(pe_names):
			refs_by_pe.setdefault(ref.pe_name, []).append(ref)

		split_rows = []
		for r in rows:
			refs = refs_by_pe.get(r.voucher_no) if r.voucher_type == "Payment Entry" else None
			if not refs:
				split_rows.append(r)
				continue

			sign = -1 if flt(r.outstanding_amount) < 0 else 1

			precision = amount_precision(r.currency)
			bound_total = sum(flt(ref.allocated_amount) for ref in refs)
			free = frappe._dict(r.copy())
			free.outstanding_amount = flt(flt(r.outstanding_amount) - sign * bound_total, precision)
			free.amount = free.outstanding_amount
			free.reference_doctype = None
			free.reference_name = None
			split_rows.append(free)

			for ref in refs:
				amt = sign * flt(ref.allocated_amount)
				slice_row = frappe._dict(r.copy())
				slice_row.voucher_row = ref.per_name
				slice_row.outstanding_amount = amt
				slice_row.amount = amt
				slice_row.reference_doctype = ref.reference_doctype
				slice_row.reference_name = ref.reference_name
				split_rows.append(slice_row)

		return split_rows

	def _fetch_po_so_references(self, pe_names):
		"""Submitted PO/SO advance references — the one allocation PLE never records."""
		if not pe_names:
			return []
		per = qb.DocType("Payment Entry Reference")
		return (
			qb.from_(per)
			.select(
				per.name.as_("per_name"),
				per.parent.as_("pe_name"),
				per.allocated_amount,
				per.reference_doctype,
				per.reference_name,
			)
			.where(
				per.parent.isin(list(pe_names))
				& (per.docstatus == 1)
				& per.reference_doctype.isin(("Sales Order", "Purchase Order"))
				& (per.allocated_amount > 0)
			)
			.run(as_dict=True)
		)

	def _query_je_outstanding(self, accounts):
		je = qb.DocType("Journal Entry")
		jea = qb.DocType("Journal Entry Account")
		account_dt = qb.DocType("Account")

		# positive = balance in the line account's natural direction, as in the ledger
		signed_amount = (
			Case()
			.when(
				account_dt.account_type == RECEIVABLE,
				jea.debit_in_account_currency - jea.credit_in_account_currency,
			)
			.else_(jea.credit_in_account_currency - jea.debit_in_account_currency)
		)

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
			signed_amount != 0,
		]
		if self.pr.from_date:
			conditions.append(je.posting_date.gte(self.pr.from_date))
		if self.pr.to_date:
			conditions.append(je.posting_date.lte(self.pr.to_date))
		if self.pr.currency_filter:
			conditions.append(jea.account_currency == self.pr.currency_filter)
		if self.vouchers is not None:
			names = [name for vtype, name in self.vouchers if vtype == "Journal Entry"]
			if not names:
				return []
			conditions.append(je.name.isin(names))
		conditions += self.dimension_filter.conditions(jea, "Journal Entry Account")

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
			.orderby(je.name)
			.orderby(jea.idx)
		)

		raw = query.run(as_dict=True)
		rows = [frappe._dict(r) for r in raw]

		# Net JEA balance against PE-side PLE allocations. A PE settling a JE writes
		# `(voucher=PE, against=JE)` rather than touching the JEA, so signed_amount
		# nets to zero only after applying these allocations.
		if rows:
			je_names = list({r.voucher_no for r in rows})
			ple_dt = qb.DocType("Payment Ledger Entry")
			from frappe.query_builder.functions import Sum

			alloc_rows = (
				qb.from_(ple_dt)
				.select(
					ple_dt.against_voucher_no.as_("je_name"),
					ple_dt.account.as_("account"),
					Sum(ple_dt.amount_in_account_currency).as_("allocated"),
				)
				.where(
					(ple_dt.against_voucher_type == "Journal Entry")
					& ple_dt.against_voucher_no.isin(je_names)
					& (ple_dt.voucher_no != ple_dt.against_voucher_no)  # exclude JE-self
					& (ple_dt.delinked == 0)
					& (ple_dt.company == self.company)
					& (ple_dt.party_type == self.party_type)
					& (ple_dt.party == self.party)
				)
				.groupby(ple_dt.against_voucher_no, ple_dt.account)
				.run(as_dict=True)
			)
			alloc_by_key = {(a.je_name, a.account): flt(a.allocated) for a in alloc_rows}

			# Self-settlement: a JE reconciled against itself writes a split leg
			# referencing the same JE. The base query excludes it and PLE netting
			# skips JE-self, so net those legs into the base leg here.
			self_settle_rows = (
				qb.from_(jea)
				.inner_join(je)
				.on(jea.parent == je.name)
				.inner_join(account_dt)
				.on(account_dt.name == jea.account)
				.select(jea.parent.as_("je_name"), jea.account, Sum(signed_amount).as_("settled"))
				.where(
					(je.docstatus == 1)
					& jea.parent.isin(je_names)
					& (jea.reference_type == "Journal Entry")
					& (jea.reference_name == jea.parent)
					& (jea.party_type == self.party_type)
					& (jea.party == self.party)
				)
				.groupby(jea.parent, jea.account)
				.run(as_dict=True)
			)
			for s in self_settle_rows:
				key = (s.je_name, s.account)
				alloc_by_key[key] = alloc_by_key.get(key, 0) + flt(s.settled)

			self._apply_settlements(rows, alloc_by_key)
			rows = [r for r in rows if r.outstanding_amount]

		return rows

	@staticmethod
	def _apply_settlements(rows, settled):
		"""Settlements are known per journal and account, not per line: spend each on
		the lines of the opposite sign, oldest first, never pushing a line past zero."""
		for r in rows:
			key = (r.voucher_no, r.account)
			left = settled.get(key, 0)
			balance = flt(r.outstanding_amount)
			if left and (left > 0) != (balance > 0):
				used = min(abs(left), abs(balance)) * (1 if left > 0 else -1)
				settled[key] = left - used
				balance += used
			r.outstanding_amount = r.amount = flt(balance, amount_precision(r.currency))

	def _enrich_voucher_metadata(self, rows):
		"""Adds is_return, is_advance, and exchange_rate etc. to the PLE rows"""
		by_type: dict[str, set[str]] = {}
		for r in rows:
			if r.voucher_type in ("Sales Invoice", "Purchase Invoice", "Payment Entry"):
				by_type.setdefault(r.voucher_type, set()).add(r.voucher_no)

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

		# PE Receive uses source_exchange_rate; PE Pay uses target_exchange_rate.
		pe_meta: dict[str, tuple] = {}
		if "Payment Entry" in by_type:
			for p in frappe.db.get_all(
				"Payment Entry",
				filters={"name": ("in", list(by_type["Payment Entry"]))},
				fields=[
					"name",
					"payment_type",
					"posting_date",
					"book_advance_payments_in_separate_party_account",
					"source_exchange_rate",
					"target_exchange_rate",
				],
			):
				exch = p.source_exchange_rate if p.payment_type == "Receive" else p.target_exchange_rate
				pe_meta[p.name] = (
					int(bool(p.book_advance_payments_in_separate_party_account)),
					flt(exch) or 1.0,
					p.posting_date,
				)

		for r in rows:
			if r.voucher_type in ("Sales Invoice", "Purchase Invoice"):
				is_ret, exch = invoice_meta.get((r.voucher_type, r.voucher_no), (0, 1.0))
				r.is_return = is_ret
				r.is_advance = 0
				r.exchange_rate = exch
			elif r.voucher_type == "Payment Entry":
				if r.voucher_no in pe_meta:
					adv, exch, posting_date = pe_meta[r.voucher_no]
					r.is_return = 0
					r.is_advance = adv
					r.exchange_rate = exch
					# later reconcile-effect ledger rows move the ledger's date, the PE's own doesn't
					r.posting_date = posting_date
			elif r.voucher_type == "Journal Entry":
				continue  # already enriched in _query_je_outstanding
			else:
				r.is_return = 0
				r.is_advance = 0
				r.exchange_rate = 1.0


class Allocator:
	"""Currency-bucketed FIFO allocator.

	Walks `to_receive` oldest-first, consuming `to_pay` oldest-first within
	each currency bucket. Never crosses currencies. Pure transformation —
	`PaymentReconciliation.allocate_entries` clears `self.allocation` and
	appends each emitted dict.
	"""

	def __init__(self, pr, to_receive=None, to_pay=None):
		# Overrides let the form pass user-selected rows; default to full tables.
		self.pr = pr
		self.company = pr.company
		self.party_type = pr.party_type
		self.to_receive = to_receive if to_receive is not None else list(pr.get("to_receive") or [])
		self.to_pay = to_pay if to_pay is not None else list(pr.get("to_pay") or [])
		self.exc_gain_loss_posting_date_setting = frappe.db.get_single_value(
			"Accounts Settings", "exchange_gain_loss_posting_date", cache=True
		)
		self.company_currency = frappe.get_cached_value("Company", pr.company, "default_currency")
		self.diff_precision = get_field_precision(
			frappe.get_meta("Payment Reconciliation Allocation").get_field("difference_amount")
		)

	def allocate(self):
		buckets_recv = self._bucket_by_currency(self.to_receive)
		buckets_pay = self._bucket_by_currency(self.to_pay)

		allocations = []
		for currency, recv_rows in buckets_recv.items():
			pay_rows = buckets_pay.get(currency, [])
			if not pay_rows:
				continue
			recv_rows = sorted(recv_rows, key=_fifo_key)
			pay_rows = sorted(pay_rows, key=_fifo_key)
			allocations.extend(self._walk(recv_rows, pay_rows))

		return allocations

	@staticmethod
	def _bucket_by_currency(rows):
		buckets = {}
		for r in rows:
			buckets.setdefault(r.currency, []).append(r)
		return buckets

	def _walk(self, receivables, payables):
		allocations = []
		recv_remaining = [flt(r.outstanding_amount) for r in receivables]
		pay_remaining = [flt(p.outstanding_amount) for p in payables]
		precision = amount_precision(receivables[0].currency)

		# Drain same-account counterparties first, then cross-account. Avoids minting
		# a bridge JE when a same-account match exists. FIFO preserved within each tier.
		for same_account_only in (True, False):
			for i, recv in enumerate(receivables):
				if recv_remaining[i] <= 0:
					continue
				for j, pay in enumerate(payables):
					if recv_remaining[i] <= 0:
						break
					if pay_remaining[j] <= 0:
						continue
					if (pay.account == recv.account) != same_account_only:
						continue
					amt = min(recv_remaining[i], pay_remaining[j])
					if amt > 0:
						allocations.append(self._make_allocation(recv, payables[j], amt))
						# round so float leftovers don't make tiny extra rows
						recv_remaining[i] = flt(recv_remaining[i] - amt, precision)
						pay_remaining[j] = flt(pay_remaining[j] - amt, precision)

		return allocations

	def _difference_account(self, recv, pay, difference_amount):
		if not difference_amount:
			return None
		# same sign rule as `_fx_difference`: only supplier invoice pairs read inverted
		inverted = recv.account_type == PAYABLE and not is_cash_pair(recv, pay)
		is_gain = difference_amount < 0 if inverted else difference_amount > 0
		return get_exchange_gain_loss_account(self.company, is_gain)

	def _make_allocation(self, recv, pay, allocated_amount):
		difference_amount = self._fx_difference(recv, pay, allocated_amount)
		payment, invoice = (pay, recv) if payment_side(self.party_type) == "to_pay" else (recv, pay)
		gain_loss_posting_date = self._gain_loss_posting_date(payment, invoice)
		is_cross_account = recv.account != pay.account

		# Pairs with no mutable voucher are bridged at reconcile time; for preview
		# metadata fall back to the party's payment side.
		side = pick_voucher_side(recv, pay, self.party_type)
		if side is None:
			side = payment_side(self.party_type).removeprefix("to_")
		mutated_row = pay if side == "pay" else recv
		referenced_row = recv if side == "pay" else pay

		row = frappe._dict(
			{
				"to_receive_voucher_type": recv.voucher_type,
				"to_receive_voucher_no": recv.voucher_no,
				"to_receive_voucher_row": recv.voucher_row,
				"to_receive_account": recv.account,
				"to_receive_party_type": recv.party_type,
				"to_receive_party": recv.party,
				"to_pay_voucher_type": pay.voucher_type,
				"to_pay_voucher_no": pay.voucher_no,
				"to_pay_voucher_row": pay.voucher_row,
				"to_pay_account": pay.account,
				"to_pay_party_type": pay.party_type,
				"to_pay_party": pay.party,
				"allocated_amount": allocated_amount,
				"unreconciled_amount": flt(mutated_row.outstanding_amount),
				"amount": flt(mutated_row.amount or mutated_row.outstanding_amount),
				"is_advance": 1 if (pay.is_advance or recv.is_advance) else 0,
				"is_cross_account": 1 if is_cross_account else 0,
				# `exchange_rate` must be the AGAINST side's rate; the voucher-side rate
				# would zero out the FX gain/loss and skip the FX JE.
				"difference_amount": difference_amount,
				"difference_account": self._difference_account(recv, pay, difference_amount),
				"gain_loss_posting_date": gain_loss_posting_date,
				"exchange_rate": flt(referenced_row.exchange_rate) or 1.0,
				# each side's own rate, so a bridge can book FX on the right leg
				"to_receive_exchange_rate": flt(recv.exchange_rate) or 1.0,
				"to_pay_exchange_rate": flt(pay.exchange_rate) or 1.0,
				"currency": mutated_row.currency,
				"cost_center": payment.cost_center or invoice.cost_center,
			}
		)

		# TODO: evaluate if true - why are these not fetched in the original fetcher?
		# Should it not be updated from original entries?
		for dim in self.pr.dimensions:
			val = self.pr.get(dim.fieldname)
			if val:
				row[dim.fieldname] = val

		return row

	def _fx_difference(self, recv, pay, allocated_amount):
		"""FX gain/loss when the two sides booked at different exchange rates.

		Sign convention matches `Payment Entry Reference.exchange_gain_loss`.
		"""
		recv_rate = flt(recv.exchange_rate) or 1.0
		pay_rate = flt(pay.exchange_rate) or 1.0
		if recv_rate == pay_rate:
			return 0.0
		if recv.currency == self.company_currency and pay.currency == self.company_currency:
			return 0.0

		amt_in_pay_rate = flt(pay_rate * flt(allocated_amount), self.diff_precision)
		amt_in_recv_rate = flt(recv_rate * flt(allocated_amount), self.diff_precision)

		# Cash-event pair (no invoice side): Receivable-style formula for both parties.
		if is_cash_pair(recv, pay):
			return amt_in_pay_rate - amt_in_recv_rate

		# SI/PI ↔ PE: invert sign for Payable accounts (Supplier).
		if recv.account_type == PAYABLE:
			return amt_in_recv_rate - amt_in_pay_rate
		return amt_in_pay_rate - amt_in_recv_rate

	def _gain_loss_posting_date(self, payment, invoice):
		date = payment.posting_date
		if payment.is_advance:
			return date
		if self.exc_gain_loss_posting_date_setting == "Invoice":
			date = invoice.posting_date
		elif self.exc_gain_loss_posting_date_setting == "Reconciliation Date":
			date = nowdate()
		return date


class ReconcileRouter:
	"""Per-Allocation-row dispatch. Each pair is settled by mutating a writable
	voucher via `reconcile_against_document`. A pair with no writable voucher in a
	shared account is first re-expressed as two rows against a minted bridge JE.
	"""

	def __init__(self, pr):
		self.pr = pr
		self.company = pr.company
		self.party_type = pr.party_type

	def execute(self, skip_ref_details_update_for_pe=False):
		adjust_allocations_for_taxes(self.pr)

		standard_args = []

		for row in self.pr.get("allocation") or []:
			if not (row.allocated_amount and row.to_receive_voucher_no and row.to_pay_voucher_no):
				continue

			sub_rows = self._bridge_cross_account(row) if self._needs_bridge(row) else [row]

			for r in sub_rows:
				standard_args.append(self._build_payment_args(r))

		if standard_args:
			reconcile_against_document(standard_args, skip_ref_details_update_for_pe, self.pr.dimensions)

	def _bridge_cross_account(self, row):
		"""Re-express the pair as two same-account rows against a minted transfer JE,
		each pairing an original voucher with the matching bridge leg. The legs are
		booked at the allocation's rate, so each sub-row carries the FX between its
		own original voucher and that rate.
		"""
		bridge = _post_cross_account_transfer(row, self.company, self.pr.dimensions)
		diff_r, diff_p = self._leg_differences(row)

		# accounts[0] = credit leg (to_receive account); accounts[1] = debit leg (to_pay account).
		recv_leg, pay_leg = bridge.accounts[0], bridge.accounts[1]

		row_r = frappe._dict(row.as_dict())
		row_r.update(
			{
				"to_pay_voucher_type": "Journal Entry",
				"to_pay_voucher_no": bridge.name,
				"to_pay_voucher_row": recv_leg.name,
				"to_pay_account": row.to_receive_account,
				"to_pay_party_type": row.to_receive_party_type,
				"to_pay_party": row.to_receive_party,
				"difference_amount": diff_r,
				"difference_account": row.difference_account if diff_r else None,
			}
		)

		row_p = frappe._dict(row.as_dict())
		row_p.update(
			{
				"to_receive_voucher_type": "Journal Entry",
				"to_receive_voucher_no": bridge.name,
				"to_receive_voucher_row": pay_leg.name,
				"to_receive_account": row.to_pay_account,
				"to_receive_party_type": row.to_pay_party_type,
				"to_receive_party": row.to_pay_party,
				"difference_amount": diff_p,
				"difference_account": row.difference_account if diff_p else None,
			}
		)

		return [row_r, row_p]

	def _leg_differences(self, row):
		"""FX for (original to_receive, bridge leg) and (bridge leg, original to_pay)."""
		allocator = Allocator(self.pr)
		allocated = flt(row.allocated_amount)

		def voucher(side, voucher_type=None, rate=None):
			return frappe._dict(
				voucher_type=voucher_type or row.get(f"{side}_voucher_type"),
				exchange_rate=rate or row.get(f"{side}_exchange_rate"),
				currency=row.currency,
				account_type=frappe.get_cached_value("Account", row.get(f"{side}_account"), "account_type"),
			)

		# legs are booked at `exchange_rate`, on the counterpart's account
		pay_leg = voucher("to_receive", "Journal Entry", row.exchange_rate)
		recv_leg = voucher("to_pay", "Journal Entry", row.exchange_rate)
		diff_r = allocator._fx_difference(voucher("to_receive"), pay_leg, allocated)
		diff_p = allocator._fx_difference(recv_leg, voucher("to_pay"), allocated)
		return diff_r, diff_p

	@staticmethod
	def _voucher_fields(row, side):
		"""Collapse a `to_receive`/`to_pay` row half into side-agnostic voucher fields."""
		return frappe._dict(
			voucher_type=row.get(f"{side}_voucher_type"),
			voucher_no=row.get(f"{side}_voucher_no"),
			voucher_row=row.get(f"{side}_voucher_row"),
			account=row.get(f"{side}_account"),
			party_type=row.get(f"{side}_party_type"),
			party=row.get(f"{side}_party"),
		)

	def _needs_bridge(self, row):
		"""Bridge when a shared-account pair has no mutable voucher, or for any
		cross-account pair. Exception: a natural-side PE booking its advance in a
		separate party account is mutated directly and posts its own reconciliation
		GL, so bridging would double-handle it. A reverse-side separate-advance PE
		is not exempt — it is never mutated, so it must be bridged.
		"""
		if row.to_receive_account == row.to_pay_account:
			recv = frappe._dict(voucher_type=row.to_receive_voucher_type)
			pay = frappe._dict(voucher_type=row.to_pay_voucher_type)
			return pick_voucher_side(recv, pay, self.party_type) is None

		natural = payment_side(self.party_type)
		if row.get(f"{natural}_voucher_type") == "Payment Entry" and frappe.db.get_value(
			"Payment Entry",
			row.get(f"{natural}_voucher_no"),
			"book_advance_payments_in_separate_party_account",
		):
			return False

		return True

	def _build_payment_args(self, row):
		"""Build `reconcile_against_document` args. Every row here must have a writable
		voucher, so `pick_voucher_side` always resolves; a `None` side means a routing
		bug let an un-bridged reverse-PE pair through.
		"""
		recv = frappe._dict(voucher_type=row.to_receive_voucher_type)
		pay = frappe._dict(voucher_type=row.to_pay_voucher_type)
		side = pick_voucher_side(recv, pay, self.party_type)

		writable = self._voucher_fields(row, "to_pay" if side == "pay" else "to_receive")
		non_writable = self._voucher_fields(row, "to_receive" if side == "pay" else "to_pay")

		if writable.voucher_type == "Journal Entry":
			account = writable.account
			dr_or_cr = "credit_in_account_currency" if side == "pay" else "debit_in_account_currency"
		else:
			account = non_writable.account
			dr_or_cr = (
				"credit_in_account_currency"
				if erpnext.get_party_account_type(self.party_type) == RECEIVABLE
				else "debit_in_account_currency"
			)

		party_type = writable.party_type or self.party_type
		difference_amount = flt(row.get("difference_amount"))
		if writable.voucher_type == "Journal Entry" and party_type != "Customer" and is_cash_pair(recv, pay):
			difference_amount = -difference_amount

		args = frappe._dict(
			{
				"writable_voucher_type": writable.voucher_type,
				"writable_voucher_no": writable.voucher_no,
				"writable_voucher_detail_no": writable.voucher_row,
				"non_writable_voucher_type": non_writable.voucher_type,
				"non_writable_voucher_no": non_writable.voucher_no,
				"account": account or self.pr.receivable_payable_account,
				"exchange_rate": row.get("exchange_rate"),
				"party_type": party_type,
				"party": writable.party or self.pr.party,
				"is_advance": row.get("is_advance"),
				"dr_or_cr": dr_or_cr,
				"unreconciled_amount": flt(row.get("unreconciled_amount")),
				"unadjusted_amount": flt(row.get("amount")),
				"allocated_amount": flt(row.get("allocated_amount")),
				"difference_amount": difference_amount,
				"difference_account": row.get("difference_account"),
				"difference_posting_date": row.get("gain_loss_posting_date"),
				"cost_center": row.get("cost_center"),
				"currency": row.get("currency"),
			}
		)

		for dim in self.pr.dimensions:
			if row.get(dim.fieldname):
				args[dim.fieldname] = row.get(dim.fieldname)

		return args


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
		company: DF.Link
		cost_center: DF.Link | None
		currency: DF.Link | None
		currency_filter: DF.Link | None
		default_advance_account: DF.Link | None
		difference_amount: DF.Currency
		fetch_limit: DF.Int
		from_date: DF.Date | None
		max_amount: DF.Currency
		min_amount: DF.Currency
		party: DF.DynamicLink
		party_type: DF.Link
		project: DF.Link | None
		receivable_payable_account: DF.Link | None
		to_date: DF.Date | None
		to_pay: DF.Table[PaymentReconciliationEntry]
		to_receive: DF.Table[PaymentReconciliationEntry]
		total_invoice_amount: DF.Currency
		total_payment_amount: DF.Currency
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.common_filter_conditions = []
		self.accounting_dimension_filter_conditions = []
		self.ple_posting_date_filter = []
		self.dimensions = get_dimensions(with_cost_center_and_project=True)[0]

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
				"fetch_limit": 50,
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
		self.set("to_receive", [])
		self.set("to_pay", [])
		self.check_mandatory_to_fetch()

		open_balances = OpenBalanceFetcher(self).fetch()
		self._classify_and_populate(open_balances)
		self._apply_fetch_limit()

	def _classify_and_populate(self, open_balances):
		open_balances.sort(key=_fifo_key)

		for row in open_balances:
			signed = flt(row.get("outstanding_amount"))
			if not signed:
				continue
			target = classify(row.get("account_type"), signed)
			table = "to_receive" if target == RECEIVABLE else "to_pay"

			self.append(
				table,
				{
					**row,
					"amount": abs(signed),
					"outstanding_amount": abs(signed),
					"exchange_rate": flt(row.get("exchange_rate")) or 1.0,
				},
			)

	def _apply_fetch_limit(self):
		limit = self.fetch_limit
		if limit and len(self.to_receive) > limit:
			self.to_receive = self.to_receive[:limit]
		if limit and len(self.to_pay) > limit:
			self.to_pay = self.to_pay[:limit]

	@frappe.whitelist()
	def calculate_difference_on_allocation_change(
		self,
		payment_entry: list | None = None,
		invoice: list | None = None,
		allocated_amount: float | None = None,
	):
		"""Backward-compat API for external callers that manually edit an
		allocation row's allocated_amount. Delegates to `Allocator._fx_difference`."""
		if not (payment_entry and invoice):
			return 0.0
		pay = (
			frappe._dict(payment_entry[0]) if isinstance(payment_entry, list) else frappe._dict(payment_entry)
		)
		recv = frappe._dict(invoice[0]) if isinstance(invoice, list) else frappe._dict(invoice)
		return Allocator(self)._fx_difference(recv, pay, flt(allocated_amount))

	@frappe.whitelist()
	def allocate_entries(
		self,
		args: dict | str | None = None,
		to_receive: list | None = None,
		to_pay: list | None = None,
		**kwargs,
	):
		"""Run the Allocator. Three call shapes:
		1. `({"to_receive": [...], "to_pay": [...]})` — Process PR background job
		2. `(to_receive=[...], to_pay=[...])` — form's "select rows then Allocate"
		3. `()` — Auto-Match across the full parent tables
		"""
		if isinstance(args, str):
			import json as _json

			args = _json.loads(args)
		if args is None:
			args = {}
		to_receive = to_receive if to_receive is not None else args.get("to_receive")
		to_pay = to_pay if to_pay is not None else args.get("to_pay")

		if to_receive is not None:
			to_receive = [frappe._dict(r) if isinstance(r, dict) else r for r in to_receive]
		if to_pay is not None:
			to_pay = [frappe._dict(r) if isinstance(r, dict) else r for r in to_pay]

		if not (to_receive or self.get("to_receive")):
			frappe.throw(_("No records found in the To Receive table"))
		if not (to_pay or self.get("to_pay")):
			frappe.throw(_("No records found in the To Pay table"))

		allocations = Allocator(self, to_receive=to_receive, to_pay=to_pay).allocate()

		self.set("allocation", [])
		for entry in allocations:
			if entry["allocated_amount"]:
				row = self.append("allocation", {})
				row.update(entry)

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
		ReconcileRouter(self).execute()
		msgprint(_("Successfully Reconciled"))

		self.get_unreconciled_entries()

	def validate_allocation(self):
		"""Per-row checks against open balances fetched fresh from the ledger, not the
		browser's copy: both sides still open, allocated ≤ each side's outstanding
		(summed across rows), matching currency and party. Each row is then rebuilt
		from the ledger, keeping only what the user may change.
		"""
		rows = [
			row
			for row in self.get("allocation") or []
			if row.allocated_amount and row.to_receive_voucher_no and row.to_pay_voucher_no
		]
		if not rows:
			frappe.throw(_("No records found in Allocation table"))

		recv_index, pay_index = self._fresh_open_balances(rows)
		allocator = Allocator(self)
		user_fields = (
			"allocated_amount",
			"difference_account",
			"gain_loss_posting_date",
			"debit_or_credit_note_posting_date",
			"cost_center",
			*(dim.fieldname for dim in self.dimensions),
		)
		used = {}

		for row in rows:
			recv_key = (
				row.to_receive_voucher_type,
				row.to_receive_voucher_no,
				row.to_receive_voucher_row or "",
			)
			pay_key = (row.to_pay_voucher_type, row.to_pay_voucher_no, row.to_pay_voucher_row or "")

			recv_src = recv_index.get(recv_key)
			pay_src = pay_index.get(pay_key)
			for key, src in ((recv_key, recv_src), (pay_key, pay_src)):
				if not src:
					frappe.throw(
						_(
							"Row {0}: {1} {2} is no longer open for this party. Please fetch the entries again."
						).format(row.idx, key[0], key[1])
					)

			# one voucher can feed several rows, so check the total used so far
			allocated = flt(row.allocated_amount)
			used[recv_key] = used.get(recv_key, 0) + allocated
			used[pay_key] = used.get(pay_key, 0) + allocated
			recv_outs = flt(recv_src.outstanding_amount)
			pay_outs = flt(pay_src.outstanding_amount)

			if used[recv_key] - recv_outs > 0.009:
				frappe.throw(
					_("Row {0}: Allocated amount {1} exceeds receivable outstanding {2} for {3}").format(
						row.idx, used[recv_key], recv_outs, row.to_receive_voucher_no
					)
				)
			if used[pay_key] - pay_outs > 0.009:
				frappe.throw(
					_("Row {0}: Allocated amount {1} exceeds payable outstanding {2} for {3}").format(
						row.idx, used[pay_key], pay_outs, row.to_pay_voucher_no
					)
				)

			if recv_src and pay_src and recv_src.currency and pay_src.currency:
				if recv_src.currency != pay_src.currency:
					frappe.throw(
						_(
							"Row {0}: Cross-currency reconciliation is not supported. "
							"Receivable {1} ({2}) does not match payable {3} ({4})."
						).format(
							row.idx,
							row.to_receive_voucher_no,
							recv_src.currency,
							row.to_pay_voucher_no,
							pay_src.currency,
						)
					)

			if (
				row.to_receive_party_type
				and row.to_pay_party_type
				and (
					row.to_receive_party_type != row.to_pay_party_type
					or row.to_receive_party != row.to_pay_party
				)
			):
				frappe.throw(
					_(
						"Row {0}: Cross-party reconciliation is not supported in this phase ({1} {2} vs {3} {4})"
					).format(
						row.idx,
						row.to_receive_party_type,
						row.to_receive_party,
						row.to_pay_party_type,
						row.to_pay_party,
					)
				)

			# rebuild from the ledger, keeping what the user may change
			kept = {field: row.get(field) for field in user_fields if row.get(field)}
			row.update(allocator._make_allocation(recv_src, pay_src, allocated))
			row.update(kept)

	def _fresh_open_balances(self, rows):
		"""Open rows of the allocated vouchers, fetched again from the ledger."""
		vouchers = {
			(row.get(f"{side}_voucher_type"), row.get(f"{side}_voucher_no"))
			for row in rows
			for side in ("to_receive", "to_pay")
		}
		self.set("to_receive", [])
		self.set("to_pay", [])
		self._classify_and_populate(OpenBalanceFetcher(self, vouchers=sorted(vouchers)).fetch())

		def index(table):
			return {(r.voucher_type, r.voucher_no, r.voucher_row or ""): r for r in self.get(table)}

		return index("to_receive"), index("to_pay")

	def check_mandatory_to_fetch(self):
		for fieldname in ["company", "party_type", "party"]:
			if not self.get(fieldname):
				frappe.throw(_("Please select {0} first").format(self.meta.get_translated_label(fieldname)))


def _make_system_journal(**kwargs):
	"""Create + submit a system-generated JE from kwargs, with standard system defaults."""
	jv = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": kwargs.get("voucher_type"),
			"company": kwargs.get("company"),
			"posting_date": kwargs.get("posting_date") or today(),
			"multi_currency": kwargs.get("multi_currency", 0),
			"accounts": kwargs.get("accounts"),
		}
	)
	jv.flags.ignore_mandatory = kwargs.get("ignore_mandatory", True)
	jv.flags.ignore_exchange_rate = kwargs.get("ignore_exchange_rate", True)
	jv.flags.skip_remarks_creation = kwargs.get("skip_remarks_creation", True)
	jv.is_system_generated = kwargs.get("is_system_generated", True)
	jv.remark = kwargs.get("remark", None)
	jv.submit()
	return jv


def _post_cross_account_transfer(row, company, active_dimensions=None):
	"""Post + submit the no-reference bridge transfer JE (same party, both legs).
	Cross-account: a genuine transfer between the accounts. Same-account invoice↔note:
	legs net to zero, settling is done by the later JEA splits.
	"""
	amount = abs(flt(row.allocated_amount))
	cost_center = row.cost_center or erpnext.get_default_cost_center(company)
	company_currency = erpnext.get_company_currency(company)
	exchange_rate = flt(row.exchange_rate) or 1.0

	def leg(account, party_type, party, dr_or_cr):
		entry = frappe._dict(
			{
				"account": account,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center,
				"exchange_rate": exchange_rate,
				dr_or_cr: amount,
			}
		)
		if active_dimensions:
			for dim in active_dimensions:
				if row.get(dim.fieldname):
					entry[dim.fieldname] = row.get(dim.fieldname)
		return entry

	accounts = [
		# to_receive voucher carries a debit balance → credit its account.
		leg(
			row.to_receive_account,
			row.to_receive_party_type,
			row.to_receive_party,
			"credit_in_account_currency",
		),
		# to_pay voucher carries a credit balance → debit its account.
		leg(row.to_pay_account, row.to_pay_party_type, row.to_pay_party, "debit_in_account_currency"),
	]

	return _make_system_journal(
		company=company,
		voucher_type=CROSS_ACCOUNT_BRIDGE_VOUCHER_TYPE,
		posting_date=_bridge_posting_date(row, company),
		multi_currency=1 if row.currency != company_currency else 0,
		accounts=accounts,
	)


def _bridge_posting_date(row, company):
	# a date the user picked wins, e.g. to stay out of a closed period
	if row.get("debit_or_credit_note_posting_date"):
		return row.debit_or_credit_note_posting_date

	# invoice vs note: posted today, like the credit/debit note journal it replaces
	if row.to_receive_voucher_type in INVOICE_DOCTYPES and row.to_pay_voucher_type in INVOICE_DOCTYPES:
		return today()

	# payment vs invoice: follows `reconciliation_takes_effect_on`
	if row.to_pay_voucher_type in INVOICE_DOCTYPES:
		invoice_type, invoice_no = row.to_pay_voucher_type, row.to_pay_voucher_no
		pay_type, pay_no = row.to_receive_voucher_type, row.to_receive_voucher_no
	else:
		invoice_type, invoice_no = row.to_receive_voucher_type, row.to_receive_voucher_no
		pay_type, pay_no = row.to_pay_voucher_type, row.to_pay_voucher_no
	pay_date = frappe.db.get_value(pay_type, pay_no, "posting_date") or today()
	return get_reconciliation_effect_date(invoice_type, invoice_no, company, pay_date)


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
