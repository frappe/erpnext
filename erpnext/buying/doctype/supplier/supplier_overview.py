import frappe
from frappe import _
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils import add_days, add_months, cint, date_diff, flt, getdate, today

from erpnext.accounts.party import get_partywise_advanced_payment_amount
from erpnext.selling.doctype.customer.customer_overview import (
	PERIODS,
	_unrestricted_read,
	ageing,
	pct_change,
	permitted,
	resolve_period,
)

CLOSED_PO_STATUS = ("Closed", "Completed", "On Hold", "Delivered")
OPEN_SQ_STATUS = ("Submitted", "Partially Ordered")


@frappe.whitelist()
def get_supplier_overview(supplier: str, company: str, period: str = "Current Fiscal Year"):
	check_access(supplier, company)

	if period not in PERIODS:
		period = "Current Fiscal Year"

	as_of = getdate(today())
	from_date, to_date = resolve_period(period, company, as_of)
	accounts = accounts_access()

	payload = {
		"supplier": supplier,
		"company": company,
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"period": period,
		"period_range": {"from_date": str(from_date), "to_date": str(to_date)},
		"as_of": str(as_of),
		"permissions": {"accounts": accounts},
		"errors": {},
	}

	for key, fn, args in (
		("position", position, (supplier, company, from_date, to_date, accounts)),
		("trend", trend, (supplier, company, from_date, to_date, accounts)),
		("delivery", delivery, (supplier, company, from_date, min(to_date, as_of), as_of)),
		("pipeline", pipeline, (supplier, company, as_of)),
	):
		try:
			payload[key] = fn(*args)
		except Exception:
			payload[key] = None
			payload["errors"][key] = 1
			frappe.log_error(title="Supplier Overview: " + key)

	return payload


@frappe.whitelist()
def get_supplier_payables(supplier: str, company: str):
	check_access(supplier, company)
	if not payables_access():
		return None

	as_of = getdate(today())
	ap = payables(supplier, company, as_of)
	overdue_prev = payables(supplier, company, add_days(as_of, -30))["overdue"]
	return {
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"outstanding": {
			"value": ap["outstanding"],
			"unpaid_count": unpaid_bills(supplier, company),
			"days_to_pay": payment_days(supplier, company, as_of, ap["outstanding"]),
		},
		"overdue": {
			"value": ap["overdue"],
			"delta": pct_change(ap["overdue"], overdue_prev),
			"delta_positive_is_good": False,
		},
		"advances": {"value": advances(supplier, company, as_of)},
		"ageing": ageing(ap),
	}


def check_access(supplier, company=None):
	if not frappe.has_permission("Supplier", "read", doc=supplier):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	allowed = frappe.permissions.get_user_permissions(frappe.session.user).get("Company")
	if company and allowed and company not in {p.get("doc") for p in allowed}:
		frappe.throw(_("Not permitted for company {0}").format(company), frappe.PermissionError)


def accounts_access():
	return bool(
		frappe.has_permission("Purchase Invoice", "read") and frappe.has_permission("GL Entry", "read")
	)


def payables_access():
	return accounts_access() and frappe.get_cached_doc("Report", "Accounts Payable").is_permitted()


def invoice_filters(supplier, company, from_date, to_date):
	return [
		["docstatus", "=", 1],
		["supplier", "=", supplier],
		["company", "=", company],
		["is_opening", "!=", "Yes"],
		["posting_date", ">=", from_date],
		["posting_date", "<=", to_date],
	]


def purchase_totals(supplier, company, from_date, to_date):
	pi = DocType("Purchase Invoice")
	row = permitted(
		"Purchase Invoice",
		invoice_filters(supplier, company, from_date, to_date),
		[
			Coalesce(Sum(pi.base_net_total), 0).as_("total"),
			Coalesce(Sum(Case().when(pi.is_return == 0, 1).else_(0)), 0).as_("count"),
		],
	)[0]
	return flt(row.total), cint(row.count)


def position(supplier, company, from_date, to_date, accounts):
	if not accounts:
		return {}

	current, bill_count = purchase_totals(supplier, company, from_date, to_date)
	previous = purchase_totals(supplier, company, add_months(from_date, -12), add_months(to_date, -12))[0]
	return {
		"net_purchases": {
			"value": current,
			"count": bill_count,
			"delta": pct_change(current, previous),
			"delta_positive_is_good": True,
		}
	}


def trend(supplier, company, from_date, to_date, accounts):
	if not accounts:
		return None

	pi = DocType("Purchase Invoice")
	billed = monthly(
		permitted(
			"Purchase Invoice",
			invoice_filters(supplier, company, from_date, to_date),
			["posting_date as date", Sum(pi.base_grand_total).as_("amount")],
			group_by="posting_date",
		)
	)
	pe = DocType("Payment Entry")
	signed = Case().when(pe.payment_type == "Pay", pe.base_paid_amount).else_(-pe.base_received_amount)
	paid = monthly(
		permitted(
			"Purchase Invoice",
			[*invoice_filters(supplier, company, from_date, to_date), ["is_paid", "=", 1]],
			["posting_date as date", Sum(pi.base_paid_amount).as_("amount")],
			group_by="posting_date",
		)
		+ permitted(
			"Payment Entry",
			{
				"docstatus": 1,
				"party_type": "Supplier",
				"party": supplier,
				"company": company,
				"payment_type": ["in", ("Pay", "Receive")],
				"posting_date": ["between", (from_date, to_date)],
			},
			["posting_date as date", Sum(signed).as_("amount")],
			group_by="posting_date",
		)
	)

	points = []
	cursor = getdate(from_date).replace(day=1)
	while cursor <= getdate(to_date):
		points.append(
			{
				"label": cursor.strftime("%b"),
				"title": cursor.strftime("%b %Y"),
				"purchased": billed.get(cursor, 0.0),
				"paid": paid.get(cursor, 0.0),
			}
		)
		cursor = add_months(cursor, 1)

	return {
		"points": points,
		"purchased": sum(p["purchased"] for p in points),
		"paid": sum(p["paid"] for p in points),
	}


def monthly(rows):
	totals = {}
	for row in rows:
		month = getdate(row.date).replace(day=1)
		totals[month] = totals.get(month, 0.0) + flt(row.amount)
	return totals


def delivery(supplier, company, from_date, to_date, as_of):
	if not (
		frappe.has_permission("Purchase Order", "read") and frappe.has_permission("Purchase Receipt", "read")
	):
		return None

	lines = permitted(
		"Purchase Order",
		[
			["docstatus", "=", 1],
			["supplier", "=", supplier],
			["company", "=", company],
			["status", "!=", "Closed"],
			["Purchase Order Item", "schedule_date", ">=", from_date],
			["Purchase Order Item", "schedule_date", "<=", to_date],
		],
		[
			"name",
			"items.name as line",
			"items.qty",
			"items.received_qty",
			"items.schedule_date",
			"items.closed",
		],
	)
	received_on = fulfilment_dates(supplier, company, {line.line: flt(line.qty) for line in lines})
	counts = {"on_time": 0, "late": 0, "overdue": 0}
	orders = set()
	for line in lines:
		due = getdate(line.schedule_date)
		if flt(line.received_qty) >= flt(line.qty):
			outcome = "late" if received_on.get(line.line, due) > due else "on_time"
		elif due < as_of and not line.closed:
			outcome = "overdue"
		else:
			continue
		counts[outcome] += 1
		orders.add(line.name)

	lines_due = sum(counts.values())
	return {
		**counts,
		"lines": lines_due,
		"orders": len(orders),
		"on_time_rate": flt(counts["on_time"] / lines_due * 100, 1) if lines_due else None,
		"scorecard": bool(
			frappe.db.exists("Supplier Scorecard", supplier)
			and frappe.has_permission("Supplier Scorecard", "read")
		),
	}


def fulfilment_dates(supplier, company, ordered):
	receipts = {}
	for doctype, line_field, extra in (
		("Purchase Receipt", "purchase_order_item", {}),
		("Purchase Invoice", "po_detail", {"update_stock": 1}),
	):
		if not ordered or not frappe.has_permission(doctype, "read"):
			continue
		item = DocType(f"{doctype} Item")
		for row in permitted(
			doctype,
			[
				{"docstatus": 1, "supplier": supplier, "company": company, **extra},
				[f"{doctype} Item", line_field, "in", list(ordered)],
			],
			[
				f"items.{line_field} as line",
				"posting_date",
				Sum(item.received_qty).as_("qty"),
			],
			group_by=f"items.{line_field}, posting_date",
		):
			day = receipts.setdefault(row.line, {})
			posted = getdate(row.posting_date)
			day[posted] = day.get(posted, 0) + flt(row.qty)

	dates = {}
	for line, by_day in receipts.items():
		received, fulfilled = 0, None
		for posted in sorted(by_day):
			received += by_day[posted]
			if received < ordered[line]:
				fulfilled = None
			elif not fulfilled:
				fulfilled = posted
		if fulfilled:
			dates[line] = fulfilled
	return dates


def pipeline(supplier, company, as_of):
	tiles = {}
	if frappe.has_permission("Supplier Quotation", "read"):
		tiles["quotations"] = open_quotations(supplier, company, as_of)
	if frappe.has_permission("Purchase Order", "read"):
		tiles.update(order_tiles(supplier, company, as_of))
	return tiles


def open_quotations(supplier, company, as_of):
	sq = DocType("Supplier Quotation")
	expiring = Case().when((sq.valid_till >= as_of) & (sq.valid_till <= add_days(as_of, 7)), 1).else_(0)
	row = permitted(
		"Supplier Quotation",
		{"docstatus": 1, "supplier": supplier, "company": company, "status": ["in", OPEN_SQ_STATUS]},
		[
			Coalesce(Sum(sq.base_grand_total), 0).as_("value"),
			Count(sq.name).as_("count"),
			Coalesce(Sum(expiring), 0).as_("expiring"),
		],
	)[0]
	return {"value": flt(row.value), "count": row.count, "expiring": cint(row.expiring)}


def order_tiles(supplier, company, as_of):
	lines = permitted(
		"Purchase Order",
		{
			"docstatus": 1,
			"supplier": supplier,
			"company": company,
			"status": ["not in", CLOSED_PO_STATUS],
		},
		[
			"name",
			"conversion_rate",
			"items.qty",
			"items.received_qty",
			"items.base_amount",
			"items.billed_amt",
			"items.schedule_date as due",
			"items.closed",
		],
	)

	receipt, billing, late = {}, {}, {}
	upcoming, oldest = [], None
	for line in lines:
		if line.closed:
			continue
		qty = flt(line.qty)
		rate = flt(line.base_amount) / qty if qty else 0
		received = min(max(flt(line.received_qty), 0), qty) if qty else 0

		unbilled = received * rate - flt(line.billed_amt) * flt(line.conversion_rate)
		if unbilled > 0:
			billing[line.name] = billing.get(line.name, 0) + unbilled

		pending = (qty - received) * rate
		if qty - received <= 0:
			continue
		receipt[line.name] = receipt.get(line.name, 0) + pending
		if not line.due:
			continue
		due = getdate(line.due)
		if due < as_of:
			late[line.name] = late.get(line.name, 0) + pending
			oldest = min(oldest or due, due)
		else:
			upcoming.append(due)

	return {
		"receipt": {
			"value": flt(sum(receipt.values()), 2),
			"count": len(receipt),
			"next_due": str(min(upcoming)) if upcoming else None,
			"orders": sorted(receipt),
		},
		"billing": {
			"value": flt(sum(billing.values()), 2),
			"count": len(billing),
			"orders": sorted(billing),
		},
		"late": {
			"value": flt(sum(late.values()), 2),
			"count": len(late),
			"days_late": date_diff(as_of, oldest) if oldest else None,
			"orders": sorted(late),
		},
	}


def payables(supplier, company, report_date):
	from erpnext.accounts.report.accounts_payable.accounts_payable import execute

	data = execute(
		{
			"company": company,
			"report_date": report_date,
			"party_type": "Supplier",
			"party": [supplier],
			"ageing_based_on": "Due Date",
			"age_as_on": "Report Date",
			"range": "30, 60, 90",
		}
	)[1]
	owed = [d for d in data if flt(d.get("outstanding")) > 0]
	total = {
		key: sum(flt(d.get(key)) for d in owed)
		for key in ("total_due", "range1", "range2", "range3", "range4")
	}
	outstanding = sum(flt(d.get("outstanding")) for d in owed)
	return {
		"outstanding": outstanding,
		"overdue": total["total_due"],
		"buckets": [
			{"label": _("Not due"), "value": outstanding - total["total_due"], "overdue": False},
			{"label": _("0–30 days"), "value": total["range1"], "overdue": True},
			{"label": _("31–60 days"), "value": total["range2"], "overdue": True},
			{"label": _("61–90 days"), "value": total["range3"], "overdue": True},
			{"label": _("90+ days"), "value": total["range4"], "overdue": True},
		],
	}


def unpaid_bills(supplier, company):
	pi = DocType("Purchase Invoice")
	return permitted(
		"Purchase Invoice",
		{
			"docstatus": 1,
			"supplier": supplier,
			"company": company,
			"is_return": 0,
			"outstanding_amount": [">", 0],
		},
		[Count(pi.name).as_("count")],
	)[0].count


def payment_days(supplier, company, as_of, outstanding):
	if outstanding <= 0:
		return None

	first_bill = frappe.get_list(
		"Purchase Invoice",
		filters={
			"docstatus": 1,
			"supplier": supplier,
			"company": company,
			"is_opening": ["!=", "Yes"],
			"posting_date": [">", add_days(as_of, -365)],
		},
		order_by="posting_date asc",
		limit=1,
		pluck="posting_date",
	)
	history = date_diff(as_of, first_bill[0]) + 1 if first_bill else 0
	if history < 30:
		return None
	trailing = purchase_totals(supplier, company, add_days(as_of, -history), as_of)[0]
	if trailing <= 0:
		return None
	days = round(outstanding / (trailing / history))
	return days if days <= 730 else None


def advances(supplier, company, as_of):
	if not _unrestricted_read("Payment Ledger Entry"):
		return None
	return flt(
		get_partywise_advanced_payment_amount(["Supplier"], as_of, company=company, party=supplier).get(
			supplier
		)
	)


TRANSACTION_TYPES = ("Purchase Invoice", "Purchase Order", "Purchase Receipt", "Payment Entry")


@frappe.whitelist()
def get_supplier_transactions(supplier: str, company: str, doc_type: str = "All", limit: int = 20):
	check_access(supplier, company)

	limit = min(cint(limit) or 20, 100)
	accounts = accounts_access()
	wanted = [doc_type] if doc_type in TRANSACTION_TYPES else list(TRANSACTION_TYPES)

	rows = []
	for doctype in wanted:
		if (doctype in ("Purchase Invoice", "Payment Entry") and not accounts) or not frappe.has_permission(
			doctype, "read"
		):
			continue
		rows.extend(transaction_rows(doctype, supplier, company, limit))

	rows.sort(key=lambda r: (r["date"], r["name"]), reverse=True)
	return rows[:limit]


def transaction_rows(doctype, supplier, company, limit):
	is_payment = doctype == "Payment Entry"
	date_field = "transaction_date" if doctype == "Purchase Order" else "posting_date"
	amount_field = "base_paid_amount" if is_payment else "base_grand_total"
	fields = ["name", "status", f"{date_field} as date", f"{amount_field} as amount"]
	if doctype == "Purchase Invoice":
		fields += ["outstanding_amount", "party_account_currency", "conversion_rate"]

	filters = {"docstatus": 1, "company": company}
	filters.update({"party_type": "Supplier", "party": supplier} if is_payment else {"supplier": supplier})

	currency = frappe.get_cached_value("Company", company, "default_currency")
	return [
		{
			"name": r.name,
			"doctype": doctype,
			"type_label": _(doctype),
			"date": str(r.date),
			"status": r.status,
			"amount": flt(r.amount),
			"outstanding": invoice_outstanding(r, currency) if doctype == "Purchase Invoice" else None,
		}
		for r in frappe.get_list(
			doctype, filters=filters, fields=fields, order_by=f"{date_field} desc, creation desc", limit=limit
		)
	]


def invoice_outstanding(row, currency):
	rate = 1 if row.party_account_currency == currency else flt(row.conversion_rate)
	return flt(row.outstanding_amount) * rate


@frappe.whitelist()
def get_supplier_companies(supplier: str):
	check_access(supplier)

	companies = set()
	for doctype, filters in (
		("Purchase Invoice", {"supplier": supplier}),
		("Purchase Order", {"supplier": supplier}),
		("Purchase Receipt", {"supplier": supplier}),
		("Supplier Quotation", {"supplier": supplier}),
		("Payment Entry", {"party_type": "Supplier", "party": supplier}),
		("GL Entry", {"party_type": "Supplier", "party": supplier, "is_cancelled": 0}),
	):
		if frappe.has_permission(doctype, "read"):
			companies.update(
				frappe.get_list(doctype, filters={**filters, "docstatus": 1}, distinct=True, pluck="company")
			)
	companies.discard(None)
	return sorted(companies)
