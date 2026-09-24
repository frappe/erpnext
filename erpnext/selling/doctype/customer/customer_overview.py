import frappe
from frappe import _
from frappe.query_builder import Case, DocType
from frappe.query_builder.functions import Coalesce, Count, Sum
from frappe.utils import add_days, add_months, add_to_date, cint, flt, getdate, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.selling.doctype.customer.customer import get_credit_limit

PERIODS = ("This fiscal year", "Last 12 months", "This quarter", "Last fiscal year")
OPEN_SO_STATUS = ("Closed", "Completed", "On Hold")


@frappe.whitelist()
def get_customer_overview(customer: str, company: str, period: str = "This fiscal year"):
	check_access(customer, company)

	if period not in PERIODS:
		period = "This fiscal year"

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

	ar = None
	if accounts:
		try:
			ar = receivables(customer, company, as_of)
		except Exception:
			payload["errors"]["receivables"] = 1
			frappe.log_error(title="Customer Overview: receivables")

	for key, fn, args in (
		("position", position, (customer, company, from_date, to_date, as_of, ar, accounts)),
		("trend", trend, (customer, company, from_date, to_date, as_of, accounts)),
		("ageing", ageing, (ar,)),
		("pipeline", pipeline, (customer, company, as_of, accounts)),
	):
		try:
			payload[key] = fn(*args)
		except Exception:
			payload[key] = None
			payload["errors"][key] = 1
			frappe.log_error(title="Customer Overview: " + key)

	return payload


def check_access(customer, company=None):
	if not frappe.has_permission("Customer", "read", doc=customer):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	allowed = frappe.permissions.get_user_permissions(frappe.session.user).get("Company")
	if company and allowed and company not in {p.get("doc") for p in allowed}:
		frappe.throw(_("Not permitted for company {0}").format(company), frappe.PermissionError)


def accounts_access():
	return bool(frappe.has_permission("Sales Invoice", "read") and frappe.has_permission("GL Entry", "read"))


def resolve_period(period, company, as_of):
	if period == "Last 12 months":
		return add_to_date(as_of, months=-12, as_string=False), as_of

	if period == "This quarter":
		quarter_start_month = ((as_of.month - 1) // 3) * 3 + 1
		return as_of.replace(month=quarter_start_month, day=1), as_of

	fy = get_fiscal_year(as_of, company=company, as_dict=True, raise_on_missing=False)
	if not fy:
		return add_to_date(as_of, months=-12, as_string=False), as_of

	if period == "Last fiscal year":
		prev = get_fiscal_year(
			add_days(getdate(fy.year_start_date), -1), company=company, as_dict=True, raise_on_missing=False
		)
		if prev:
			return getdate(prev.year_start_date), getdate(prev.year_end_date)

	return getdate(fy.year_start_date), min(as_of, getdate(fy.year_end_date))


def net_sales(customer, company, from_date, to_date):
	si = DocType("Sales Invoice")
	result = (
		frappe.qb.from_(si)
		.select(Coalesce(Sum(si.base_net_total), 0))
		.where(
			(si.docstatus == 1)
			& (si.customer == customer)
			& (si.company == company)
			& (si.posting_date >= from_date)
			& (si.posting_date <= to_date)
		)
	).run()
	return flt(result[0][0])


def position(customer, company, from_date, to_date, as_of, ar, accounts):
	cards = {}
	if not accounts:
		return cards

	current = net_sales(customer, company, from_date, to_date)
	prev = net_sales(customer, company, add_to_date(from_date, years=-1), add_to_date(to_date, years=-1))
	invoice_count = frappe.db.count(
		"Sales Invoice",
		{
			"docstatus": 1,
			"customer": customer,
			"company": company,
			"is_return": 0,
			"posting_date": ["between", [from_date, to_date]],
		},
	)
	cards["net_sales"] = {
		"value": current,
		"count": invoice_count,
		"delta": pct_change(current, prev),
		"delta_positive_is_good": True,
	}

	if not ar:
		return cards

	outstanding = ar["outstanding"]
	overdue = ar["overdue"]
	overdue_prev = receivables(customer, company, add_days(as_of, -30))["overdue"]

	unpaid_count = frappe.db.count(
		"Sales Invoice",
		{
			"docstatus": 1,
			"customer": customer,
			"company": company,
			"is_return": 0,
			"outstanding_amount": (">", 0),
		},
	)

	cards["outstanding"] = {
		"value": outstanding,
		"unpaid_count": unpaid_count,
		"days_to_pay": collection_days(customer, company, as_of, outstanding),
	}
	cards["overdue"] = {
		"value": overdue,
		"delta": pct_change(overdue, overdue_prev),
		"delta_positive_is_good": False,
	}

	advance = flt(ar.get("advance"))
	if advance:
		cards["advances"] = {"value": advance}

	credit_limit = flt(get_credit_limit(customer, company))
	cards["credit"] = {
		"limit": credit_limit,
		"used_pct": flt(outstanding / credit_limit * 100, 1) if credit_limit else None,
	}

	return cards


def collection_days(customer, company, as_of, outstanding):
	trailing = net_sales(customer, company, add_days(as_of, -365), as_of)
	if trailing <= 0:
		return None
	days = int(round(outstanding / (trailing / 365)))
	return days if days <= 730 else None


def receivables(customer, company, report_date):
	from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
		execute as ar_summary,
	)

	_columns, data = ar_summary(
		{
			"company": company,
			"report_date": report_date,
			"party_type": "Customer",
			"party": [customer],
			"ageing_based_on": "Due Date",
			"range": "30, 60, 90",
		}
	)
	row = data[0] if data else {}
	outstanding = flt(row.get("outstanding"))
	overdue = flt(row.get("total_due"))
	buckets = [
		{"key": "not_due", "label": _("Not due"), "value": outstanding - overdue, "overdue": False},
		{"key": "b1", "label": _("1–30 days"), "value": flt(row.get("range1")), "overdue": True},
		{"key": "b2", "label": _("31–60 days"), "value": flt(row.get("range2")), "overdue": True},
		{"key": "b3", "label": _("61–90 days"), "value": flt(row.get("range3")), "overdue": True},
		{"key": "b4", "label": _("90+ days"), "value": flt(row.get("range4")), "overdue": True},
	]
	return {
		"buckets": buckets,
		"outstanding": outstanding,
		"overdue": overdue,
		"advance": flt(row.get("advance")),
	}


def ageing(ar):
	if not ar:
		return None
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
	rows = (
		frappe.qb.from_(si)
		.select(si.posting_date, si.base_net_total)
		.where(
			(si.docstatus == 1)
			& (si.customer == customer)
			& (si.company == company)
			& (si.posting_date >= from_date)
			& (si.posting_date <= to_date)
		)
	).run(as_dict=True)
	by_month = {}
	for r in rows:
		month = getdate(r.posting_date).replace(day=1)
		by_month[month] = by_month.get(month, 0.0) + flt(r.base_net_total)

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
		tiles.update(invoice_tiles(customer, company, as_of))
	return tiles


def quotation_tiles(customer, company):
	quotation = DocType("Quotation")
	quote = (
		frappe.qb.from_(quotation)
		.select(
			Coalesce(Sum(quotation.base_grand_total), 0).as_("value"),
			Count(quotation.name).as_("count"),
		)
		.where(
			(quotation.docstatus == 1)
			& (quotation.status == "Open")
			& (quotation.quotation_to == "Customer")
			& (quotation.party_name == customer)
			& (quotation.company == company)
		)
	).run(as_dict=True)[0]
	return {"quotations": {"value": flt(quote.value), "count": quote.count}}


def sales_order_tiles(customer, company, as_of):
	so = DocType("Sales Order")
	open_so = (
		(so.docstatus == 1)
		& (so.customer == customer)
		& (so.company == company)
		& (so.status.notin(OPEN_SO_STATUS))
	)

	delivery = (
		frappe.qb.from_(so)
		.select(
			Coalesce(Sum(so.base_grand_total * (100 - so.per_delivered) / 100), 0).as_("value"),
			Count(so.name).as_("count"),
			Coalesce(Sum(Case().when(so.delivery_date < as_of, 1).else_(0)), 0).as_("past_due"),
		)
		.where(open_so & (so.per_delivered < 100))
	).run(as_dict=True)[0]

	billing = (
		frappe.qb.from_(so)
		.select(
			Coalesce(Sum(so.base_grand_total * (100 - so.per_billed) / 100), 0).as_("value"),
			Count(so.name).as_("count"),
		)
		.where(open_so & (so.per_billed < 100))
	).run(as_dict=True)[0]
	return {
		"delivery": {
			"value": flt(delivery.value),
			"count": delivery.count,
			"past_due": delivery.past_due or 0,
		},
		"billing": {"value": flt(billing.value), "count": billing.count},
	}


def invoice_tiles(customer, company, as_of):
	si = DocType("Sales Invoice")
	invoices = (
		frappe.qb.from_(si)
		.select(
			Coalesce(Sum(si.outstanding_amount), 0).as_("value"),
			Count(si.name).as_("count"),
			Coalesce(Sum(Case().when(si.due_date < as_of, 1).else_(0)), 0).as_("overdue"),
		)
		.where(
			(si.docstatus == 1)
			& (si.customer == customer)
			& (si.company == company)
			& (si.is_return == 0)
			& (si.outstanding_amount > 0)
		)
	).run(as_dict=True)[0]
	return {
		"invoices": {
			"value": flt(invoices.value),
			"count": invoices.count,
			"overdue": invoices.overdue or 0,
		}
	}


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


TXN_SPECS = {
	"Sales Invoice": {
		"party_field": "customer",
		"extra": {},
		"fields": [
			"name",
			"posting_date as date",
			"status",
			"base_grand_total as amount",
			"outstanding_amount as outstanding",
			"is_return",
		],
		"order_by": "posting_date desc, creation desc",
		"row": lambda r: {
			"status": "Return" if r.is_return else r.status,
			"amount": flt(r.amount),
			"outstanding": flt(r.outstanding),
		},
	},
	"Sales Order": {
		"party_field": "customer",
		"extra": {},
		"fields": ["name", "transaction_date as date", "status", "base_grand_total as amount", "per_billed"],
		"order_by": "transaction_date desc, creation desc",
		"row": lambda r: {
			"status": r.status,
			"amount": flt(r.amount),
			"outstanding": flt(r.amount) * (100 - flt(r.per_billed)) / 100,
		},
	},
	"Payment Entry": {
		"party_field": "party",
		"extra": {"party_type": "Customer"},
		"fields": [
			"name",
			"posting_date as date",
			"base_paid_amount as amount",
			"unallocated_amount as outstanding",
		],
		"order_by": "posting_date desc, creation desc",
		"row": lambda r: {"status": "Submitted", "amount": flt(r.amount), "outstanding": flt(r.outstanding)},
	},
}


def _fetch_rows(doctype, customer, company, limit):
	spec = TXN_SPECS[doctype]
	filters = {"docstatus": 1, "company": company, spec["party_field"]: customer, **spec["extra"]}
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
				**spec["row"](r),
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
	for doctype, field in (
		("Sales Invoice", "customer"),
		("Sales Order", "customer"),
		("Quotation", "party_name"),
	):
		if frappe.has_permission(doctype, "read"):
			companies.update(
				frappe.get_list(
					doctype, filters={field: customer, "docstatus": 1}, distinct=True, pluck="company"
				)
			)
	companies.discard(None)
	return sorted(companies)
