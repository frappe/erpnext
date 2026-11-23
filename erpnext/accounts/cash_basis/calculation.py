# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The cash basis calculation for one company to one date: load, classify, build adjustment rows."""

from collections import defaultdict
from dataclasses import dataclass, field

import frappe
from frappe.model.meta import get_field_precision
from frappe.utils import flt, getdate

from erpnext.accounts.cash_basis import queries
from erpnext.accounts.cash_basis.adjustments import AdjustmentBuilder
from erpnext.accounts.cash_basis.exceptions import ExceptionCollector
from erpnext.accounts.cash_basis.obligations import (
	CASH_ACCOUNT_TYPES,
	OBLIGATION_VOUCHER_TYPES,
	PARTY_ACCOUNT_TYPES,
	ObligationBuilder,
	gl_amount,
	party_sign,
)
from erpnext.accounts.cash_basis.settlements import (
	SKIPPED_JOURNAL_TYPES,
	SettlementBuilder,
	get_unapplied_rows,
	mark_consumed,
)

INVOICE_TYPES = ("Sales Invoice", "Purchase Invoice")
UNAPPLIED_INCOME_AND_EXPENSE = "Income and Expense"
UNAPPLIED_BALANCE_SHEET = "Balance Sheet"


@dataclass
class CalculationContext:
	company: str
	to_date: object
	precision: int = 2
	precision_tolerance: float = 0.005
	party_types: tuple = queries.CONVERTIBLE_PARTY_TYPES
	dimension_fields: list = field(default_factory=list)
	accounts: dict = field(default_factory=dict)
	gl_rows: dict = field(default_factory=dict)
	invoice_headers: dict = field(default_factory=dict)
	voucher_dates: dict = field(default_factory=dict)
	journal_types: dict = field(default_factory=dict)
	journal_treatments: dict = field(default_factory=dict)  # name: cash_basis_treatment
	deferred_items: dict = field(default_factory=dict)  # (doctype, name): [DeferredItem]
	schedule_journal_rows: dict = field(default_factory=dict)  # (doctype, name): GL rows
	payment_journals: set = field(default_factory=set)
	party_only_journals: set = field(default_factory=set)
	revaluation_journals: list = field(default_factory=list)
	period_closing_vouchers: list = field(default_factory=list)
	row_order: dict = field(default_factory=dict)
	unapplied_accounts: dict = field(default_factory=dict)
	default_cost_center: str | None = None


@dataclass
class CalculationResult:
	rows: list
	exceptions: list
	events: list
	obligations: dict
	account_rates: dict = field(
		default_factory=dict
	)  # (voucher type, voucher, account, party type, party): rate


class CashBasisCalculation:
	"""The calculation stands alone: the caller gives the unapplied treatment and accounts.

	unapplied_accounts: {"Customer": receipts account, "Supplier": payments account}.
	Without both accounts, the treatment is the Balance Sheet treatment: no unapplied rows.
	"""

	def __init__(self, company: str, to_date, unapplied_treatment=None, unapplied_accounts=None):
		self.ctx = CalculationContext(company=company, to_date=getdate(to_date))
		accounts = unapplied_accounts or {}
		if unapplied_treatment == UNAPPLIED_INCOME_AND_EXPENSE and all(
			accounts.get(party_type) for party_type in self.ctx.party_types
		):
			self.ctx.unapplied_accounts = {
				party_type: accounts[party_type] for party_type in self.ctx.party_types
			}
		self.collector = ExceptionCollector()
		self.own_rows: dict[tuple, list] = defaultdict(list)
		self.account_rates: dict[tuple, float] = {}
		self.settlement_rows: dict[tuple, list] = defaultdict(list)

	def run(self) -> CalculationResult:
		self.load()
		obligations = self.build_obligations()
		events = SettlementBuilder(self.ctx, self.collector).build_events(obligations, self.settlement_rows)
		unapplied_rows = get_unapplied_rows(self.ctx, self.own_rows, self.settlement_rows)
		mark_consumed(events, unapplied_rows)
		set_weights(events)
		rows = AdjustmentBuilder(self.ctx).build(
			obligations, events, unapplied_rows, self.ctx.revaluation_journals
		)
		return CalculationResult(rows, self.collector.as_list(), events, obligations, self.account_rates)

	def load(self):
		ctx = self.ctx
		self.load_company_settings()
		ctx.dimension_fields = queries.get_dimension_fields()
		ctx.accounts = queries.get_account_details(ctx.company)

		ple_rows = queries.get_payment_ledger_rows(ctx.company, ctx.to_date)
		vouchers = defaultdict(set)
		# Account currency for each unit of company currency, for a row in another currency. A
		# Journal Entry can have rows of one party at different rates: use the rate weighted by
		# absolute amounts, so that rows of opposite sign (a transfer) do not cancel. It is exact for
		# one rate or one sign, and an approximation otherwise (for display only). A row with
		# no amount in the account currency (exchange gain or loss) has no rate.
		account_amounts = defaultdict(lambda: [0.0, 0.0])
		for index, row in enumerate(ple_rows):
			ctx.row_order[row.name] = index
			if flt(row.amount) and flt(row.amount_in_account_currency):
				amounts = account_amounts[
					(row.voucher_type, row.voucher_no, row.account, row.party_type, row.party)
				]
				amounts[0] += abs(flt(row.amount_in_account_currency))
				amounts[1] += abs(flt(row.amount))
			vouchers[row.voucher_type].add(row.voucher_no)
			if row.voucher_type == row.against_voucher_type and row.voucher_no == row.against_voucher_no:
				self.own_rows[(row.voucher_type, row.voucher_no)].append(row)
			else:
				self.settlement_rows[(row.against_voucher_type, row.against_voucher_no)].append(row)
		for key, (in_account_currency, amount) in account_amounts.items():
			if amount > ctx.precision_tolerance:
				self.account_rates[key] = in_account_currency / amount

		ctx.revaluation_journals = queries.get_revaluation_journal_entries(ctx.company, ctx.to_date)
		ctx.period_closing_vouchers = queries.get_period_closing_vouchers(ctx.company, ctx.to_date)
		vouchers["Journal Entry"].update(ctx.revaluation_journals)
		self.load_headers(vouchers)
		gl_vouchers = set().union(*(vouchers.get(t, set()) for t in (*INVOICE_TYPES, "Journal Entry")))
		for row in queries.get_gl_rows(ctx.company, gl_vouchers, ctx.to_date):
			ctx.gl_rows.setdefault((row.voucher_type, row.voucher_no), []).append(row)

	def load_company_settings(self):
		ctx = self.ctx
		currency, ctx.default_cost_center = queries.get_company_defaults(ctx.company)
		ctx.precision = get_field_precision(frappe.get_meta("GL Entry").get_field("debit"), currency=currency)
		ctx.precision_tolerance = 0.5 / (10**ctx.precision)

	def load_headers(self, vouchers):
		ctx = self.ctx
		for doctype in INVOICE_TYPES:
			names = vouchers.get(doctype, set())
			for name, header in queries.get_invoice_headers(doctype, names).items():
				ctx.invoice_headers[(doctype, name)] = header
				ctx.voucher_dates[(doctype, name)] = header.posting_date
			# Also the returns that settle an invoice: their deferred rows are contra rows.
			for name, items in queries.get_deferred_items(doctype, names).items():
				ctx.deferred_items[(doctype, name)] = items
		deferred = defaultdict(set)
		for doctype, name in ctx.deferred_items:
			deferred[doctype].add(name)
		for row in queries.get_schedule_journal_rows(ctx.company, deferred, ctx.to_date):
			ctx.schedule_journal_rows.setdefault((row.against_voucher_type, row.against_voucher), []).append(
				row
			)
		for doctype in ("Payment Entry", "Journal Entry"):
			for name, header in queries.get_settling_voucher_headers(
				doctype, vouchers.get(doctype, set())
			).items():
				ctx.voucher_dates[(doctype, name)] = header.posting_date
				if doctype == "Journal Entry":
					ctx.journal_types[name] = header.voucher_type
					ctx.journal_treatments[name] = header.cash_basis_treatment

	def build_obligations(self) -> dict:
		self.set_payment_journals()
		builder = ObligationBuilder(self.ctx, self.collector)
		obligations = {}
		for key, rows in self.own_rows.items():
			voucher_type, voucher_no = key
			if voucher_type not in OBLIGATION_VOUCHER_TYPES:
				continue
			gl_rows = self.ctx.gl_rows.get(key, [])
			if voucher_type == "Journal Entry" and voucher_no in self.ctx.payment_journals:
				continue
			obligation = builder.build(voucher_type, voucher_no, rows, gl_rows)
			if obligation:
				obligations[key] = obligation
		return obligations

	def is_payment_journal(self, gl_rows) -> bool:
		"""A Journal Entry with no P&L row is a payment when it pays cash, has only party rows,
		or decreases the open amount of its party rows.

		Else, for example a purchase of an asset on credit, it is an obligation with no convertible line.
		The GL rows decide, because a reconciliation can change the PLE rows in place.
		"""
		accounts = self.ctx.accounts
		party_rows = [r for r in gl_rows if accounts[r.account].account_type in PARTY_ACCOUNT_TYPES]
		other = [
			accounts[r.account]
			for r in gl_rows
			if accounts[r.account].account_type not in PARTY_ACCOUNT_TYPES
		]
		if any(account.report_type != "Balance Sheet" for account in other):
			return False
		pays_cash = any(account.account_type in CASH_ACCOUNT_TYPES for account in other)
		open_change = sum(party_sign(accounts[r.account].account_type) * gl_amount(r) for r in party_rows)
		return pays_cash or not other or open_change < 0

	def set_payment_journals(self):
		for (voucher_type, voucher_no), gl_rows in self.ctx.gl_rows.items():
			if (
				voucher_type != "Journal Entry"
				or self.ctx.journal_types.get(voucher_no) in SKIPPED_JOURNAL_TYPES
			):
				continue
			if self.is_payment_journal(gl_rows):
				self.ctx.payment_journals.add(voucher_no)
				if all(self.ctx.accounts[r.account].account_type in PARTY_ACCOUNT_TYPES for r in gl_rows):
					self.ctx.party_only_journals.add(voucher_no)


def set_weights(events):
	"""The part of each settlement that recognises the lines of its obligation.

	A link Journal Entry has only party rows. A debit settlement is cash only to the extent that
	it uses the cash of a payment. The rest is non-cash: with a credit obligation in the group,
	a credit note set against the invoice, as Payment Reconciliation does. The credit side keeps
	the difference of the two ratios (rule 4 of section 6.5).
	"""
	links = defaultdict(list)
	for event in events:
		if event.settler.is_link:
			links[id(event.settler)].append(event)
		else:
			event.weight = 1.0 if event.settler.is_cash else 0.0
			event.pays_cash = event.settler.is_cash

	for group in links.values():
		debits = [e for e in group if not e.obligation.is_credit]
		credits = [e for e in group if e.obligation.is_credit]
		debit_total = sum(e.amount for e in debits)
		debit_ratio = sum(e.amount * e.obligation.ratio for e in debits) / debit_total if debit_total else 0.0
		for event in debits:
			used = event.consumed / event.amount_company if event.amount_company else 0.0
			event.weight = min(max(used, 0.0), 1.0)
			event.pays_cash = event.weight > 0
		for event in credits:
			ratio = event.obligation.ratio
			event.weight = flt(1 - debit_ratio / ratio) if debits and ratio else 1.0


def get_cash_adjustments(
	company,
	to_date,
	from_date=None,
	*,
	group_by="row",
	filters=None,
	unapplied_treatment=None,
	unapplied_accounts=None,
) -> list[dict]:
	"""Public: adjustment rows for the cash basis view of the company, dated from_date to to_date.

	filters: the report filters. The rows follow the rules of the GL query of the reports:
	cost center and tree dimensions with their children, project, finance book. The
	calculation reads whole vouchers; the user permissions of the session user then apply
	to the adjustment rows.

	group_by "row" gives one row for each line and event. "account" gives totals for each
	account, posting date, and dimension. Each row has is_cash_adjustment = 1.
	"""
	result = CashBasisCalculation(company, to_date, unapplied_treatment, unapplied_accounts).run()
	return filter_and_group(result.rows, from_date, to_date, group_by, company, filters)


def get_exceptions(company, to_date, from_date=None) -> list[dict]:
	"""Public: the cash basis exceptions, with the reason (section 6.9).

	A voucher exception stays accrual. A mixed settlement is treated as cash (section 6.4).
	"""
	exceptions = CashBasisCalculation(company, to_date).run().exceptions
	if from_date:
		from_date = getdate(from_date)
		exceptions = [e for e in exceptions if getdate(e["posting_date"]) >= from_date]
	return exceptions


def filter_and_group(rows, from_date, to_date, group_by, company, filters=None) -> list[dict]:
	from erpnext.accounts.cash_basis.filters import apply_report_filters

	from_date = getdate(from_date) if from_date else None
	to_date = getdate(to_date)
	selected = [
		r for r in rows if r["posting_date"] <= to_date and (not from_date or r["posting_date"] >= from_date)
	]
	set_fiscal_years(selected, company)
	selected = apply_report_filters(selected, company, filters)
	if group_by == "row":
		return selected
	if group_by != "account":
		frappe.throw(frappe._("Group by must be row or account."), title=frappe._("Invalid Group By"))
	return group_by_account(selected)


def set_fiscal_years(rows, company=None):
	from erpnext.accounts.utils import get_fiscal_year

	years = {}
	for row in rows:
		posting_date = row["posting_date"]
		if posting_date not in years:
			fiscal_year = get_fiscal_year(posting_date, company=company, raise_on_missing=False)
			years[posting_date] = fiscal_year[0] if fiscal_year else None
		row["fiscal_year"] = years[posting_date]


def group_by_account(rows) -> list[dict]:
	keep = ("account", "posting_date", "fiscal_year", "cost_center", "project", "finance_book")
	grouped = {}
	for row in rows:
		dimension_keys = tuple(sorted(k for k in row if k not in keep and k not in NON_GROUP_KEYS))
		key = tuple(row[k] for k in keep) + tuple((k, row[k]) for k in dimension_keys)
		total = grouped.setdefault(
			key, {**{k: row[k] for k in keep}, **{k: row[k] for k in dimension_keys}, "amount": 0.0}
		)
		total["amount"] += row["debit"] - row["credit"]
	result = []
	for total in grouped.values():
		amount = flt(total.pop("amount"), 9)
		if amount:
			result.append(
				{**total, "debit": max(amount, 0.0), "credit": max(-amount, 0.0), "is_cash_adjustment": 1}
			)
	return result


NON_GROUP_KEYS = {
	"debit",
	"credit",
	"party_type",
	"party",
	"voucher_type",
	"voucher_no",
	"against_voucher_type",
	"against_voucher",
	"remarks",
	"is_opening",
	"company",
	"is_cash_adjustment",
}
