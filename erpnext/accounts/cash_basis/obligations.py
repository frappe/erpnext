# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Obligation vouchers: classes of their GL rows, the proof rule, and the convertible lines.

Sign rules: a GL amount is debit less credit, in the company currency. A PLE amount
increases the open amount of the party, for a receivable and for a payable.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from frappe.utils import flt

from erpnext.accounts.cash_basis import exceptions as reasons
from erpnext.accounts.cash_basis.deferrals import split_deferred_rows

PARTY_ACCOUNT_TYPES = ("Receivable", "Payable")
CASH_ACCOUNT_TYPES = ("Cash", "Bank")
DEFERRAL_VOUCHER_TYPE = "Process Deferred Accounting"
TAX_WITHHELD_REMARK = "TDS Deducted"
OBLIGATION_VOUCHER_TYPES = ("Sales Invoice", "Purchase Invoice", "Journal Entry")


def gl_amount(row) -> float:
	return float(row.debit or 0) - float(row.credit or 0)


def gl_amount_in_account_currency(row) -> float:
	return float(row.debit_in_account_currency or 0) - float(row.credit_in_account_currency or 0)


def party_sign(account_type: str) -> int:
	"""Factor that turns a GL amount on a party account into a PLE amount."""
	return 1 if account_type == "Receivable" else -1


@dataclass
class Line:
	"""A convertible line: the C rows of one voucher with the same account and dimensions."""

	key: tuple
	amount: float = 0.0
	dated_amounts: dict = field(default_factory=lambda: defaultdict(float))
	# A deferred line: the deferral is on the deferred account (key), the recognition on the
	# income or expense account of the item.
	recognition_key: tuple | None = None


@dataclass
class SelfSettlement:
	"""A part of the party amount that the invoice settles itself (section 6.6)."""

	amount: float  # PLE sign, account currency
	is_cash: bool
	contra_rows: list  # P&L rows for a non-cash part
	amount_company: float  # PLE sign, company currency


@dataclass
class Obligation:
	voucher_type: str
	voucher_no: str
	posting_date: object
	party_type: str
	party: str
	party_account: str
	account_type: str
	base: float  # B: PLE sign, account currency
	base_company: float  # PLE sign, company currency
	party_total: float  # GL sign, company currency
	convertible_total: float  # GL sign, company currency
	lines: list
	dimensions: dict
	self_settlements: list = field(default_factory=list)
	schedule_rows: list = field(default_factory=list)  # deferred schedule, removed on the cash basis

	@property
	def ratio(self) -> float:
		"""c: the convertible amount for each unit of the party amount, both GL sign."""
		return self.convertible_total / self.party_total if self.party_total else 0.0

	@property
	def is_credit(self) -> bool:
		return self.base < 0


@dataclass
class RowClasses:
	party: list = field(default_factory=list)
	self_party: list = field(default_factory=list)
	self_contra: list = field(default_factory=list)
	internal: list = field(default_factory=list)
	deferral: list = field(default_factory=list)
	deferred: list = field(default_factory=list)  # DeferredPiece: rows on a deferred account
	balance: list = field(default_factory=list)
	convertible: list = field(default_factory=list)
	party_without_party: bool = False


class ObligationBuilder:
	"""Builds one Obligation from the GL rows of a voucher, or records an exception."""

	def __init__(self, context, collector):
		self.ctx = context
		self.collector = collector

	def build(self, voucher_type, voucher_no, own_rows, gl_rows):
		first = own_rows[0]
		header = self.ctx.invoice_headers.get((voucher_type, voucher_no))
		amount = sum(flt(r.amount) for r in own_rows)

		def fail(reason):
			self.collector.add(
				voucher_type, voucher_no, first.posting_date, first.party_type, first.party, amount, reason
			)

		if first.party_type not in self.ctx.party_types:
			return fail(reasons.OTHER_PARTY_TYPE) if self.has_convertible_rows(gl_rows) else None
		if not gl_rows:
			# A PLE row with no GL row: the rows cannot be checked.
			return fail(reasons.PROOF_RULE_FAILED)
		classes = self.classify(gl_rows, first.party, header)
		if classes.party_without_party:
			return fail(reasons.PARTY_LINE_WITHOUT_PARTY)
		items = self.ctx.deferred_items.get((voucher_type, voucher_no))
		if not self.set_deferred_rows(classes, items, bool(header and header.is_return)):
			return fail(reasons.DEFERRED)
		parties = {(r.party_type, r.party) for r in classes.party + classes.self_party}
		accounts = {r.account for r in classes.party + classes.self_party}
		if not parties:
			# No party row in the GL rows: the rows cannot be checked against the party.
			return fail(reasons.PROOF_RULE_FAILED)
		if len(parties) != 1 or len(accounts) != 1:
			return fail(reasons.MULTIPLE_PARTIES)
		if (
			not self.sums_to_zero(classes.internal)
			or not self.sums_to_zero(classes.self_party + classes.self_contra)
			or not self.sums_to_zero(classes.deferral)
			or abs(
				sum(gl_amount(r) for r in classes.party + classes.balance + classes.convertible)
				+ sum(piece.amount for piece in classes.deferred)
			)
			> self.ctx.precision_tolerance
		):
			return fail(reasons.PROOF_RULE_FAILED)

		obligation = self.make_obligation(voucher_type, voucher_no, first, classes)
		obligation.schedule_rows = classes.deferral + self.ctx.schedule_journal_rows.get(
			(voucher_type, voucher_no), []
		)
		if not obligation.base:
			return None
		if header and classes.self_party:
			settlements = self.get_self_settlements(obligation, classes, header)
			if settlements is None:
				return fail(reasons.SELF_SETTLEMENT_MISMATCH)
			obligation.self_settlements = settlements
		return obligation

	def classify(self, gl_rows, party, header) -> RowClasses:
		classes = RowClasses()
		obligation_sign = -1 if header and header.is_return else 1
		# The party row of tax withheld at source names its tax account in "against".
		withheld_accounts = set().union(
			*(against_names(r) for r in gl_rows if r.party and r.remarks == TAX_WITHHELD_REMARK)
		)
		contra_accounts = withheld_accounts | self.self_settlement_accounts(gl_rows, header)
		for row in gl_rows:
			account = self.ctx.accounts[row.account]
			if account.account_type in PARTY_ACCOUNT_TYPES:
				self.classify_party_row(row, account, header, obligation_sign, contra_accounts, classes)
			elif row.against_voucher_type == DEFERRAL_VOUCHER_TYPE:
				classes.deferral.append(row)
			elif row.account in contra_accounts:
				classes.self_contra.append(row)
			elif party not in against_names(row):
				classes.internal.append(row)
			elif account.report_type == "Profit and Loss":
				classes.convertible.append(row)
			else:
				classes.balance.append(row)
		return classes

	def set_deferred_rows(self, classes, items, is_return) -> bool:
		"""Move the rows on the deferred accounts of the items to deferred lines (phase 7).

		False when the voucher has schedule rows but no deferred item, or an item has no row.
		"""
		if not items:
			return not classes.deferral
		split = split_deferred_rows(classes.balance, items, self.ctx.precision, is_return)
		if split is None:
			return False
		classes.deferred, classes.balance = split
		return True

	def classify_party_row(self, row, account, header, obligation_sign, contra_accounts, classes):
		if not row.party:
			classes.party_without_party = True
		elif row.remarks == TAX_WITHHELD_REMARK or against_names(row) & contra_accounts:
			# A payment, change, write-off or loyalty row names its contra account in "against".
			classes.self_party.append(row)
		elif (
			header
			and has_self_settlement(header)
			and (party_sign(account.account_type) * gl_amount(row) * obligation_sign < 0)
		):
			classes.self_party.append(row)
		else:
			classes.party.append(row)

	def self_settlement_accounts(self, gl_rows, header) -> set[str]:
		"""The contra accounts of the self-settlement of an invoice (section 6.6)."""
		if not header or not has_self_settlement(header):
			return set()
		accounts = set()
		for row in gl_rows:
			account = self.ctx.accounts[row.account]
			if account.account_type not in PARTY_ACCOUNT_TYPES and is_self_settlement_contra(
				row, account, header
			):
				accounts.add(row.account)
		return accounts

	def make_obligation(self, voucher_type, voucher_no, first, classes) -> Obligation:
		party_row = classes.party[0] if classes.party else classes.self_party[0]
		account_type = self.ctx.accounts[party_row.account].account_type
		sign = party_sign(account_type)
		lines = group_lines(classes.convertible, self.ctx.dimension_fields) + group_deferred_lines(
			classes.deferred, self.ctx.dimension_fields
		)
		return Obligation(
			voucher_type=voucher_type,
			voucher_no=voucher_no,
			posting_date=self.ctx.voucher_dates.get((voucher_type, voucher_no), first.posting_date),
			party_type=party_row.party_type,
			party=party_row.party,
			party_account=party_row.account,
			account_type=account_type,
			base=sign * sum(gl_amount_in_account_currency(r) for r in classes.party),
			base_company=sign * sum(gl_amount(r) for r in classes.party),
			party_total=sum(gl_amount(r) for r in classes.party),
			convertible_total=sum(line.amount for line in lines),
			lines=lines,
			dimensions=dimensions_of(party_row, self.ctx.dimension_fields),
		)

	def get_self_settlements(self, obligation, classes, header) -> list | None:
		"""Split the self-settlement of an invoice into cash and non-cash parts (section 6.6)."""
		sign = party_sign(obligation.account_type)
		to_account_currency = obligation.base / obligation.base_company if obligation.base_company else 1
		cash = 0.0
		non_cash = defaultdict(list)
		for row in classes.self_contra:
			account = self.ctx.accounts[row.account]
			if account.report_type == "Profit and Loss":
				non_cash[row.account].append(row)
			else:
				cash += sign * gl_amount(row)

		settlements = []
		if cash:
			settlements.append(SelfSettlement(cash * to_account_currency, True, [], amount_company=cash))
		for rows in non_cash.values():
			amount = sum(sign * gl_amount(r) for r in rows)
			settlements.append(
				SelfSettlement(amount * to_account_currency, False, rows, amount_company=amount)
			)

		withheld = [r for r in classes.self_party if r.remarks == TAX_WITHHELD_REMARK]
		expected = get_expected_self_settlement(header) + abs(sum(gl_amount(r) for r in withheld))
		actual = sum(sign * gl_amount(r) for r in classes.self_party)
		if abs(abs(actual) - abs(expected)) > self.ctx.precision_tolerance:
			return None
		return settlements

	def has_convertible_rows(self, gl_rows) -> bool:
		return any(self.ctx.accounts[r.account].report_type == "Profit and Loss" for r in gl_rows)

	def sums_to_zero(self, rows) -> bool:
		return abs(sum(gl_amount(r) for r in rows)) <= self.ctx.precision_tolerance


def has_self_settlement(header) -> bool:
	return bool(
		header.get("is_pos")
		or header.get("is_paid")
		or flt(header.get("write_off_amount"))
		or flt(header.get("loyalty_amount"))
	)


def is_self_settlement_contra(row, account, header) -> bool:
	if (header.get("is_pos") or header.get("is_paid")) and account.account_type in CASH_ACCOUNT_TYPES:
		return True
	if flt(header.get("write_off_amount")) and row.account == header.get("write_off_account"):
		return True
	return bool(flt(header.get("loyalty_amount")) and row.account == header.get("loyalty_redemption_account"))


def get_expected_self_settlement(header) -> float:
	"""The total that the invoice settles itself, from the document, in the company currency."""
	paid = 0.0
	if header.get("is_pos") or header.get("is_paid"):
		paid = flt(header.base_paid_amount) - flt(header.get("base_change_amount"))
	loyalty = flt(header.get("loyalty_amount")) * flt(header.get("conversion_rate") or 1)
	return paid + flt(header.get("base_write_off_amount")) + loyalty


def against_names(row) -> set[str]:
	return {name.strip() for name in (row.against or "").split(",") if name.strip()}


def group_lines(rows, dimension_fields) -> list[Line]:
	lines: dict[tuple, Line] = {}
	for row in rows:
		key = line_key(row, dimension_fields)
		line = lines.setdefault(key, Line(key))
		amount = gl_amount(row)
		line.amount += amount
		line.dated_amounts[row.posting_date] += amount
	return list(lines.values())


def group_deferred_lines(pieces, dimension_fields) -> list[Line]:
	lines: dict[tuple, Line] = {}
	for piece in pieces:
		key = line_key(piece.row, dimension_fields)
		recognition_key = (piece.account, *key[1:])
		line = lines.setdefault((key, recognition_key), Line(key, recognition_key=recognition_key))
		line.amount += piece.amount
		line.dated_amounts[piece.row.posting_date] += piece.amount
	return list(lines.values())


def line_key(row, dimension_fields) -> tuple:
	return (
		row.account,
		row.cost_center,
		row.project,
		row.finance_book,
		*(row.get(fieldname) for fieldname in dimension_fields),
	)


def dimensions_of(row, dimension_fields) -> dict:
	values = {"cost_center": row.cost_center, "project": row.project, "finance_book": row.finance_book}
	values.update({fieldname: row.get(fieldname) for fieldname in dimension_fields})
	return values
