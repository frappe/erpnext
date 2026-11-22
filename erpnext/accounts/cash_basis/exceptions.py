# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Exceptions: vouchers and settlements that the calculation cannot classify.

The calculation never drops or guesses an exception: it lists it. A voucher that is an exception
stays accrual. A mixed settlement is treated as cash, and listed (section 6.4).
"""

from dataclasses import asdict, dataclass, replace

from frappe import _

MULTIPLE_PARTIES = "multiple parties"
PROOF_RULE_FAILED = "proof rule failed"
DEFERRED = "deferred revenue or expense"
MIXED_SETTLEMENT = "mixed settlement"
SELF_SETTLEMENT_MISMATCH = "self-settlement mismatch"
PARTY_LINE_WITHOUT_PARTY = "party line without party"
OTHER_PARTY_TYPE = "other party type"

REASONS = (
	MULTIPLE_PARTIES,
	PROOF_RULE_FAILED,
	DEFERRED,
	MIXED_SETTLEMENT,
	SELF_SETTLEMENT_MISMATCH,
	PARTY_LINE_WITHOUT_PARTY,
	OTHER_PARTY_TYPE,
)


def get_reason_label(reason: str) -> str:
	return {
		MULTIPLE_PARTIES: _("Multiple parties"),
		PROOF_RULE_FAILED: _("Proof rule failed"),
		DEFERRED: _("Deferred revenue or expense"),
		MIXED_SETTLEMENT: _("Mixed settlement"),
		SELF_SETTLEMENT_MISMATCH: _("Self-settlement mismatch"),
		PARTY_LINE_WITHOUT_PARTY: _("Party line without party"),
		OTHER_PARTY_TYPE: _("Other party type"),
	}[reason]


@dataclass(frozen=True)
class CashBasisException:
	voucher_type: str
	voucher_no: str
	posting_date: object
	party_type: str | None
	party: str | None
	amount: float
	reason: str

	def as_dict(self) -> dict:
		return asdict(self)


class ExceptionCollector:
	"""Collects each exception one time, for each voucher and reason.

	A settling voucher with an exception can settle several obligations. Its amount is the total.
	"""

	def __init__(self):
		self._items: dict[tuple, CashBasisException] = {}

	def add(self, voucher_type, voucher_no, posting_date, party_type, party, amount, reason):
		if reason not in REASONS:
			raise ValueError(f"Unknown cash basis exception reason: {reason}")
		key = (voucher_type, voucher_no, reason)
		if key in self._items:
			item = self._items[key]
			same_party = (item.party_type, item.party) == (party_type, party)
			self._items[key] = replace(
				item,
				amount=item.amount + amount,
				party_type=item.party_type if same_party else None,
				party=item.party if same_party else None,
			)
		else:
			self._items[key] = CashBasisException(
				voucher_type, voucher_no, posting_date, party_type, party, amount, reason
			)

	def as_list(self) -> list[dict]:
		items = sorted(
			self._items.values(), key=lambda e: (str(e.posting_date), e.voucher_type, e.voucher_no)
		)
		return [item.as_dict() for item in items]
