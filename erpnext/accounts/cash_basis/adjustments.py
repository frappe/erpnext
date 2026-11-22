# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Adjustment rows (section 6.5, 6.7, 6.10). Each adjustment is a pair with opposite signs."""

from collections import defaultdict

from frappe.utils import flt, getdate

from erpnext.accounts.cash_basis.obligations import gl_amount, party_sign

DEFERRAL = "Cash basis: deferral"
SCHEDULE_REMOVAL = "Cash basis: deferred schedule removed"
RECOGNITION = "Cash basis: recognition"
NON_CASH = "Cash basis: non-cash settlement"
UNAPPLIED = "Cash basis: unapplied cash"
REVALUATION = "Cash basis: unrealised exchange difference"
PERIOD_CLOSING = "Cash basis: period closing"


class AdjustmentBuilder:
	def __init__(self, context):
		self.ctx = context
		self.rows: list[dict] = []

	def build(self, obligations, events, unapplied_rows, revaluation_journals) -> list[dict]:
		events_by_obligation = defaultdict(list)
		for event in events:
			events_by_obligation[(event.obligation.voucher_type, event.obligation.voucher_no)].append(event)
		for key, obligation in obligations.items():
			self.add_deferral(obligation)
			self.add_schedule_removal(obligation)
			self.add_recognition(obligation, events_by_obligation.get(key, []))
		for event in events:
			if not event.settler.is_cash and not event.settler.is_link:
				self.add_non_cash_removal(event)
		if self.ctx.unapplied_accounts:
			self.add_unapplied(unapplied_rows, events)
		for voucher_no in revaluation_journals:
			self.add_revaluation_removal(voucher_no)
		for closing_voucher in self.ctx.period_closing_vouchers:
			self.add_closing_transfer(closing_voucher)
		return self.rows

	def add_closing_transfer(self, closing_voucher):
		"""Section 6.11: a PCV closes the cash basis P&L of its period to its closing account.

		The rows have the voucher type of the PCV, so a report that ignores closing entries
		ignores them too.
		"""
		start, end = getdate(closing_voucher.period_start_date), getdate(closing_voucher.period_end_date)
		dimension_keys = ("cost_center", "project", "finance_book", *self.ctx.dimension_fields)
		totals = defaultdict(float)
		for row in self.rows:
			if row["voucher_type"] == "Period Closing Voucher" or not (start <= row["posting_date"] <= end):
				continue
			if self.ctx.accounts[row["account"]].report_type == "Profit and Loss":
				# The accrual PCV closes each dimension combination, so the transfer does too.
				key = (row["account"], tuple(row.get(field) for field in dimension_keys))
				totals[key] += row["debit"] - row["credit"]
		for (account, values), amount in sorted(totals.items(), key=lambda item: str(item[0])):
			dimensions = dict(zip(dimension_keys, values, strict=True))
			common = (
				end,
				None,
				None,
				dimensions,
				PERIOD_CLOSING,
				"Period Closing Voucher",
				closing_voucher.name,
			)
			self.append(account, -amount, *common)
			self.append(closing_voucher.closing_account_head, amount, *common)

	def add_deferral(self, obligation):
		"""Rule 1: remove each convertible row on its own date."""
		for line in obligation.lines:
			for posting_date, amount in line.dated_amounts.items():
				self.add_pair(
					obligation,
					line.key,
					-amount,
					posting_date,
					DEFERRAL,
					obligation.voucher_type,
					obligation.voucher_no,
				)

	def add_recognition(self, obligation, events):
		"""Rule 2: recognise the lines in proportion to the cash settled.

		Each target is the rounded cumulative amount, not a sum of rounded parts. When the cash
		settled reaches the base, the target is the line itself, so no rounding remainder stays.
		"""
		weighted = 0.0
		recognised = defaultdict(float)
		for event in events:
			weighted += event.amount * event.weight
			ratio = weighted / obligation.base
			for line in obligation.lines:
				target = flt(line.amount * ratio, self.ctx.precision)
				# Two deferred lines can share the deferred account, so the identity is both keys.
				identity = (line.key, line.recognition_key)
				delta = flt(target - recognised[identity], self.ctx.precision)
				if not delta:
					continue
				recognised[identity] = target
				self.add_pair(
					obligation,
					line.recognition_key or line.key,
					delta,
					event.recognition_date,
					RECOGNITION,
					event.settler.voucher_type,
					event.settler.voucher_no,
				)

	def add_schedule_removal(self, obligation):
		"""Phase 7: remove each row of the deferred schedule on its own date.

		Each schedule entry is balanced (the deferred account against the income or expense
		account), so the removal rows of one entry are a pair.
		"""
		for row in obligation.schedule_rows:
			self.append(
				row.account,
				-gl_amount(row),
				row.posting_date,
				None,
				None,
				self.row_dimensions(row),
				SCHEDULE_REMOVAL,
				row.voucher_type,
				row.voucher_no,
				obligation.voucher_type,
				obligation.voucher_no,
			)

	def add_non_cash_removal(self, event):
		"""Rule 3: remove the P&L contra rows of a non-cash settler in the proportion c of the obligation,
		and the deferred rows of a return in full for the share."""
		settler = event.settler
		# A row of a return on a deferred account goes to zero on the cash basis, as the deferred
		# line of V does (rule 6): it is removed in full, for the share of this settlement.
		removals = [(row, event.share) for row in settler.deferred_rows]
		if settler.ratio and settler.contra_rows:
			factor = event.share * event.obligation.ratio / settler.ratio
			removals += [(row, factor) for row in settler.contra_rows]
		for row, factor in removals:
			amount = flt(-gl_amount(row) * factor, self.ctx.precision)
			if amount:
				key = (
					row.account,
					row.cost_center,
					row.project,
					row.finance_book,
					*self.dimension_values(row),
				)
				self.add_pair(
					event.obligation,
					key,
					amount,
					settler.posting_date,
					NON_CASH,
					settler.voucher_type,
					settler.voucher_no,
				)

	def add_unapplied(self, unapplied_rows, events):
		"""Section 6.7: unapplied cash shows on the unapplied account until its recognition date."""
		consumed = defaultdict(float)
		for event in events:
			if not event.pays_cash:
				continue
			for account, amount in event.consumed_by_account.items():
				consumed[(event.settler.voucher_type, event.settler.voucher_no, account)] += amount
		for row in unapplied_rows:
			amount = row.amount
			if amount > 0:
				key = (row.voucher_type, row.voucher_no, row.account)
				used = min(amount, consumed[key])
				consumed[key] -= used
				amount -= used
			if abs(amount) > self.ctx.precision_tolerance:
				self.add_unapplied_pair(row.party_type, row.party, row.account, -amount, row.cash_date, row)

		for event in events:
			if event.settler.voucher_type not in ("Payment Entry", "Journal Entry") or not event.pays_cash:
				continue
			recognition_date, cash_date = event.recognition_date, getdate(event.cash_date)
			for account, amount in event.consumed_by_account.items():
				self.add_unapplied_pair(
					event.obligation.party_type,
					event.obligation.party,
					account,
					-amount,
					recognition_date,
					event,
				)
			rest = event.amount_company - event.consumed if event.settler.is_cash else 0.0
			if recognition_date > cash_date and abs(rest) > self.ctx.precision_tolerance:
				party = (event.obligation.party_type, event.obligation.party)
				self.add_unapplied_pair(*party, event.account, rest, cash_date, event)
				self.add_unapplied_pair(*party, event.account, -rest, recognition_date, event)

	def add_unapplied_pair(self, party_type, party, account, received, posting_date, source):
		"""received > 0 moves cash onto the unapplied account; received < 0 moves it off."""
		unapplied_account = self.ctx.unapplied_accounts[party_type]
		party_amount = party_sign(self.ctx.accounts[account].account_type) * received
		voucher_type, voucher_no = self.source_voucher(source)
		dimensions = {fieldname: None for fieldname in self.ctx.dimension_fields}
		dimensions["cost_center"] = getattr(source, "cost_center", None) or self.ctx.default_cost_center
		self.append(
			unapplied_account,
			-party_amount,
			posting_date,
			None,
			None,
			dimensions,
			UNAPPLIED,
			voucher_type,
			voucher_no,
		)
		self.append(
			account,
			party_amount,
			posting_date,
			party_type,
			party,
			dimensions,
			UNAPPLIED,
			voucher_type,
			voucher_no,
		)

	def add_revaluation_removal(self, voucher_no):
		"""Section 6.10: an unrealised difference on a party account does not belong on a cash basis."""
		rows = self.ctx.gl_rows.get(("Journal Entry", voucher_no), [])
		party_rows = [
			r
			for r in rows
			if r.party and self.ctx.accounts[r.account].account_type in ("Receivable", "Payable")
		]
		pl_rows = [r for r in rows if self.ctx.accounts[r.account].report_type == "Profit and Loss"]
		pl_total = sum(gl_amount(r) for r in pl_rows)
		if not party_rows or not pl_total:
			return
		for party_row in party_rows:
			amount = gl_amount(party_row)
			for pl_row in pl_rows:
				part = flt(amount * gl_amount(pl_row) / pl_total, self.ctx.precision)
				dims = self.row_dimensions(pl_row)
				self.append(
					pl_row.account,
					part,
					pl_row.posting_date,
					None,
					None,
					dims,
					REVALUATION,
					"Journal Entry",
					voucher_no,
				)
				self.append(
					party_row.account,
					-part,
					pl_row.posting_date,
					party_row.party_type,
					party_row.party,
					dims,
					REVALUATION,
					"Journal Entry",
					voucher_no,
				)

	def add_pair(self, obligation, key, amount, posting_date, remark, against_type, against_no):
		amount = flt(amount, self.ctx.precision)
		if not amount:
			return
		account, cost_center, project, finance_book, *dimension_values = key
		dimensions = {"cost_center": cost_center, "project": project, "finance_book": finance_book}
		dimensions.update(dict(zip(self.ctx.dimension_fields, dimension_values, strict=True)))
		common = (
			posting_date,
			remark,
			obligation.voucher_type,
			obligation.voucher_no,
			against_type,
			against_no,
		)
		self.append(account, amount, common[0], None, None, dimensions, *common[1:])
		self.append(
			obligation.party_account,
			-amount,
			common[0],
			obligation.party_type,
			obligation.party,
			dimensions,
			*common[1:],
		)

	def append(
		self,
		account,
		amount,
		posting_date,
		party_type,
		party,
		dimensions,
		remark,
		voucher_type,
		voucher_no,
		against_type=None,
		against_no=None,
	):
		amount = flt(amount, self.ctx.precision)
		if not amount:
			return
		self.rows.append(
			{
				"account": account,
				"posting_date": getdate(posting_date),
				"debit": amount if amount > 0 else 0.0,
				"credit": -amount if amount < 0 else 0.0,
				"party_type": party_type,
				"party": party,
				"voucher_type": voucher_type,
				"voucher_no": voucher_no,
				"against_voucher_type": against_type,
				"against_voucher": against_no,
				"remarks": remark,
				"is_opening": "No",
				"company": self.ctx.company,
				"is_cash_adjustment": 1,
				**{"cost_center": None, "project": None, "finance_book": None},
				**dimensions,
			}
		)

	def source_voucher(self, source):
		if hasattr(source, "settler"):
			return source.settler.voucher_type, source.settler.voucher_no
		return source.voucher_type, source.voucher_no

	def dimension_values(self, row):
		return [row.get(fieldname) for fieldname in self.ctx.dimension_fields]

	def row_dimensions(self, row):
		values = {"cost_center": row.cost_center, "project": row.project, "finance_book": row.finance_book}
		values.update({fieldname: row.get(fieldname) for fieldname in self.ctx.dimension_fields})
		return values
