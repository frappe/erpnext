# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Settlement events from the Payment Ledger, their cash date, and their class (sections 6.3, 6.4, 6.7)."""

from collections import defaultdict
from dataclasses import dataclass, field, replace

from frappe.utils import flt, getdate

from erpnext.accounts.cash_basis import exceptions as reasons
from erpnext.accounts.cash_basis.obligations import (
	CASH_ACCOUNT_TYPES,
	PARTY_ACCOUNT_TYPES,
	against_names,
	gl_amount,
)

CASH = "Cash"
NON_CASH = "Non-cash"
CASH_AND_NON_CASH = "Cash and Non-cash"
SKIPPED_JOURNAL_TYPES = ("Exchange Gain Or Loss", "Exchange Rate Revaluation")
# Journal Entry.cash_basis_treatment: the user decides the class of a settling Journal Entry.
AUTOMATIC = "Automatic"
CASH_SETTLEMENT = "Cash Settlement"
NON_CASH_ADJUSTMENT = "Non-cash Adjustment"


@dataclass
class Settler:
	"""How one settling voucher settles: cash, non-cash with P&L rows, or a link to another obligation."""

	voucher_type: str
	voucher_no: str
	posting_date: object
	is_cash: bool
	contra_rows: list = field(default_factory=list)
	ratio: float = 0.0  # c of the settler: P&L amount for each unit of its party amount, GL sign
	# The rows of a return on the deferred account of its deferred items (phase 7). They count in
	# the ratio, and they are removed in full for the share, not scaled by c (rule 3).
	deferred_rows: list = field(default_factory=list)
	is_link: bool = False
	exception: str | None = None


@dataclass
class SettlementEvent:
	obligation: object
	settler: Settler
	amount: float  # s: PLE sign, account currency; positive decreases the open amount
	amount_company: float  # s in company currency, same sign
	account: str
	order: int
	share: float = 1.0
	consumed_by_account: dict = field(default_factory=dict)  # company currency, for each account
	weight: float = 1.0  # part of s that recognises the lines: 1 for cash, 0 for non-cash
	pays_cash: bool = False  # the event takes cash off the unapplied account

	@property
	def consumed(self) -> float:
		"""Company currency: the part of the event that unapplied rows of its settler paid."""
		return sum(self.consumed_by_account.values())

	@property
	def cash_date(self):
		return self.settler.posting_date

	@property
	def recognition_date(self):
		return max(getdate(self.cash_date), getdate(self.obligation.posting_date))


@dataclass
class UnappliedRow:
	"""An unapplied row of a payment: an own PLE row of a Payment Entry or a cash Journal Entry."""

	voucher_type: str
	voucher_no: str
	party_type: str
	party: str
	account: str
	amount: float  # PLE sign, company currency
	cash_date: object
	cost_center: str | None


class SettlementBuilder:
	def __init__(self, context, collector):
		self.ctx = context
		self.collector = collector
		self.settlers: dict[tuple, Settler] = {}

	def build_events(self, obligations: dict, settlement_rows: dict) -> list[SettlementEvent]:
		events = []
		for key, obligation in obligations.items():
			events.extend(self.self_settlement_events(obligation))
			by_settler = defaultdict(list)
			for row in settlement_rows.get(key, ()):
				by_settler[(row.voucher_type, row.voucher_no)].append(row)
			for (voucher_type, settler_no), rows in by_settler.items():
				event = self.make_event(obligation, voucher_type, settler_no, rows)
				if event:
					events.append(event)
		self.set_shares(events)
		return sorted(events, key=lambda e: (getdate(e.recognition_date), e.order))

	def self_settlement_events(self, obligation):
		settler_base = Settler(obligation.voucher_type, obligation.voucher_no, obligation.posting_date, True)
		events = []
		for part in obligation.self_settlements:
			settler = settler_base
			if not part.is_cash:
				rows = part.contra_rows
				settler = Settler(
					obligation.voucher_type,
					obligation.voucher_no,
					obligation.posting_date,
					False,
					contra_rows=rows,
					# The contra row and the party row of a self-settlement have opposite signs.
					ratio=-1.0,
				)
			events.append(
				SettlementEvent(
					obligation, settler, part.amount, part.amount_company, obligation.party_account, 0
				)
			)
		return events

	def make_event(self, obligation, voucher_type, settler_no, rows):
		amount = -sum(flt(r.amount_in_account_currency) for r in rows)
		if abs(amount) <= self.ctx.precision_tolerance:
			return None
		settler = self.get_settler(voucher_type, settler_no, obligation, rows[0].posting_date)
		if settler is None:
			return None
		amount_company = -sum(flt(r.amount) for r in rows)
		if settler.exception:
			# The exceptions are in company currency, as the reports total them.
			self.collector.add(
				voucher_type,
				settler_no,
				settler.posting_date,
				obligation.party_type,
				obligation.party,
				amount_company,
				settler.exception,
			)
		return SettlementEvent(
			obligation,
			settler,
			amount,
			amount_company,
			rows[0].account,
			self.ctx.row_order[rows[0].name],
		)

	def get_settler(self, voucher_type, voucher_no, obligation, row_date) -> Settler | None:
		key = (voucher_type, voucher_no, obligation.party_type, obligation.party)
		if key not in self.settlers:
			self.settlers[key] = self.classify_settler(voucher_type, voucher_no, obligation, row_date)
		return self.settlers[key]

	def classify_settler(self, voucher_type, voucher_no, obligation, row_date) -> Settler | None:
		"""row_date: the posting date of its ledger row, for a voucher type with no loaded header.

		All ledger rows of a voucher have its posting date, so the cached settler is the same for
		each call.
		"""
		posting_date = self.ctx.voucher_dates.get((voucher_type, voucher_no), row_date)
		if voucher_type == "Payment Entry":
			return Settler(voucher_type, voucher_no, posting_date, True)
		if voucher_type == "Journal Entry":
			return self.classify_journal(voucher_no, posting_date, obligation)
		if voucher_type in ("Sales Invoice", "Purchase Invoice"):
			header = self.ctx.invoice_headers.get((voucher_type, voucher_no))
			if header and header.is_return:
				return self.non_cash_settler(voucher_type, voucher_no, posting_date, obligation)
		return Settler(voucher_type, voucher_no, posting_date, True, exception=reasons.MIXED_SETTLEMENT)

	def classify_journal(self, voucher_no, posting_date, obligation) -> Settler | None:
		journal_type = self.ctx.journal_types.get(voucher_no)
		if journal_type in SKIPPED_JOURNAL_TYPES:
			return None
		rows = self.ctx.gl_rows.get(("Journal Entry", voucher_no), [])
		party_rows = [r for r in rows if self.ctx.accounts[r.account].account_type in PARTY_ACCOUNT_TYPES]
		party_names = {r.name for r in party_rows}
		other_rows = [r for r in rows if r.name not in party_names]
		# The user decides the class of an entry with other rows. A Journal Entry with only party
		# rows always follows rule 4, and the form refuses a Bank or Cash row for a non-cash
		# adjustment: an older entry with such a value keeps the automatic class.
		treatment = self.ctx.journal_treatments.get(voucher_no) if other_rows else None
		if treatment == CASH_SETTLEMENT:
			return Settler("Journal Entry", voucher_no, posting_date, True)
		if treatment == NON_CASH_ADJUSTMENT and not self.has_cash_row(voucher_no):
			return self.non_cash_settler("Journal Entry", voucher_no, posting_date, obligation)
		if any((r.party_type, r.party) != (obligation.party_type, obligation.party) for r in party_rows):
			return Settler(
				"Journal Entry", voucher_no, posting_date, True, exception=reasons.MIXED_SETTLEMENT
			)
		if not other_rows:
			return Settler("Journal Entry", voucher_no, posting_date, False, is_link=True)

		report_types = {self.ctx.accounts[r.account].report_type for r in other_rows}
		if report_types == {"Balance Sheet"}:
			return Settler("Journal Entry", voucher_no, posting_date, True)
		if report_types == {"Profit and Loss"}:
			return self.non_cash_settler("Journal Entry", voucher_no, posting_date, obligation)
		return Settler("Journal Entry", voucher_no, posting_date, True, exception=reasons.MIXED_SETTLEMENT)

	def has_cash_row(self, voucher_no) -> bool:
		rows = self.ctx.gl_rows.get(("Journal Entry", voucher_no), [])
		return any(self.ctx.accounts[r.account].account_type in CASH_ACCOUNT_TYPES for r in rows)

	def non_cash_settler(self, voucher_type, voucher_no, posting_date, obligation) -> Settler:
		rows = self.ctx.gl_rows.get((voucher_type, voucher_no), [])
		deferred_items = defaultdict(set)
		for item in self.ctx.deferred_items.get((voucher_type, voucher_no), []):
			deferred_items[item.deferred_account].add(item.name)
		party_total = 0.0
		contra_rows, deferred_rows = [], []
		for row in rows:
			account = self.ctx.accounts[row.account]
			if account.account_type in PARTY_ACCOUNT_TYPES:
				party_total += gl_amount(row)
			elif account.report_type == "Profit and Loss" and obligation.party in against_names(row):
				contra_rows.append(row)
			elif row.get("voucher_detail_no") in deferred_items.get(row.account, ()):
				deferred_rows.append(row)
		# c_X counts the deferred rows too, as c_V counts the deferred line of V.
		contra_total = sum(gl_amount(r) for r in contra_rows + deferred_rows)
		ratio = contra_total / party_total if party_total else 0.0
		return Settler(
			voucher_type,
			voucher_no,
			posting_date,
			False,
			contra_rows=contra_rows,
			ratio=ratio,
			deferred_rows=deferred_rows,
		)

	def set_shares(self, events):
		"""share = s divided by the total that the settling voucher allocates (section 6.5)."""
		totals = defaultdict(float)
		for event in events:
			totals[id(event.settler)] += event.amount
		for event in events:
			total = totals[id(event.settler)]
			event.share = event.amount / total if total else 0.0


def get_unapplied_rows(context, own_rows: dict, settlement_rows: dict) -> list[UnappliedRow]:
	"""Own PLE rows of Payment Entries and cash Journal Entries (section 6.7).

	Two more kinds of rows count here:
	- A row of a voucher against a payment uses the cash of that payment. It counts for the
	  voucher that holds it, for example a Journal Entry that moves an advance onto an invoice.
	- A settlement of an invoice that is dated after the report date is still unapplied cash
	  at the report date.
	The own rows of a Journal Entry with only party rows move unapplied cash. They count only
	up to the unapplied credit that payments of the party put on the account before them.
	"""
	rows, journal_rows, journal_settled = [], [], defaultdict(float)
	for (against_type, against_no), ple_rows in settlement_rows.items():
		if is_payment(context, against_type, against_no):
			rows.extend(make_unapplied_row(context, r) for r in ple_rows if not is_skipped(context, r))
			continue
		for row in ple_rows:
			if row.voucher_no in context.party_only_journals:
				journal_settled[row.voucher_no] += -flt(row.amount)
			elif (against_type, against_no) not in own_rows and is_payment(
				context, row.voucher_type, row.voucher_no
			):
				rows.append(make_unapplied_row(context, row))
	for (voucher_type, voucher_no), ple_rows in own_rows.items():
		if is_payment(context, voucher_type, voucher_no):
			target = journal_rows if voucher_no in context.party_only_journals else rows
			target.extend(make_unapplied_row(context, row) for row in ple_rows)
	rows = [row for row in rows if row.party_type in context.party_types]
	journal_rows = [row for row in journal_rows if row.party_type in context.party_types]
	return rows + cap_journal_rows(rows, journal_rows, journal_settled)


def cap_journal_rows(payment_rows, journal_rows, journal_settled) -> list[UnappliedRow]:
	"""Limit the own rows of party-only Journal Entries to the unapplied credit they can move."""
	credit = defaultdict(list)  # (party_type, party, account) -> [(date, amount)]
	for row in payment_rows:
		credit[(row.party_type, row.party, row.account)].append((getdate(row.cash_date), -row.amount))
	drawn_before = defaultdict(float)
	capped = []
	by_journal = defaultdict(list)
	for row in journal_rows:
		by_journal[row.voucher_no].append(row)
	for voucher_no, rows in sorted(
		by_journal.items(), key=lambda item: (getdate(item[1][0].cash_date), item[0])
	):
		drawn = 0.0
		for row in (r for r in rows if r.amount > 0):
			key = (row.party_type, row.party, row.account)
			cash_date = getdate(row.cash_date)
			available = sum(a for d, a in credit[key] if d <= cash_date) - drawn_before[key]
			used = min(row.amount, max(available, 0.0))
			drawn_before[key] += used
			drawn += used
			if used > 0:
				capped.append(replace(row, amount=used))
		# A credit on another party account is a transfer of what the Journal Entry drew.
		room = max(drawn - max(journal_settled[voucher_no], 0.0), 0.0)
		for row in (r for r in rows if r.amount < 0):
			moved = min(-row.amount, room)
			room -= moved
			if moved > 0:
				capped.append(replace(row, amount=-moved))
				# A later Journal Entry can draw on the credit that this one moved.
				credit[(row.party_type, row.party, row.account)].append((getdate(row.cash_date), moved))
	return capped


def is_payment(context, voucher_type, voucher_no) -> bool:
	"""A payment dated on or before the report date."""
	posting_date = context.voucher_dates.get((voucher_type, voucher_no))
	if not posting_date or getdate(posting_date) > context.to_date:
		return False
	return voucher_type == "Payment Entry" or (
		voucher_type == "Journal Entry" and voucher_no in context.payment_journals
	)


def is_skipped(context, row) -> bool:
	return (
		row.voucher_type == "Journal Entry"
		and context.journal_types.get(row.voucher_no) in SKIPPED_JOURNAL_TYPES
	)


def make_unapplied_row(context, row) -> UnappliedRow:
	return UnappliedRow(
		row.voucher_type,
		row.voucher_no,
		row.party_type,
		row.party,
		row.account,
		flt(row.amount),
		context.voucher_dates.get((row.voucher_type, row.voucher_no), row.posting_date),
		row.cost_center,
	)


def mark_consumed(events, unapplied_rows):
	"""Match the use of an unapplied row (a positive own row) to the settlements of the same payment."""
	available = defaultdict(lambda: defaultdict(float))
	for row in unapplied_rows:
		if row.amount > 0:
			available[(row.voucher_type, row.voucher_no)][row.account] += row.amount
	for event in events:
		payment = (event.settler.voucher_type, event.settler.voucher_no)
		for account, amount in available.get(payment, {}).items():
			used = min(amount, event.amount_company - event.consumed)
			if used <= 0:
				continue
			event.consumed_by_account[account] = event.consumed_by_account.get(account, 0.0) + used
			available[payment][account] -= used


def get_settlement_events(company, to_date, from_date=None) -> list[dict]:
	"""Public: the settlement events of the converted obligations, by recognition date.

	Keys: against_voucher_type, against_voucher_no (the obligation), voucher_type, voucher_no
	(the settling voucher), party_type, party, account, amount (company currency),
	amount_in_account_currency, cash_date, recognition_date, settlement_class (Cash, Non-cash, or
	Cash and Non-cash for a part used from a payment).
	"""
	from erpnext.accounts.cash_basis.calculation import CashBasisCalculation

	from_date = getdate(from_date) if from_date else None
	events = []
	for event in CashBasisCalculation(company, to_date).run().events:
		if from_date and event.recognition_date < from_date:
			continue
		events.append(
			{
				"against_voucher_type": event.obligation.voucher_type,
				"against_voucher_no": event.obligation.voucher_no,
				"voucher_type": event.settler.voucher_type,
				"voucher_no": event.settler.voucher_no,
				"party_type": event.obligation.party_type,
				"party": event.obligation.party,
				"account": event.account,
				"amount": event.amount_company,
				"amount_in_account_currency": event.amount,
				"cash_date": getdate(event.cash_date),
				"recognition_date": event.recognition_date,
				"settlement_class": get_settlement_class(event.weight),
			}
		)
	return events


def get_settlement_class(weight: float) -> str:
	if weight >= 1:
		return CASH
	return CASH_AND_NON_CASH if weight > 0 else NON_CASH
