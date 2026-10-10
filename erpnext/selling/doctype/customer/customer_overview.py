import frappe
from frappe import _
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils import add_days, add_months, add_to_date, cint, date_diff, flt, getdate, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

PERIODS = ("Current Fiscal Year", "Last 12 Months", "This Quarter", "Last Fiscal Year")
OPEN_SO_STATUS = ("Closed", "Completed", "On Hold")


@frappe.whitelist()
def get_customer_overview(customer: str, company: str, period: str = "Current Fiscal Year"):
	check_access(customer, company)

	if period not in PERIODS:
		period = "Current Fiscal Year"

	as_of = getdate(today())
	from_date, to_date = resolve_period(period, company, as_of)
	accounts = accounts_access()

	payload = {
		"customer": customer,
		"company": company,
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"period": period,
		"period_range": {"from_date": str(from_date), "to_date": str(to_date)},
		"as_of": str(as_of),
		"permissions": {"accounts": accounts},
		"errors": {},
	}

	for key, fn, args in (
		("position", position, (customer, company, from_date, to_date, accounts)),
		("trend", trend, (customer, company, from_date, to_date, as_of, accounts)),
		("pipeline", pipeline, (customer, company, as_of, accounts)),
		("loyalty", loyalty, (customer, company)),
	):
		try:
			payload[key] = fn(*args)
		except Exception:
			payload[key] = None
			payload["errors"][key] = 1
			frappe.log_error(title="Customer Overview: " + key)

	return payload


@frappe.whitelist()
def get_customer_receivables(customer: str, company: str):
	check_access(customer, company)
	if not receivables_access():
		return None

	as_of = getdate(today())
	ar = receivables(customer, company, as_of)
	overdue_prev = receivables(customer, company, add_days(as_of, -30))["overdue"]
	return {
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"outstanding": {
			"value": ar["outstanding"],
			"unpaid_count": unpaid_invoices(customer, company, as_of)["count"],
			"days_to_pay": collection_days(customer, company, as_of, ar["outstanding"]),
		},
		"overdue": {
			"value": ar["overdue"],
			"delta": pct_change(ar["overdue"], overdue_prev),
			"delta_positive_is_good": False,
		},
		"advances": {"value": reported_advances(customer, company, as_of)},
		"credit": credit_position(customer, company),
		"ageing": ageing(ar),
	}


def check_access(customer, company=None):
	if not frappe.has_permission("Customer", "read", doc=customer):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	allowed = frappe.permissions.get_user_permissions(frappe.session.user).get("Company")
	if company and allowed and company not in {p.get("doc") for p in allowed}:
		frappe.throw(_("Not permitted for company {0}").format(company), frappe.PermissionError)


def accounts_access():
	return bool(frappe.has_permission("Sales Invoice", "read") and frappe.has_permission("GL Entry", "read"))


def receivables_access():
	return accounts_access() and frappe.get_cached_doc("Report", "Accounts Receivable Summary").is_permitted()


def _unrestricted_read(doctype):
	from frappe.desk.reportview import build_match_conditions

	readable = frappe.has_permission(doctype, "read")
	return readable and not build_match_conditions(doctype)


def credit_position(customer, company):
	# The credit check needs whole-company exposure; a partial total would
	# incorrectly advertise available credit to a restricted viewer.
	unrestricted = all(
		_unrestricted_read(doctype) for doctype in ("GL Entry", "Sales Order", "Delivery Note")
	)
	return {
		"limit": flt(get_credit_limit(customer, company)),
		"used": flt(get_customer_outstanding(customer, company)) if unrestricted else None,
	}


def permitted(doctype, filters, fields, **kwargs):
	return frappe.qb.get_query(
		doctype, filters=filters, fields=fields, ignore_permissions=False, **kwargs
	).run(as_dict=True)


def invoice_filters(customer, company, from_date, to_date):
	return [
		["docstatus", "=", 1],
		["customer", "=", customer],
		["company", "=", company],
		["is_opening", "!=", "Yes"],
		["posting_date", ">=", from_date],
		["posting_date", "<=", to_date],
	]


def resolve_period(period, company, as_of):
	if period == "Last 12 Months":
		return add_months(as_of.replace(day=1), -11), as_of

	if period == "This Quarter":
		quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
		return as_of.replace(month=quarter_start_month, day=1), as_of

	fy = get_fiscal_year(as_of, company=company, as_dict=True, raise_on_missing=False)
	if not fy:
		return add_to_date(as_of, months=-12, as_string=False), as_of

	if period == "Last Fiscal Year":
		prev = get_fiscal_year(
			add_days(getdate(fy.year_start_date), -1), company=company, as_dict=True, raise_on_missing=False
		)
		if prev:
			return getdate(prev.year_start_date), getdate(prev.year_end_date)

	return getdate(fy.year_start_date), min(as_of, getdate(fy.year_end_date))


def sales_totals(customer, company, from_date, to_date):
	si = DocType("Sales Invoice")
	row = permitted(
		"Sales Invoice",
		invoice_filters(customer, company, from_date, to_date),
		[
			Coalesce(Sum(si.base_net_total), 0).as_("total"),
			Coalesce(Sum(Case().when(si.is_return == 0, 1).else_(0)), 0).as_("count"),
		],
	)[0]
	return flt(row.total), cint(row.count)


def net_sales(customer, company, from_date, to_date):
	return sales_totals(customer, company, from_date, to_date)[0]


def loyalty(customer, company):
	program = frappe.db.get_value("Customer", customer, "loyalty_program")
	if not program:
		return None

	lpe = frappe.qb.DocType("Loyalty Point Entry")
	points = (
		frappe.qb.from_(lpe)
		.select(Sum(lpe.loyalty_points))
		.where((lpe.customer == customer) & (lpe.company == company) & (lpe.expiry_date >= getdate(today())))
	).run()[0][0]
	return {"program": program, "points": cint(points)}


def position(customer, company, from_date, to_date, accounts):
	if not accounts:
		return {}

	current, invoice_count = sales_totals(customer, company, from_date, to_date)
	prev = net_sales(customer, company, add_to_date(from_date, years=-1), add_to_date(to_date, years=-1))
	return {
		"net_sales": {
			"value": current,
			"count": invoice_count,
			"delta": pct_change(current, prev),
			"delta_positive_is_good": True,
		}
	}


def collection_days(customer, company, as_of, outstanding):
	if outstanding <= 0:
		return None

	first_invoice = frappe.get_list(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"customer": customer,
			"company": company,
			"is_opening": ["!=", "Yes"],
			"posting_date": [">", add_days(as_of, -365)],
		},
		order_by="posting_date asc",
		limit=1,
		pluck="posting_date",
	)
	history = date_diff(as_of, first_invoice[0]) + 1 if first_invoice else 0
	if history < 30:
		return None
	trailing = net_sales(customer, company, add_days(as_of, -history), as_of)
	if trailing <= 0:
		return None
	days = round(outstanding / (trailing / history))
	return days if days <= 730 else None


def receivables(customer, company, report_date):
	from erpnext.accounts.report.accounts_receivable.accounts_receivable import (
		execute as accounts_receivable,
	)

	data = accounts_receivable(
		{
			"company": company,
			"report_date": report_date,
			"party_type": "Customer",
			"party": [customer],
			"ageing_based_on": "Due Date",
			"age_as_on": "Report Date",
			"range": "30, 60, 90",
		}
	)[1]
	owed = [d for d in data if flt(d.get("outstanding")) > 0]
	row = {
		key: sum(flt(d.get(key)) for d in owed)
		for key in ("outstanding", "total_due", "range1", "range2", "range3", "range4")
	}
	outstanding = sum(flt(d.get("outstanding")) for d in data)
	overdue = flt(row.get("total_due"))
	not_due = flt(row.get("outstanding")) - overdue
	buckets = [
		{"key": "not_due", "label": _("Not due"), "value": not_due, "overdue": False},
		{"key": "b1", "label": _("0–30 days"), "value": flt(row.get("range1")), "overdue": True},
		{"key": "b2", "label": _("31–60 days"), "value": flt(row.get("range2")), "overdue": True},
		{"key": "b3", "label": _("61–90 days"), "value": flt(row.get("range3")), "overdue": True},
		{"key": "b4", "label": _("90+ days"), "value": flt(row.get("range4")), "overdue": True},
	]
	return {
		"buckets": buckets,
		"outstanding": outstanding,
		"overdue": overdue,
	}


def reported_advances(customer, company, report_date):
	from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import execute

	rows = execute(
		{
			"company": company,
			"report_date": report_date,
			"party_type": "Customer",
			"party": [customer],
			"customer": customer,
			"ageing_based_on": "Due Date",
			"age_as_on": "Report Date",
			"range": "30, 60, 90",
		}
	)[1]
	return next((row.get("advance") for row in rows if row.get("party") == customer), None)


def ageing(ar):
	buckets = ar["buckets"]
	total = flt(sum(b["value"] for b in buckets))
	overdue = flt(sum(b["value"] for b in buckets if b["overdue"]))
	return {
		"buckets": buckets,
		"total": total,
		"overdue": overdue,
		"overdue_pct": flt(overdue / total * 100, 1) if total else 0,
	}


def trend(customer, company, from_date, to_date, as_of, accounts):
	if not accounts:
		return None
	si = DocType("Sales Invoice")
	rows = permitted(
		"Sales Invoice",
		invoice_filters(customer, company, from_date, to_date),
		["posting_date", Sum(si.base_net_total).as_("total")],
		group_by="posting_date",
	)
	by_month = {}
	for r in rows:
		month = getdate(r.posting_date).replace(day=1)
		by_month[month] = by_month.get(month, 0.0) + flt(r.total)

	points, closed = [], []
	cursor = getdate(from_date).replace(day=1)
	last = getdate(to_date).replace(day=1)
	current_month = as_of.replace(day=1)
	while cursor <= last:
		is_mtd = cursor == current_month
		value = by_month.get(cursor, 0.0)
		points.append({"label": cursor.strftime("%b"), "value": value, "mtd": is_mtd})
		if not is_mtd:
			closed.append(value)
		cursor = add_months(cursor, 1)

	return {
		"points": points,
		"average": flt(sum(closed) / len(closed)) if closed else 0,
		"has_mtd": any(p["mtd"] for p in points),
	}


def pipeline(customer, company, as_of, accounts):
	tiles = {}
	if frappe.has_permission("Quotation", "read"):
		tiles.update(quotation_tiles(customer, company))
	if frappe.has_permission("Sales Order", "read"):
		tiles.update(sales_order_tiles(customer, company, as_of))
	if accounts:
		tiles["invoices"] = unpaid_invoices(customer, company, as_of)
	return tiles


def quotation_tiles(customer, company):
	quotation = DocType("Quotation")
	quote = permitted(
		"Quotation",
		{
			"docstatus": 1,
			"status": "Open",
			"quotation_to": "Customer",
			"party_name": customer,
			"company": company,
		},
		[Coalesce(Sum(quotation.base_grand_total), 0).as_("value"), Count(quotation.name).as_("count")],
	)[0]
	return {"quotations": {"value": flt(quote.value), "count": quote.count}}


def sales_order_tiles(customer, company, as_of):
	so = DocType("Sales Order")
	open_orders = {
		"docstatus": 1,
		"customer": customer,
		"company": company,
		"status": ["not in", OPEN_SO_STATUS],
	}

	delivery = permitted(
		"Sales Order",
		{**open_orders, "per_delivered": ["<", 100], "skip_delivery_note": 0},
		[
			Coalesce(Sum(so.base_grand_total * (100 - so.per_delivered) / 100), 0).as_("value"),
			Count(so.name).as_("count"),
			Coalesce(Sum(Case().when(so.delivery_date < as_of, 1).else_(0)), 0).as_("past_due"),
		],
	)[0]

	billing = permitted(
		"Sales Order",
		{**open_orders, "per_billed": ["<", 100]},
		[
			Coalesce(Sum(so.base_grand_total * (100 - so.per_billed) / 100), 0).as_("value"),
			Count(so.name).as_("count"),
		],
	)[0]
	return {
		"delivery": {
			"value": flt(delivery.value),
			"count": delivery.count,
			"past_due": delivery.past_due or 0,
		},
		"billing": {"value": flt(billing.value), "count": billing.count},
	}


def base_outstanding(si, company):
	company_currency = frappe.get_cached_value("Company", company, "default_currency")
	return (
		Case()
		.when(si.party_account_currency == company_currency, si.outstanding_amount)
		.else_(si.outstanding_amount * si.conversion_rate)
	)


def unpaid_invoices(customer, company, as_of):
	si = DocType("Sales Invoice")
	row = permitted(
		"Sales Invoice",
		{
			"docstatus": 1,
			"customer": customer,
			"company": company,
			"is_return": 0,
			"outstanding_amount": [">", 0],
		},
		[
			Coalesce(Sum(base_outstanding(si, company)), 0).as_("value"),
			Count(si.name).as_("count"),
			Coalesce(Sum(Case().when(si.due_date < as_of, 1).else_(0)), 0).as_("overdue"),
		],
	)[0]
	return {"value": flt(row.value), "count": row.count, "overdue": row.overdue or 0}


TRANSACTION_TYPES = ("Sales Invoice", "Sales Order", "Payment Entry")


@frappe.whitelist()
def get_customer_transactions(customer: str, company: str, doc_type: str = "All", limit: int = 20):
	check_access(customer, company)

	limit = min(cint(limit) or 20, 100)
	accounts = accounts_access()
	wanted = [doc_type] if doc_type in TRANSACTION_TYPES else list(TRANSACTION_TYPES)

	rows = []
	for dt in wanted:
		if (dt in ("Sales Invoice", "Payment Entry") and not accounts) or not frappe.has_permission(
			dt, "read"
		):
			continue
		rows.extend(_fetch_rows(dt, customer, company, limit))

	rows.sort(key=lambda r: (str(r["date"]), r["name"]), reverse=True)
	return rows[:limit]


def _txn_specs():
	return {
		"Sales Invoice": {
			"party_field": "customer",
			"extra": {},
			"fields": [
				"name",
				"posting_date as date",
				"status",
				"base_grand_total as amount",
				"outstanding_amount as outstanding",
				"party_account_currency",
				"conversion_rate",
				"is_return",
			],
			"order_by": "posting_date desc, creation desc",
			"row": lambda r, currency: {
				"status": "Return" if r.is_return else r.status,
				"amount": flt(r.amount),
				"outstanding": flt(r.outstanding)
				* (1 if r.party_account_currency == currency else flt(r.conversion_rate)),
			},
		},
		"Sales Order": {
			"party_field": "customer",
			"extra": {},
			"fields": ["name", "transaction_date as date", "status", "base_grand_total as amount"],
			"order_by": "transaction_date desc, creation desc",
			"row": lambda r, currency: {"status": r.status, "amount": flt(r.amount), "outstanding": None},
		},
		"Payment Entry": {
			"party_field": "party",
			"extra": {"party_type": "Customer"},
			"fields": ["name", "posting_date as date", "base_paid_amount as amount"],
			"order_by": "posting_date desc, creation desc",
			"row": lambda r, currency: {"status": "Submitted", "amount": flt(r.amount), "outstanding": None},
		},
	}


def _fetch_rows(doctype, customer, company, limit):
	spec = _txn_specs()[doctype]
	filters = {"docstatus": 1, "company": company, spec["party_field"]: customer, **spec["extra"]}
	currency = frappe.get_cached_value("Company", company, "default_currency")
	rows = []
	for r in frappe.get_list(
		doctype, filters=filters, fields=spec["fields"], order_by=spec["order_by"], limit=limit
	):
		rows.append(
			{
				"name": r.name,
				"doctype": doctype,
				"type_label": _(doctype),
				"date": str(r.date),
				**spec["row"](r, currency),
			}
		)
	return rows


def pct_change(current, previous):
	if not previous:
		return None
	return flt((current - previous) / abs(previous) * 100, 1)


@frappe.whitelist()
def get_customer_companies(customer: str):
	check_access(customer)

	companies = set()
	for doctype, filters in (
		("Sales Invoice", {"customer": customer}),
		("Sales Order", {"customer": customer}),
		("Quotation", {"quotation_to": "Customer", "party_name": customer}),
		("Payment Entry", {"party_type": "Customer", "party": customer}),
		("GL Entry", {"party_type": "Customer", "party": customer, "is_cancelled": 0}),
	):
		if frappe.has_permission(doctype, "read"):
			companies.update(
				frappe.get_list(doctype, filters={**filters, "docstatus": 1}, distinct=True, pluck="company")
			)
	companies.discard(None)
	return sorted(companies)
