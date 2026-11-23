# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""The link between the financial reports and the cash basis calculation.

One job: give each converting report the adjustment rows of one calculation for each company,
in the shape it reads: the statements, Trial Balance, Cash Flow, the template engine, the
General Ledger, the consolidated reports, Profitability Analysis, Dimension-wise Accounts
Balance, and Financial Ratios.

A report that converts calls resolve_accounting_method at the start of execute. The shared
functions convert only when that resolved value is Cash, so a report that does not convert
stays accrual, also for a company with the default Cash.
"""

from datetime import datetime, time
from urllib.parse import quote, urlencode

import frappe
from frappe import _
from frappe.query_builder.functions import Max, Substring
from frappe.utils import add_days, escape_html, flt, fmt_money, get_url_to_report_with_filters, getdate

from erpnext.accounts.cash_basis import ACCRUAL, CASH, get_accounting_method, is_cash_method_available
from erpnext.accounts.cash_basis.adjustments import (
	DEFERRAL,
	NON_CASH,
	PERIOD_CLOSING,
	RECOGNITION,
	REVALUATION,
	SCHEDULE_REMOVAL,
	UNAPPLIED,
)

CACHE_KEY = "_cash_basis_result"
RESOLVED_KEY = "_cash_basis_resolved"
REPORT_END_KEY = "_cash_basis_report_end"
PRIVATE_KEYS = (CACHE_KEY, RESOLVED_KEY, REPORT_END_KEY)
# A request cannot send this object, so a client cannot mark a report run as converting.
# A deep copy or a JSON round trip of the filters does not keep it: such a copy runs as accrual.
RESOLVED = object()
PERIOD_CLOSING_VOUCHER = "Period Closing Voucher"


def resolve_accounting_method(filters) -> bool:
	"""Set the method of this report run on the filters, and mark the run as converting.

	Return True for Cash.
	"""
	filters.accounting_method = get_accounting_method(filters)
	for key in PRIVATE_KEYS:
		filters.pop(key, None)
	if filters.accounting_method != CASH:
		return False
	filters[RESOLVED_KEY] = RESOLVED
	filters[CACHE_KEY] = {}
	return True


def without_private_keys(filters) -> dict:
	"""The filters as SQL parameters: the private keys of a cash basis run are not values."""
	return {key: value for key, value in filters.items() if key not in PRIVATE_KEYS}


def uses_cash_basis(filters) -> bool:
	"""True only for a report run that resolved the method Cash at the start of execute."""
	return (
		bool(filters) and filters.get(RESOLVED_KEY) is RESOLVED and filters.get("accounting_method") == CASH
	)


def set_report_end(filters, report_end):
	"""Each converting report states its own last date, after it builds its periods.

	The filters do not always hold it: in Fiscal Year mode, period_end_date is the hidden
	date of the page, not the end of the selected years.
	"""
	if uses_cash_basis(filters):
		filters[REPORT_END_KEY] = getdate(report_end)


def get_report_result(filters, to_date, company=None):
	"""One calculation for each company of a report run, at the last date of the report.

	The filters hold it. Each slice of the report (an opening, a period) cuts this one result
	by date, as a multi-period Profit and Loss does. company: a company of a consolidated
	report; a company outside the rollout scope gets no result (None).
	"""
	from erpnext.accounts.cash_basis.calculation import CashBasisCalculation
	from erpnext.accounts.cash_basis.settings import get_unapplied_settings

	cache = filters.setdefault(CACHE_KEY, {})
	calculation_date = filters.get(REPORT_END_KEY) or getdate(to_date)
	if getdate(to_date) > calculation_date:
		frappe.throw(
			_("A cash basis report asked for {0}, after its own last date {1}.").format(
				getdate(to_date), calculation_date
			),
			title=_("Cash Basis Report Error"),
		)
	company = company or filters.company
	if (
		company != filters.company
		and get_accounting_method({"company": company, "accounting_method": CASH}) != CASH
	):
		return None
	if cache.get("date") != calculation_date:
		cache.clear()
		cache["date"] = calculation_date
	key = ("result", company)
	if key not in cache:
		cache[key] = CashBasisCalculation(company, calculation_date, **get_unapplied_settings(company)).run()
	return cache[key]


def get_report_adjustments(
	filters,
	from_date,
	to_date,
	root_lft=None,
	root_rgt=None,
	root_type=None,
	ignore_closing_entries=False,
	group_by_account=False,
) -> list[frappe._dict]:
	"""Adjustment rows in the shape of the GL rows of set_gl_entries_by_account.

	A report calls this for each root account. The rows of one date range are made one time.
	"""
	entries = get_dated_entries(filters, from_date, to_date, ignore_closing_entries)
	accounts = get_leaf_accounts(filters.company, root_lft, root_rgt, root_type)
	# Copies: the conversion to the presentation currency changes the rows in place.
	entries = [frappe._dict(entry) for entry in entries if entry.account in accounts]
	return group_entries_by_account(entries) if group_by_account else entries


def get_dated_entries(
	filters, from_date, to_date, ignore_closing_entries, company=None
) -> list[frappe._dict]:
	from erpnext.accounts.cash_basis.calculation import filter_and_group

	company = company or filters.company
	result = get_report_result(filters, to_date, company)
	if result is None:
		return []
	cache = filters[CACHE_KEY]
	key = ("entries", company, str(from_date), str(getdate(to_date)), bool(ignore_closing_entries))
	if key not in cache:
		rows = filter_and_group(result.rows, from_date, to_date, "row", company, filters)
		if ignore_closing_entries:
			rows = [r for r in rows if r["voucher_type"] != PERIOD_CLOSING_VOUCHER]
		currency = frappe.get_cached_value("Company", company, "default_currency")
		rate_of = get_reporting_rates(filters, company, result)
		cache[key] = [to_gl_entry(row, currency, rate_of) for row in rows]
	return cache[key]


def to_gl_entry(row, currency, rate_of=None) -> frappe._dict:
	"""rate_of: a function from an adjustment row to its reporting rate."""
	entry = frappe._dict(row)
	entry.account_currency = currency
	entry.debit_in_account_currency = entry.debit
	entry.credit_in_account_currency = entry.credit
	rate = rate_of(entry) if rate_of else 0.0
	entry.debit_in_reporting_currency = flt(flt(entry.debit) * rate)
	entry.credit_in_reporting_currency = flt(flt(entry.credit) * rate)
	return entry


def get_reporting_rates(filters, company, result):
	"""A function from an adjustment row to the reporting rate of the company for that row.

	As GL Entry.set_amount_in_reporting_currency, the rate is the rate of the posting date of
	the row. The GL Entries keep that rate, and two vouchers of one date can keep different
	rates. Thus the rate of a row is, in this order: the rate of its voucher on its date (a
	deferral, a revaluation), the rate of its against voucher on its date (a recognition has the
	payment as the against voucher and the payment date), the highest rate of the date, and the
	exchange rate of the date. The queries run once for each company and run.
	"""
	currency, reporting_currency = frappe.get_cached_value(
		"Company", company, ["default_currency", "reporting_currency"]
	)
	if not reporting_currency:
		return None
	if reporting_currency == currency:
		return lambda entry: 1.0
	cache = filters[CACHE_KEY]
	key = ("rates", company)
	if key not in cache:
		dates = sorted({getdate(row["posting_date"]) for row in result.rows})
		vouchers = {row["voucher_no"] for row in result.rows}
		vouchers.update(row["against_voucher"] for row in result.rows if row.get("against_voucher"))
		by_voucher = get_voucher_reporting_rates(company, dates, vouchers)
		by_date = get_date_reporting_rates(company, dates)

		def rate_of(entry):
			posting_date = getdate(entry.posting_date)
			for voucher in (
				(entry.voucher_type, entry.voucher_no),
				(entry.get("against_voucher_type"), entry.get("against_voucher")),
			):
				if (rate := by_voucher.get((*voucher, posting_date))) is not None:
					return rate
			if posting_date not in by_date:
				by_date[posting_date] = get_reporting_rate(currency, reporting_currency, posting_date)
			return by_date[posting_date]

		cache[key] = rate_of
	return cache[key]


def get_voucher_reporting_rates(company, dates, vouchers) -> dict:
	"""The reporting rate of each voucher of the adjustment rows on each of the dates."""
	from erpnext.accounts.cash_basis.queries import batches

	gle = frappe.qb.DocType("GL Entry")
	rates = {}
	if not dates:
		return rates
	for batch in batches(sorted(vouchers)):
		for posting_date, voucher_type, voucher_no, rate in (
			frappe.qb.from_(gle)
			.select(
				gle.posting_date, gle.voucher_type, gle.voucher_no, Max(gle.reporting_currency_exchange_rate)
			)
			.where(
				(gle.company == company)
				& (gle.is_cancelled == 0)
				& gle.posting_date.isin(dates)
				& gle.voucher_no.isin(batch)
			)
			.groupby(gle.posting_date, gle.voucher_type, gle.voucher_no)
			.run()
		):
			if flt(rate):
				rates[(voucher_type, voucher_no, getdate(posting_date))] = flt(rate)
	return rates


def get_date_reporting_rates(company, dates) -> dict:
	"""The highest reporting rate of the GL Entries of the company on each of the dates."""
	if not dates:
		return {}
	gle = frappe.qb.DocType("GL Entry")
	return {
		getdate(posting_date): flt(rate)
		for posting_date, rate in (
			frappe.qb.from_(gle)
			.select(gle.posting_date, Max(gle.reporting_currency_exchange_rate))
			.where((gle.company == company) & (gle.is_cancelled == 0) & gle.posting_date.isin(dates))
			.groupby(gle.posting_date)
			.run()
		)
		if flt(rate)
	}


@frappe.request_cache
def get_reporting_rate(currency, reporting_currency, posting_date) -> float:
	"""The exchange rate of a date with no GL Entry of the company."""
	from erpnext.setup.utils import get_exchange_rate

	return flt(get_exchange_rate(currency, reporting_currency, posting_date))


def group_entries_by_account(entries) -> list[frappe._dict]:
	grouped = {}
	for entry in entries:
		total = grouped.setdefault(
			entry.account,
			frappe._dict(
				account=entry.account,
				debit=0.0,
				credit=0.0,
				debit_in_account_currency=0.0,
				credit_in_account_currency=0.0,
				debit_in_reporting_currency=0.0,
				credit_in_reporting_currency=0.0,
				account_currency=entry.account_currency,
				posting_date=entry.posting_date,
				is_opening="No",
				fiscal_year=entry.fiscal_year,
				is_cash_adjustment=1,
			),
		)
		for field in (
			"debit",
			"credit",
			"debit_in_account_currency",
			"credit_in_account_currency",
			"debit_in_reporting_currency",
			"credit_in_reporting_currency",
		):
			total[field] += flt(entry.get(field))
		if entry.posting_date > total.posting_date:
			total.posting_date, total.fiscal_year = entry.posting_date, entry.fiscal_year
	return list(grouped.values())


@frappe.request_cache
def get_leaf_accounts(company, root_lft=None, root_rgt=None, root_type=None) -> set[str]:
	filters = {"company": company, "is_group": 0}
	if root_lft and root_rgt:
		filters.update({"lft": (">=", root_lft), "rgt": ("<=", root_rgt)})
	if root_type:
		filters["root_type"] = root_type
	return set(frappe.get_all("Account", filters=filters, pluck="name"))


def get_report_message(
	filters, to_date, balance_sheet=False, from_date=None, companies=None, others=()
) -> str | None:
	"""The alert of a report run: the method, and on Cash the exceptions and the BS note.

	companies: the companies of a consolidated report, each with its own result. others: the
	filters of other runs of the same report (Consolidated Trial Balance runs one per company).
	"""
	runs = [f for f in (filters, *others) if uses_cash_basis(f)]
	if not runs:
		return get_accrual_message(filters, companies or [run.get("company") for run in (filters, *others)])
	by_company = {}
	for run in runs:
		for company in companies or [run.company]:
			result = get_report_result(run, to_date, company)
			if result and result.exceptions:
				by_company.setdefault(company, []).extend(result.exceptions)
	method = _("Income and expenses are reported when they are paid.")
	if balance_sheet:
		method = _(
			"Income and expenses are reported when they are paid, and receivables and payables show only the tax of unpaid invoices, because tax stays on the accrual basis."
		)
	lines = [escape_html(method)]
	actions = []
	consolidated = bool(companies or others)
	for company, exceptions in by_company.items():
		summary = escape_html(get_exceptions_summary(company, exceptions))
		url = get_reconciliation_url(runs[0], company, to_date, from_date)
		if consolidated:
			# A consolidated report has one line and one button for each company.
			lines.append(f"{frappe.bold(escape_html(company))}: {summary}")
			actions.append((_("Review {0}").format(company), url))
		else:
			lines.append(summary)
			actions.append((_("Review"), url))
	return get_alert_html(_("Accounting Method: Cash"), lines, actions)


def get_accrual_message(filters, companies) -> str | None:
	"""The alert of an accrual run, for a company that can also report on Cash.

	A company outside the rollout scope has no method to choose, so its reports show no alert.
	"""
	if not filters or filters.get("accounting_method") != ACCRUAL:
		return None
	if not any(isinstance(company, str) and is_cash_method_available(company) for company in companies):
		return None
	lines = [escape_html(_("Income and expenses are reported when they are invoiced."))]
	return get_alert_html(_("Accounting Method: Accrual"), lines)


def get_alert_html(title, lines, actions=()) -> str:
	"""The Espresso info alert of frappe.ui.alert as a banner, built on the server for the report message.

	Each line is HTML. actions: (label, url) pairs, shown as buttons under the lines.
	The info alert is also used when vouchers need review: the method is information, not a warning.
	"""
	icon = '<svg class="icon icon-sm" stroke="currentColor" aria-hidden="true"><use href="#icon-info-solid"></use></svg>'
	head = f'{icon}<span class="es-alert__title">{escape_html(title)}</span>'
	body = "".join(f'<p class="es-alert__description">{line}</p>' for line in lines)
	if actions:
		buttons = "".join(
			'<a class="es-button es-alert__action" data-variant="outline" '
			f'data-size="md" href="{escape_html(url)}">{escape_html(label)}</a>'
			for label, url in actions
		)
		body += f'<div class="es-alert__actions">{buttons}</div>'
	return (
		f'<div class="es-alert" role="alert" data-layout="banner" data-theme="blue">'
		f'<div class="es-alert__head">{head}</div><div class="es-alert__body">{body}</div></div>'
	)


def get_exceptions_summary(company, exceptions) -> str:
	"""The count and the total of the exceptions of one company, in its currency."""
	total = fmt_money(
		sum(flt(e["amount"]) for e in exceptions),
		currency=frappe.get_cached_value("Company", company, "default_currency"),
	)
	count = len(exceptions)
	message = (
		_("{0} voucher needs review (total {1})") if count == 1 else _("{0} vouchers need review (total {1})")
	)
	return message.format(count, total)


def get_reconciliation_url(filters, company, to_date, from_date) -> str:
	"""The Cash Basis Reconciliation of one company, for the period of the report."""
	return get_url_to_report_with_filters(
		"Cash Basis Reconciliation",
		urlencode(
			{
				"company": company,
				"from_date": str(getdate(from_date or filters.get("from_date") or to_date)),
				"to_date": str(getdate(to_date)),
				"finance_book": filters.get("finance_book") or "",
				"include_default_book_entries": filters.get("include_default_book_entries") or 0,
			},
			quote_via=quote,
		),
	)


def get_opening_entries(
	filters,
	report_type,
	from_date,
	year_start_date=None,
	include_closing=False,
	closing_date=None,
	ignore_reporting_currency=True,
) -> list[frappe._dict]:
	"""Adjustment rows before from_date, for the opening of Trial Balance (get_rootwise_opening_balances).

	The rules follow get_opening_balance: a P&L opening from the GL starts at the year start
	unless show_unclosed_fy_pl_balances is set, and the closing rows count only on request.
	On the path with Account Closing Balance (closing_date), the closing balance of a P&L
	account holds its full history to that date, so the adjustment rows to that date all count.
	"""
	to_date = add_days(from_date, -1)
	ignore_closing = not include_closing
	if report_type == "Profit and Loss" and year_start_date:
		if closing_date:
			after_closing = max(getdate(add_days(closing_date, 1)), getdate(year_start_date))
			entries = get_dated_entries(filters, None, closing_date, ignore_closing)
			if after_closing <= getdate(to_date):
				entries = entries + get_dated_entries(filters, after_closing, to_date, ignore_closing)
		else:
			entries = get_dated_entries(filters, year_start_date, to_date, ignore_closing)
	else:
		entries = get_dated_entries(filters, None, to_date, ignore_closing)
	accounts = get_report_type_accounts(filters.company, report_type)
	entries = [frappe._dict(entry) for entry in entries if entry.account in accounts]
	# As get_opening_balance: only the path that ignores the reporting currency converts here.
	if filters.get("presentation_currency") and ignore_reporting_currency:
		from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency

		convert_to_presentation_currency(entries, get_currency(filters))
	return entries


def get_account_type_movement(
	filters, accounts, start_date, end_date, dimension_field=None, dimension_value=None, company=None
):
	"""Credit less debit of the adjustment rows on the accounts, for a row of Cash Flow."""
	from erpnext.accounts.report.financial_statements import _matches_dimension_value

	entries = get_dated_entries(filters, start_date, end_date, ignore_closing_entries=True, company=company)
	accounts = set(accounts)
	check_dimension = bool(dimension_field) and dimension_value is not None
	return sum(
		flt(e.credit) - flt(e.debit)
		for e in entries
		if e.account in accounts
		and (not check_dimension or _matches_dimension_value(e.get(dimension_field), dimension_value))
	)


def get_engine_adjustments(filters, account_names, periods) -> tuple[dict, dict]:
	"""Opening totals and movements for each period, for the Financial Report Template engine.

	The engine leaves out PCV rows except those on a closing account, so the closing transfer
	rows follow the same rule.
	"""
	accounts = set(account_names)
	first_start = getdate(periods[0]["from_date"])
	closing_heads = set(
		frappe.get_all(
			"Period Closing Voucher", filters={"docstatus": 1}, pluck="closing_account_head", distinct=True
		)
	)

	def keep(entry):
		if entry.account not in accounts:
			return False
		return entry.voucher_type != PERIOD_CLOSING_VOUCHER or entry.account in closing_heads

	opening = {}
	for entry in get_dated_entries(filters, None, add_days(first_start, -1), False):
		if keep(entry):
			opening[entry.account] = opening.get(entry.account, 0.0) + flt(entry.debit) - flt(entry.credit)

	movements = {}
	entries = get_dated_entries(filters, first_start, periods[-1]["to_date"], False)
	for period in periods:
		start, end = getdate(period["from_date"]), getdate(period["to_date"])
		for entry in entries:
			if keep(entry) and start <= entry.posting_date <= end:
				by_period = movements.setdefault(entry.account, {})
				by_period[period["key"]] = (
					by_period.get(period["key"], 0.0) + flt(entry.debit) - flt(entry.credit)
				)
	return opening, movements


@frappe.request_cache
def get_report_type_accounts(company, report_type) -> set[str]:
	return set(
		frappe.get_all("Account", filters={"company": company, "report_type": report_type}, pluck="name")
	)


def add_report_message(result, filters, to_date, balance_sheet=False, from_date=None, others=()):
	"""Put the cash basis message into the message slot of a report result."""
	message = get_report_message(
		filters, to_date, balance_sheet=balance_sheet, from_date=from_date, others=others
	)
	if not message or not result:
		return result
	result = list(result)
	while len(result) < 3:
		result.append(None)
	result[2] = "<br>".join(line for line in (result[2], message) if line)
	return tuple(result)


def get_ledger_adjustments(filters, with_opening) -> list[frappe._dict]:
	"""Adjustment rows in the shape of the rows of the General Ledger, with its conditions.

	Each row has the voucher of its obligation (or of its payment) and a remark such as
	"Cash basis: deferral". with_opening: the report also needs the rows before from_date.
	The column Cash Basis Adjustment shows the kind of each row. The Remarks column keeps the
	remark of the voucher.
	"""
	from_date = None if with_opening else filters.from_date
	result = get_report_result(filters, filters.to_date)
	entries = get_dated_entries(filters, from_date, filters.to_date, ignore_closing_entries=False)
	rates = get_obligation_rates(result.obligations)
	parties = set(filters.party or [])
	accounts = set(filters.account or [])
	excluded = set(filters.get("voucher_no_not_in") or [])
	labels = get_adjustment_labels()
	rows = []
	for entry in entries:
		if accounts and entry.account not in accounts:
			continue
		if filters.get("voucher_no") and entry.voucher_no != filters.voucher_no:
			continue
		# A row belongs to its obligation and to its settling voucher.
		if filters.get("against_voucher_no") and filters.against_voucher_no not in (
			entry.voucher_no,
			entry.against_voucher,
		):
			continue
		if entry.voucher_no in excluded:
			continue
		if filters.get("party_type") and entry.party_type != filters.party_type:
			continue
		if parties and entry.party not in parties:
			continue
		if filters.get("categorize_by") == "Categorize by Party" and not filters.get("party_type"):
			if entry.party_type not in ("Customer", "Supplier"):
				continue
		rate = result.account_rates.get(
			(entry.voucher_type, entry.voucher_no, entry.account, entry.party_type, entry.party)
		)
		if rate is None:
			rate = rates.get((entry.voucher_type, entry.voucher_no))
		rows.append(to_ledger_row(entry, rate, labels))
	if filters.get("show_remarks"):
		remarks = get_voucher_remarks({(row.voucher_type, row.voucher_no) for row in rows})
		for row in rows:
			row.remarks = remarks.get((row.voucher_type, row.voucher_no))
	return rows


def get_voucher_remarks(vouchers) -> dict:
	"""The remark of each voucher, cut as the General Ledger cuts it.

	When the GL rows of a voucher have different remarks (a Journal Entry with a remark on each
	row), it is the remark of the first row, by creation and name.
	"""
	gle = frappe.qb.DocType("GL Entry")
	length = frappe.get_single_value("Accounts Settings", "general_ledger_remarks_length")
	remark_field = Substring(gle.remarks, 1, length) if length else gle.remarks
	remarks = {}
	names = sorted({voucher_no for _voucher_type, voucher_no in vouchers})
	for start in range(0, len(names), 500):
		for voucher_type, voucher_no, remark in (
			frappe.qb.from_(gle)
			.select(gle.voucher_type, gle.voucher_no, remark_field)
			.where(gle.voucher_no.isin(names[start : start + 500]) & (gle.is_cancelled == 0))
			.orderby(gle.creation)
			.orderby(gle.name)
			.run()
		):
			remarks.setdefault((voucher_type, voucher_no), remark)
	return remarks


def get_adjustment_labels() -> dict:
	"""The label and the hover card text of each kind of adjustment row, for the column Cash Basis Adjustment."""
	return {
		DEFERRAL: (
			_("Deferred Until Paid"),
			_("The invoice is not counted on its date. It is counted when it is paid."),
		),
		RECOGNITION: (
			_("Recognized When Paid"),
			_("The paid part of the invoice is counted as income or expense on the payment date."),
		),
		NON_CASH: (
			_("Non-cash Settlement"),
			_(
				"A credit note or a write-off closed the invoice. No cash moved, so the invoice and the write-off are not counted."
			),
		),
		UNAPPLIED: (
			_("Unapplied Cash"),
			_(
				"The payment is not applied to an invoice. It is counted as income or expense until you apply it."
			),
		),
		REVALUATION: (
			_("Exchange Difference Removed"),
			_("An unrealized exchange gain or loss is not cash, so it is not counted."),
		),
		PERIOD_CLOSING: (
			_("Period Closing"),
			_(
				"The cash basis profit of the period moves to the closing account of the Period Closing Voucher."
			),
		),
		SCHEDULE_REMOVAL: (
			_("Deferred Schedule Removed"),
			_("The entry of the deferral schedule is not counted. The item is counted when it is paid."),
		),
	}


def get_obligation_rates(obligations) -> dict:
	"""Account currency for each unit of company currency, for each obligation."""
	return {
		key: obligation.base / obligation.base_company
		for key, obligation in obligations.items()
		if obligation.base_company
	}


def to_ledger_row(entry, rate, labels) -> frappe._dict:
	label, explanation = labels.get(entry.remarks, (None, None))
	row = frappe._dict(entry)
	row.update(
		{
			"gl_entry": None,
			"voucher_subtype": None,
			"against": None,
			"cash_basis_kind": entry.remarks,
			"cash_basis_adjustment": label,
			"cash_basis_adjustment_help": explanation,
			"debit_in_transaction_currency": 0.0,
			"credit_in_transaction_currency": 0.0,
			# The adjustment rows sort after the GL rows, by is_cash_adjustment, not by creation.
			"creation": datetime.combine(getdate(entry.posting_date), time.min),
		}
	)
	account_currency = get_account_currency_of(entry.account)
	if account_currency != entry.account_currency:
		# A party account in another currency: the amounts at the rate of the obligation.
		row.account_currency = account_currency
		# A revaluation has no effect in the account currency.
		if rate and entry.remarks != REVALUATION:
			precision = get_currency_precision_of(account_currency)
			row.debit_in_account_currency = flt(flt(entry.debit) * flt(rate), precision)
			row.credit_in_account_currency = flt(flt(entry.credit) * flt(rate), precision)
		else:
			row.debit_in_account_currency = row.credit_in_account_currency = 0.0
	return row


@frappe.request_cache
def get_account_currency_of(account) -> str:
	return frappe.get_cached_value("Account", account, "account_currency")


@frappe.request_cache
def get_currency_precision_of(currency) -> int:
	from frappe.model.meta import get_field_precision

	return get_field_precision(
		frappe.get_meta("GL Entry").get_field("debit_in_account_currency"), currency=currency
	)


def get_company_entries(
	filters, company, from_date, to_date, root_lft, root_rgt, root_type=None, ignore_closing_entries=False
) -> list[frappe._dict]:
	"""Adjustment rows of one company of a consolidated report, with the account fields it reads."""
	entries = get_dated_entries(filters, from_date, to_date, ignore_closing_entries, company=company)
	accounts = get_account_fields(company, root_lft, root_rgt, root_type)
	result = []
	for entry in entries:
		if entry.account in accounts:
			row = frappe._dict(entry)
			row.update(accounts[entry.account])
			row.company = company
			result.append(row)
	return result


@frappe.request_cache
def get_account_fields(company, root_lft, root_rgt, root_type=None) -> dict:
	filters = {"company": company, "is_group": 0, "lft": (">=", root_lft), "rgt": ("<=", root_rgt)}
	if root_type:
		filters["root_type"] = root_type
	rows = frappe.get_all(
		"Account",
		filters=filters,
		fields=["name", "account_name", "account_number", "root_type", "report_type", "account_type"],
	)
	return {row.pop("name"): row for row in rows}


def get_account_type_balance(filters, account_type, to_date) -> float:
	"""Debit less credit of the adjustment rows to the date on the accounts of a type (Financial Ratios)."""
	accounts = get_account_type_accounts(filters.company, account_type)
	return sum(
		flt(e.debit) - flt(e.credit)
		for e in get_dated_entries(filters, None, to_date, False)
		if e.account in accounts
	)


def get_profit_and_loss_adjustments(filters, company, from_date, to_date) -> list[frappe._dict]:
	"""P&L adjustment rows of one company, for the translation difference of a consolidated report."""
	accounts = get_report_type_accounts(company, "Profit and Loss")
	return [
		frappe._dict(
			company=company,
			posting_date=entry.posting_date,
			debit=entry.debit,
			credit=entry.credit,
			debit_in_reporting_currency=entry.debit_in_reporting_currency,
			credit_in_reporting_currency=entry.credit_in_reporting_currency,
		)
		for entry in get_dated_entries(filters, from_date, to_date, False, company=company)
		if entry.account in accounts
	]


def get_dimension_entries(
	filters, from_date, to_date, fieldname, ignore_closing_entries
) -> list[frappe._dict]:
	"""Adjustment rows in the shape of Profitability Analysis: the dimension value and the root type."""
	root_types = get_account_root_types(filters.company)
	return [
		frappe._dict(
			posting_date=entry.posting_date,
			based_on=entry.get(fieldname),
			debit=entry.debit,
			credit=entry.credit,
			is_opening="No",
			type=root_types.get(entry.account),
		)
		for entry in get_dated_entries(filters, from_date, to_date, ignore_closing_entries)
		if entry.get(fieldname)
	]


def get_dimension_list_entries(filters, dimension_field, dimension_list, accounts=None) -> list[frappe._dict]:
	"""Adjustment rows of Dimension-wise Accounts Balance: the dimension values, no closing rows."""
	values = set(dimension_list)
	accounts = set(accounts or [])
	return [
		frappe._dict(entry)
		for entry in get_dated_entries(filters, filters.get("from_date"), filters.get("to_date"), True)
		if entry.get(dimension_field) in values and (not accounts or entry.account in accounts)
	]


@frappe.request_cache
def get_account_root_types(company) -> dict:
	return dict(
		frappe.get_all("Account", filters={"company": company}, fields=["name", "root_type"], as_list=True)
	)


@frappe.request_cache
def get_account_type_accounts(company, account_type) -> set[str]:
	return set(
		frappe.get_all("Account", filters={"company": company, "account_type": account_type}, pluck="name")
	)


def get_statement_print_rows(filters: dict | None, data: list) -> tuple[list, str | None]:
	"""The rows of the Statement of Account print format, and the method to show in its head.

	A party statement shows what the customer or supplier owes, so it always uses the accrual
	basis: after a cash basis run, run the General Ledger again on the accrual basis. Other prints
	of the format (an account ledger, a Bank Book, a list of vouchers) keep the rows of the run,
	and show the method when it is Cash. The accrual rerun ignores a row selection in the grid.
	"""
	from erpnext.accounts.report.general_ledger.general_ledger import execute

	filters = frappe._dict(filters or {})
	if get_accounting_method(filters) != CASH:
		return data, None
	if not is_party_statement(filters):
		return data, CASH
	accrual = without_private_keys(filters)
	accrual["accounting_method"] = ACCRUAL
	return execute(frappe._dict(accrual))[1], None


def is_party_statement(filters) -> bool:
	"""True when the print is for one or more customers or suppliers."""
	parties = filters.get("party")
	if isinstance(parties, str):
		parties = frappe.parse_json(parties) if parties.startswith("[") else [parties]
	return filters.get("party_type") in ("Customer", "Supplier") and bool(parties)
