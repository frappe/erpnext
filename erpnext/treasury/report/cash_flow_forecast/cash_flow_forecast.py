# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from functools import partial

import frappe
from frappe import _
from frappe.query_builder.functions import Max, Min, Sum
from frappe.utils import add_days, cint, flt, formatdate, getdate

import erpnext
from erpnext.setup.utils import get_exchange_rate
from erpnext.treasury.dashboard import HELD_STATUSES, get_month_ends
from erpnext.treasury.doctype.investment_transaction.investment_transaction import EXIT_TYPES, PURCHASE_TYPES
from erpnext.treasury.report.bank_and_cash_balances.bank_and_cash_balances import get_cash_balances
from erpnext.treasury.report.utils import get_currency_column, parse_filters

INFLOWS = ("receivables", "maturities", "interest")
OUTFLOWS = ("payables", "commitments")


def execute(filters=None):
	filters = parse_filters(filters)
	filters.currency = erpnext.get_company_currency(filters.company)
	period_ends = get_period_ends(filters)

	return get_columns(filters, period_ends), get_data(filters, period_ends)


def get_period_ends(filters):
	count = cint(filters.periods) or 6
	if filters.periodicity == "Weekly":
		return [getdate(add_days(filters.from_date, 7 * (i + 1) - 1)) for i in range(count)]

	return get_month_ends(filters.from_date, count)


def get_data(filters, period_ends):
	flows = {**get_party_flows(filters.company), **get_investment_flows(filters)}
	inflows = {key: get_period_totals(flows[key], period_ends, filters) for key in INFLOWS}
	outflows = {key: get_period_totals(flows[key], period_ends, filters) for key in OUTFLOWS}
	labels = get_flow_labels()
	total_in, total_out = sum_columns(inflows.values()), sum_columns(outflows.values())
	net = [inflow - outflow for inflow, outflow in zip(total_in, total_out, strict=True)]
	opening, closing = get_running_balances(get_opening_balance(filters), net)

	row = partial(make_row, filters.currency)
	return [
		row(_("Opening Balance"), opening, bold=1, total=opening[0]),
		row(_("Cash Inflows"), bold=1),
		*[row(labels[key], inflows[key]) for key in INFLOWS],
		row(_("Total Inflows"), total_in, bold=1),
		row(_("Cash Outflows"), bold=1),
		*[row(labels[key], outflows[key]) for key in OUTFLOWS],
		row(_("Total Outflows"), total_out, bold=1),
		row(_("Net Cash Flow"), net, bold=1),
		row(_("Closing Balance"), closing, bold=1, total=closing[-1]),
	]


def get_flow_labels():
	return {
		"receivables": _("Customer Receivables"),
		"maturities": _("Investment Maturities"),
		"interest": _("Investment Interest"),
		"payables": _("Supplier Payables"),
		"commitments": _("Committed Investments"),
	}


def get_party_flows(company):
	"""Outstanding customer and supplier invoices, each expected on its due date, or per payment term."""
	ple = frappe.qb.DocType("Payment Ledger Entry")
	rows = (
		frappe.qb.from_(ple)
		.select(
			ple.account_type,
			ple.against_voucher_type.as_("voucher_type"),
			ple.against_voucher_no.as_("voucher_no"),
			Sum(ple.amount).as_("outstanding"),
			Max(ple.due_date).as_("due_date"),
			Min(ple.posting_date).as_("posting_date"),
		)
		.where(ple.company == company)
		.where(ple.delinked == 0)
		.where(ple.account_type.isin(("Receivable", "Payable")))
		.groupby(ple.account_type, ple.against_voucher_type, ple.against_voucher_no)
	).run(as_dict=True)

	flows = {"receivables": [], "payables": []}
	unpaid = []
	for row in rows:
		row.outstanding = flt(row.outstanding, 2)
		if row.account_type == "Receivable" and row.outstanding > 0:
			unpaid.append((flows["receivables"], row, row.outstanding))
		elif row.account_type == "Payable" and row.outstanding < 0:
			unpaid.append((flows["payables"], row, -row.outstanding))

	payment_terms = get_payment_terms([row for _flows, row, _outstanding in unpaid])
	for party_flows, row, outstanding in unpaid:
		terms = payment_terms.get((row.voucher_type, row.voucher_no))
		if terms:
			party_flows.extend(spread_over_terms(outstanding, terms))
		else:
			party_flows.append((row.due_date or row.posting_date, outstanding))

	return flows


def get_payment_terms(rows):
	"""Payment schedule (due date, company currency amount) of each invoice, earliest first."""
	terms = {}
	for voucher_type in {row.voucher_type for row in rows}:
		schedules = frappe.get_all(
			"Payment Schedule",
			filters={
				"parenttype": voucher_type,
				"parent": ("in", [row.voucher_no for row in rows if row.voucher_type == voucher_type]),
			},
			fields=["parent", "due_date", "base_payment_amount"],
			order_by="due_date asc, idx asc",
		)
		for schedule in schedules:
			terms.setdefault((voucher_type, schedule.parent), []).append(
				(schedule.due_date, flt(schedule.base_payment_amount))
			)

	return terms


def spread_over_terms(outstanding, terms):
	"""The outstanding amount on the due dates of the terms it is left on: payments settled the earliest first."""
	paid = sum(amount for _due_date, amount in terms) - outstanding
	flows = []
	for due_date, amount in terms:
		settled = min(amount, max(paid, 0))
		paid -= settled
		if flt(amount - settled, 2) > 0:
			flows.append((due_date, amount - settled))

	# rounding, or an outstanding above the schedule's total, stays with the last term
	difference = flt(outstanding - sum(amount for _due_date, amount in flows), 2)
	if difference:
		due_date, amount = flows.pop() if flows else (terms[-1][0], 0)
		flows.append((due_date, amount + difference))

	return flows


def get_investment_flows(filters):
	# closed investments are kept, as they can still be owed interest
	investments = frappe.get_all(
		"Investment",
		filters={"company": filters.company, "docstatus": 1},
		fields=[
			"name",
			"status",
			"instrument_class",
			"interest_payout_type",
			"maturity_date",
			"purchase_date",
			"approved_amount",
			"total_cost",
			"unamortised_premium_discount",
			"currency",
		],
	)
	held = [i for i in investments if i.status in HELD_STATUSES]

	return {
		# a bond is redeemed at face value: book value plus the discount not yet amortised (in its own currency)
		"maturities": [
			(
				i.maturity_date,
				flt(i.total_cost) + flt(i.unamortised_premium_discount) * get_rate(i.currency, filters),
			)
			for i in held
			if i.maturity_date
		],
		"interest": get_interest_flows(investments, filters),
		"commitments": get_commitment_flows(held, filters),
	}


def get_interest_flows(investments, filters):
	"""Interest still owed: each period's interest, oldest first, less what was already received."""
	by_name = {investment.name: investment for investment in investments}
	received = get_interest_received(list(by_name))
	periods = get_schedule_periods(list(by_name))
	add_bought_interest(periods, list(by_name))
	flows = []

	for period in periods:
		investment = by_name[period.investment]
		unpaid = flt(period.interest_amount) - received.get(investment.name, 0)
		received[investment.name] = max(-unpaid, 0)

		date = investment.maturity_date if is_paid_at_maturity(investment) else period.period_to
		if unpaid > 0 and date:
			flows.append((date, unpaid * get_rate(investment.currency, filters)))

	return flows


def get_interest_received(investments):
	if not investments:
		return {}

	# accrued interest also comes in from buyers, with bond sales
	receipts = frappe.get_all(
		"Investment Transaction",
		filters={
			"investment": ("in", investments),
			"docstatus": 1,
			"transaction_type": ("in", ("Interest Receipt", *EXIT_TYPES)),
		},
		fields=[
			"investment",
			{"SUM": "interest_amount", "as": "received"},
			{"SUM": "accrued_interest_in_sale", "as": "sold"},
		],
		group_by="investment",
	)
	return {receipt.investment: flt(receipt.received) + flt(receipt.sold) for receipt in receipts}


def add_bought_interest(periods, investments):
	"""Interest bought with a bond is paid with the coupon of the period it was bought in."""
	if not investments:
		return

	purchases = frappe.get_all(
		"Investment Transaction",
		filters={
			"investment": ("in", investments),
			"docstatus": 1,
			"transaction_type": ("in", PURCHASE_TYPES),
			"accrued_interest_in_purchase": (">", 0),
		},
		fields=["investment", "posting_date", "accrued_interest_in_purchase"],
	)
	for purchase in purchases:
		period = next(
			(
				p
				for p in periods
				if p.investment == purchase.investment
				and getdate(p.period_to) >= getdate(purchase.posting_date)
			),
			None,
		)
		if period:
			period.interest_amount = flt(period.interest_amount) + flt(purchase.accrued_interest_in_purchase)


def get_schedule_periods(investments):
	"""Actual interest of fully accrued periods, else the estimate, so the forecast uses real figures."""
	if not investments:
		return []

	periods = frappe.get_all(
		"Investment Interest Schedule",
		filters={
			"parent": ("in", investments),
			"parenttype": "Investment",
			"parentfield": "interest_schedule",
		},
		fields=["parent as investment", "period_to", "estimated_interest", "actual_interest", "status"],
		order_by="period_to asc",
	)
	for period in periods:
		is_accrued = period.status == "Accrued"
		period.interest_amount = period.actual_interest if is_accrued else period.estimated_interest

	return periods


def is_paid_at_maturity(investment):
	return investment.instrument_class == "Deposit" and investment.interest_payout_type == "Cumulative"


def get_commitment_flows(investments, filters):
	"""Approved investments not bought yet: their Approved Amount goes out on the purchase date."""
	bought = set(
		frappe.get_all(
			"Investment Transaction",
			filters={"company": filters.company, "docstatus": 1, "transaction_type": ("in", PURCHASE_TYPES)},
			pluck="investment",
			distinct=True,
		)
	)

	return [
		(i.purchase_date, flt(i.approved_amount) * get_rate(i.currency, filters))
		for i in investments
		if i.status != "Partially Redeemed" and i.name not in bought
	]


def get_rate(currency, filters):
	if not currency or currency == filters.currency:
		return 1

	return flt(get_exchange_rate(currency, filters.currency, filters.from_date)) or 1


def get_period_totals(flows, period_ends, filters):
	totals = [0.0] * len(period_ends)
	for date, amount in flows:
		index = get_period_index(getdate(date), period_ends, filters)
		if index is not None:
			totals[index] += flt(amount)

	return totals


def get_period_index(date, period_ends, filters):
	"""Period the date falls in; overdue dates go to the first period when Include Overdue is ticked."""
	if date < getdate(filters.from_date):
		return 0 if cint(filters.include_overdue) else None

	return next((i for i, period_end in enumerate(period_ends) if date <= period_end), None)


def get_opening_balance(filters):
	balances = get_cash_balances(filters.company, add_days(filters.from_date, -1))
	return sum(flt(row.balance) for row in balances)


def get_running_balances(opening_balance, net_flows):
	opening, closing = [], []
	balance = opening_balance
	for net_flow in net_flows:
		opening.append(balance)
		balance += net_flow
		closing.append(balance)

	return opening, closing


def sum_columns(rows):
	return [sum(column) for column in zip(*rows, strict=True)]


def make_row(currency, label, values=None, bold=0, total=None):
	row = {"category": label, "currency": currency, "bold": bold}
	if values is not None:
		row.update({f"period_{i}": value for i, value in enumerate(values)})
		row["total"] = sum(values) if total is None else total

	return row


def get_columns(filters, period_ends):
	columns = [{"label": _("Category"), "fieldname": "category", "fieldtype": "Data", "width": 220}]
	for i, period_end in enumerate(period_ends):
		label = (
			_("Week to {0}").format(formatdate(period_end, "dd MMM"))
			if filters.periodicity == "Weekly"
			else formatdate(period_end, "MMM YYYY")
		)
		columns.append(get_currency_column(label, f"period_{i}"))

	columns.append(get_currency_column(_("Total"), "total", 140))
	return columns
