"""In-site helpers for accounts-code-review: fixtures, settings, outcomes, snapshots, invariants.

Runs inside `bench console` (engine.py loads it). Everything here is deterministic
for a given site and code: fixed posting date, explicit accounts and exchange
rates, and snapshots that replace every site-specific name with a stable label.
"""

import json
import re
from pathlib import Path

import frappe
from frappe.utils import add_days, add_years, flt, getdate

DATE = "2025-01-15"  # every scenario posts on this date; reports read as of REPORT_DATE
REPORT_DATE = "2025-02-14"
EUR_RATE = 1.1  # foreign currency per scenario: EUR, or USD when the company currency is EUR
EUR_PAYMENT_RATE = 1.2
DEFAULT_PROFILE = {"country": "United States", "currency": "USD", "chart_of_accounts": "Standard"}

# Item fields that an installed app makes mandatory through a hook, which the
# Item meta does not show. Each value is a query whose first row is used, so the
# choice is the same on every run. Add an app here when the preflight names it.
APP_ITEM_FIELDS = {
	"gst_hsn_code": "select name from `tabGST HSN Code` where char_length(name) in (6, 8) order by name limit 1",
}


# Records the review creates that no company owns, for cleanup: {doctype: [names]}.
# engine.py saves it to <workdir>/site-created.json after every session.
CREATED = {}

# ---------------------------------------------------------------- fixtures


def setup_company(company_name, abbr, company_values=None, profile=None):
	"""Create a company from the plan's profile, with every account the library needs."""
	profile = {**DEFAULT_PROFILE, **(profile or {})}
	if not frappe.db.exists("Company", company_name):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": abbr,
				"country": profile["country"],
				"default_currency": profile["currency"],
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": profile["chart_of_accounts"],
			}
		).insert()
	ensure_fiscal_year(company_name, DATE)
	ensure_fiscal_year(company_name, REPORT_DATE)

	company = frappe.get_doc("Company", company_name)
	ctx = frappe._dict(
		company=company.name,
		abbr=company.abbr,
		currency=company.default_currency,
		receivable=company.default_receivable_account,
		payable=company.default_payable_account,
		income=company.default_income_account,
		expense=company.default_expense_account,
		cash=company.default_cash_account,
		cost_center=company.cost_center,
		warehouse=frappe.db.get_value("Warehouse", {"company": company.name, "warehouse_name": "Stores"}),
	)
	ctx.bank = _leaf(company, "Review Bank", account_type="Bank", parent_type="Bank")
	ctx.tax = _leaf(company, "Review Tax", account_type="Tax", parent_type="Tax")
	ctx.foreign_currency = "USD" if company.default_currency == "EUR" else "EUR"
	ctx.receivable_eur = _leaf(
		company,
		f"Review Debtors {ctx.foreign_currency}",
		account_type="Receivable",
		parent_of=ctx.receivable,
		currency=ctx.foreign_currency,
	)
	if not company.exchange_gain_loss_account:
		company.db_set(
			"exchange_gain_loss_account", _leaf(company, "Review Exchange Gain Loss", parent_of=ctx.expense)
		)
	if company_values:
		company.reload()
		company.update(company_values)
		company.save()
	return ctx


def ensure_fiscal_year(company_name, date):
	"""Make sure the company has a fiscal year that contains date, without overlapping any.

	Sites differ: calendar years, April-March years, years limited to some
	companies. Use a year that already covers the date. Otherwise create one
	for this company only, in the gap between the years that apply to it.
	"""
	date = getdate(date)
	years = frappe.get_all("Fiscal Year", {"disabled": 0}, ["name", "year_start_date", "year_end_date"])
	for fy in years:
		fy.companies = frappe.get_all("Fiscal Year Company", {"parent": fy.name}, pluck="company")
	applies = [fy for fy in years if not fy.companies or company_name in fy.companies]
	if any(fy.year_start_date <= date <= fy.year_end_date for fy in applies):
		return

	start, end = getdate(f"{date.year}-01-01"), getdate(f"{date.year}-12-31")
	for fy in applies:
		if fy.year_end_date < date:
			start = max(start, getdate(add_days(fy.year_end_date, 1)))
		elif fy.year_start_date > date:
			end = min(end, getdate(add_days(fy.year_start_date, -1)))
	fy = frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": f"{company_name} {start}",
			"year_start_date": start,
			"year_end_date": end,
			# a gap between the site's years is shorter than a year; ERPNext allows that as a short year
			"is_short_year": int(getdate(add_days(add_years(start, 1), -1)) != end),
			"companies": [{"company": company_name}],
		}
	).insert()
	CREATED.setdefault("Fiscal Year", []).append(fy.name)


def make_masters(ctx, prefix, item_fields=None):
	"""Masters shared by every company of one review. Names are fixed by prefix."""
	ctx.customer = _party("Customer", f"{prefix} Customer", ctx.currency)
	ctx.supplier = _party("Supplier", f"{prefix} Supplier", ctx.currency)
	ctx.customer_eur = _party("Customer", f"{prefix} Customer {ctx.foreign_currency}", ctx.foreign_currency)
	_party_account("Customer", ctx.customer_eur, ctx.company, ctx.receivable_eur)
	ctx.service_item = _item(f"{prefix} Service", 0, item_fields)
	ctx.stock_item = _item(f"{prefix} Stock", 1, item_fields)
	return ctx


def _leaf(company, name, account_type=None, parent_type=None, parent_of=None, currency=None):
	existing = frappe.db.get_value("Account", {"company": company.name, "account_name": name})
	if existing:
		return existing
	if parent_type:
		parent = frappe.db.get_value(
			"Account", {"company": company.name, "account_type": parent_type, "is_group": 1}
		) or frappe.db.get_value("Account", {"company": company.name, "account_name": "Duties and Taxes"})
	else:
		parent = frappe.db.get_value("Account", parent_of, "parent_account")
	return (
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": name,
				"company": company.name,
				"parent_account": parent,
				"account_type": account_type,
				"account_currency": currency or company.default_currency,
			}
		)
		.insert()
		.name
	)


PARTY_GROUPS = {
	"Customer": {"customer_group": "Customer Group", "territory": "Territory"},
	"Supplier": {"supplier_group": "Supplier Group"},
}


def _party(doctype, name, currency):
	if frappe.db.exists(doctype, name):
		return name
	field = frappe.scrub(doctype)
	groups = {f: leaf(tree) for f, tree in PARTY_GROUPS[doctype].items()}
	return (
		frappe.get_doc(
			{
				"doctype": doctype,
				f"{field}_name": name,
				f"{field}_type": "Individual",
				"default_currency": currency,
				**groups,
			}
		)
		.insert()
		.name
	)


def leaf(tree_doctype):
	"""A non-group node of a tree, the same one on every run: the first by name.

	Site defaults (Selling Settings' customer group, for example) may point at a
	group node, which ERPNext rejects. Create a node when the tree has no leaf.
	"""
	name = frappe.db.get_value(tree_doctype, {"is_group": 0}, "name", order_by="name asc")
	if name:
		return name
	root = frappe.db.get_value(tree_doctype, {"is_group": 1}, "name", order_by="lft asc")
	field = frappe.scrub(tree_doctype) + "_name"
	doc = frappe.get_doc(
		{
			"doctype": tree_doctype,
			field: f"Review {tree_doctype}",
			f"parent_{frappe.scrub(tree_doctype)}": root,
		}
	).insert()
	CREATED.setdefault(tree_doctype, []).append(doc.name)
	return doc.name


def _party_account(doctype, party, company, account):
	doc = frappe.get_doc(doctype, party)
	if not any(row.company == company for row in doc.accounts):
		doc.append("accounts", {"company": company, "account": account})
		doc.save()


def item_fields(overrides=None):
	"""Plan overrides first, then APP_ITEM_FIELDS for fields the Item meta has."""
	fields = dict(overrides or {})
	meta = frappe.get_meta("Item")
	for field, query in APP_ITEM_FIELDS.items():
		if field not in fields and meta.has_field(field):
			rows = frappe.db.sql(query)
			if rows:
				fields[field] = rows[0][0]
	return fields


def _item(item_code, is_stock_item, item_fields):
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_group": leaf("Item Group"),
				"stock_uom": "Nos",
				"is_stock_item": is_stock_item,
				**(item_fields or {}),
			}
		).insert()
	return item_code


def day(offset):
	return add_days(DATE, offset)


# ---------------------------------------------------------------- settings
#
# A variant is {"id", "singles": {doctype: {field: value}}, "company": {field: value}}.
# Singles are site-wide. frappe.db caches single values per process, so the
# orchestrator switches them in one console session and runs phases in the next.


def record_originals(variants, path):
	path = Path(path)
	originals = json.loads(path.read_text()) if path.exists() else {}
	for variant in variants:
		for dt, values in variant.get("singles", {}).items():
			for field in values:
				if field not in originals.setdefault(dt, {}):
					originals[dt][field] = frappe.db.get_single_value(dt, field, cache=False)
	path.write_text(json.dumps(originals, indent=1, sort_keys=True, default=str))
	return originals


def target_singles(variant, originals):
	target = {dt: dict(values) for dt, values in originals.items()}
	for dt, values in variant.get("singles", {}).items():
		target.setdefault(dt, {}).update(values)
	return target


def save_singles(values_by_doctype):
	"""Save through the controller, so on_update side effects run as in desk."""
	for dt, values in sorted(values_by_doctype.items()):
		doc = frappe.get_single(dt)
		doc.update(values)
		doc.save()
	frappe.db.commit()
	frappe.clear_cache()


def singles_mismatch(expected):
	return [
		f"{dt}.{field}={frappe.db.get_single_value(dt, field, cache=False)!r}, want {value!r}"
		for dt, values in sorted(expected.items())
		for field, value in sorted(values.items())
		if str(frappe.db.get_single_value(dt, field, cache=False) or "") != str(value or "")
	]


# ---------------------------------------------------------------- lab


class Lab:
	"""One company's scenario run: the registry of labelled documents and action outcomes."""

	def __init__(self, ctx):
		self.ctx = ctx
		self.registry = {}
		self.outcomes = {}
		self.owners = {}  # label -> scenario id, for the report
		self.current = None

	def reg(self, label, doc):
		assert "." not in label, f"labels must not contain '.': {label}"
		self.registry[label] = [doc.doctype, doc.name]
		self.owners[label] = self.current
		return doc

	def get(self, label):
		return frappe.get_doc(*self.registry[label])

	def attempt(self, label, fn):
		"""Run fn in a savepoint; record "ok" or the error. Never raises."""
		savepoint = f"attempt_{len(self.outcomes)}"
		frappe.db.savepoint(savepoint)
		try:
			result = fn()
		except Exception as e:
			frappe.db.rollback(save_point=savepoint)
			frappe.local.message_log = []
			self.outcomes[label] = f"{type(e).__name__}: {frappe.utils.strip_html(str(e))[:300]}"
			return None
		self.outcomes[label] = "ok"
		return result


# ---------------------------------------------------------------- snapshot

DOC_FIELDS = (
	"docstatus",
	"status",
	"is_return",
	"return_against",
	"grand_total",
	"base_grand_total",
	"rounded_total",
	"total_taxes_and_charges",
	"outstanding_amount",
	"paid_amount",
	"received_amount",
	"base_paid_amount",
	"unallocated_amount",
	"total_allocated_amount",
	"difference_amount",
	"total_debit",
	"total_credit",
)
VOLATILE = {"name", "gl_entry", "creation", "modified", "owner", "modified_by", "idx"}
# Running totals depend on the order of rows that tie on posting date, which the
# reports leave to the database. Closing balances are in snapshot["balances"].
RUNNING_TOTALS = {
	"balance",
	"balance_in_account_currency",
	"bal_in_account_currency",
	"bal_in_company_currency",
}


def snapshot(lab, reports):
	"""Company-wide ledger state with every site-specific name replaced by a stable label."""
	ctx = lab.ctx
	norm = _Normalizer(_name_map(lab), ctx.company, ctx.abbr)

	gl, ple = {}, {}
	for row in frappe.get_all(
		"GL Entry",
		{"company": ctx.company},
		[
			"voucher_type",
			"voucher_no",
			"account",
			"party",
			"debit",
			"credit",
			"against_voucher",
			"is_cancelled",
		],
		order_by="creation, name",
	):
		gl.setdefault(norm(row.pop("voucher_no")), []).append(norm(row))
	for row in frappe.get_all(
		"Payment Ledger Entry",
		{"company": ctx.company},
		["voucher_type", "voucher_no", "account", "party", "amount", "against_voucher_no", "delinked"],
		order_by="creation, name",
	):
		ple.setdefault(norm(row.pop("voucher_no")), []).append(norm(row))

	balances = {
		norm(row.account): flt(row.net, 6)
		for row in frappe.db.sql(
			"""select account, sum(debit) - sum(credit) net from `tabGL Entry`
			where company=%s and is_cancelled=0 group by account""",
			ctx.company,
			as_dict=1,
		)
	}

	docs = {}
	for label, (doctype, name) in lab.registry.items():
		doc = frappe.get_doc(doctype, name)
		docs[label] = {f: norm(doc.get(f)) for f in DOC_FIELDS if f == "docstatus" or doc.meta.has_field(f)}

	return {
		"docs": dict(sorted(docs.items())),
		"gl": {k: sorted(v, key=_sort_key) for k, v in sorted(gl.items())},
		"ple": {k: sorted(v, key=_sort_key) for k, v in sorted(ple.items())},
		"balances": dict(sorted(balances.items())),
		"outcomes": {k: norm(v) for k, v in sorted(lab.outcomes.items())},
		"reports": {
			label: _report(name, filters, norm) for label, (name, filters) in sorted(reports.items())
		},
		"invariants": check_invariants(ctx.company, norm),
	}


def name_map(lab):
	"""Every name a snapshot or the browser may show, mapped to its stable placeholder."""
	names = _name_map(lab)
	names[lab.ctx.company] = "<company>"
	return names


def _name_map(lab):
	"""Registered names -> <label>; every other voucher -> <Type#k> in creation order."""
	names = {name: f"<{label}>" for label, (_, name) in lab.registry.items()}
	counters = {}
	for doctype in ("GL Entry", "Payment Ledger Entry"):
		for row in frappe.get_all(
			doctype, {"company": lab.ctx.company}, ["voucher_type", "voucher_no"], order_by="creation, name"
		):
			if row.voucher_no not in names:
				counters[row.voucher_type] = counters.get(row.voucher_type, 0) + 1
				names[row.voucher_no] = f"<{row.voucher_type}#{counters[row.voucher_type]}>"
	return names


class _Normalizer:
	"""Exact names map whole; inside longer strings a name matches only at word boundaries,
	so company "X C" never rewrites "X Customer"."""

	def __init__(self, names, company, abbr):
		self.exact = dict(names)
		self.exact[company] = "<company>"
		alternatives = sorted(self.exact, key=len, reverse=True)
		self.pattern = re.compile("|".join(rf"(?<![\w-]){re.escape(n)}(?![\w-])" for n in alternatives))
		self.abbr_suffix = f" - {abbr}"

	def __call__(self, value):
		if isinstance(value, dict):
			return {k: self(v) for k, v in value.items() if k not in VOLATILE}
		if isinstance(value, list | tuple):
			return [self(v) for v in value]
		if isinstance(value, str):
			if value in self.exact:
				return self.exact[value]
			value = self.pattern.sub(lambda m: self.exact[m.group(0)], value)
			return value.replace(self.abbr_suffix, "")
		if isinstance(value, bool) or value is None:
			return value
		if isinstance(value, int | float):
			return flt(value, 6)
		return str(value)


def _sort_key(row):
	return json.dumps(row, sort_keys=True, default=str)


def _report(report_name, filters, norm):
	from frappe.desk.query_report import run

	try:
		result = run(report_name, filters=filters, ignore_prepared_report=True)
	except Exception as e:
		return f"ERROR {type(e).__name__}: {norm(str(e))[:300]}"
	rows = [norm(row) for row in result.get("result") or []]
	rows = [
		{k: v for k, v in r.items() if k not in RUNNING_TOTALS} if isinstance(r, dict) else r for r in rows
	]
	return sorted(rows, key=lambda r: (not isinstance(r, dict), _sort_key(r)))


def standard_reports(ctx):
	from erpnext.accounts.utils import get_fiscal_year

	fy = get_fiscal_year(DATE, company=ctx.company)[0]
	# "range" is the filter since v16; range1..range4 before it. Each version ignores the other.
	ageing = {
		"ageing_based_on": "Due Date",
		"range": "30, 60, 90, 120",
		"range1": 30,
		"range2": 60,
		"range3": 90,
		"range4": 120,
	}
	return {
		"general_ledger": (
			"General Ledger",
			{
				"company": ctx.company,
				"from_date": DATE,
				"to_date": REPORT_DATE,
				"group_by": "Group by Voucher (Consolidated)",
			},
		),
		"trial_balance": (
			"Trial Balance",
			{"company": ctx.company, "fiscal_year": fy, "from_date": DATE, "to_date": REPORT_DATE},
		),
		"accounts_receivable": (
			"Accounts Receivable",
			{"company": ctx.company, "report_date": REPORT_DATE, **ageing},
		),
		"accounts_payable": (
			"Accounts Payable",
			{"company": ctx.company, "report_date": REPORT_DATE, **ageing},
		),
	}


# ---------------------------------------------------------------- invariants


def check_invariants(company, norm=str):
	"""Ledger invariants that must hold for any company. Returns sorted violations."""
	violations = []
	for v in frappe.db.sql(
		"""select voucher_type, voucher_no, sum(debit) dr, sum(credit) cr from `tabGL Entry`
		where company=%s and is_cancelled=0 group by voucher_type, voucher_no
		having abs(sum(debit) - sum(credit)) > 0.005""",
		company,
		as_dict=1,
	):
		violations.append(
			f"unbalanced GL: {v.voucher_type} {norm(v.voucher_no)} Dr {flt(v.dr, 2)} Cr {flt(v.cr, 2)}"
		)

	for table, live in (("GL Entry", "is_cancelled=0"), ("Payment Ledger Entry", "delinked=0")):
		for v in frappe.db.sql(
			f"select distinct voucher_type, voucher_no from `tab{table}` where company=%s and {live}",
			company,
			as_dict=1,
		):
			if frappe.db.get_value(v.voucher_type, v.voucher_no, "docstatus") != 1:
				violations.append(
					f"live {table} for non-submitted voucher: {v.voucher_type} {norm(v.voucher_no)}"
				)

	for doctype in ("Sales Invoice", "Purchase Invoice"):
		for inv in frappe.get_all(
			doctype,
			{"company": company, "docstatus": 1},
			["name", "outstanding_amount", "is_return", "return_against"],
		):
			if inv.is_return and inv.return_against:
				continue
			ple = frappe.db.sql(
				"""select coalesce(sum(amount_in_account_currency), 0) from `tabPayment Ledger Entry`
				where against_voucher_type=%s and against_voucher_no=%s and delinked=0""",
				(doctype, inv.name),
			)[0][0]
			if abs(flt(ple) - flt(inv.outstanding_amount)) > 0.005:
				violations.append(
					f"outstanding mismatch: {doctype} {norm(inv.name)} "
					f"doc={flt(inv.outstanding_amount, 2)} ple={flt(ple, 2)}"
				)

	dr, cr = frappe.db.sql(
		"select sum(debit), sum(credit) from `tabGL Entry` where company=%s and is_cancelled=0", company
	)[0]
	if abs(flt(dr) - flt(cr)) > 0.005:
		violations.append(f"trial balance off: Dr {flt(dr, 2)} Cr {flt(cr, 2)}")
	return sorted(violations)


# ---------------------------------------------------------------- cleanup

MASTERS = ("Customer", "Supplier", "Item")
TRAILS = (
	("Version", "ref_doctype", "docname"),
	("Comment", "reference_doctype", "reference_name"),
	("Activity Log", "reference_doctype", "reference_name"),
)


def delete_review_data(prefix, created, since):
	"""Delete everything one run created on the site. Returns what is left (should be empty).

	Transactions go through ERPNext's own Transaction Deletion Record, so every
	ledger, stock and payment table that has a company field is covered.
	"""
	started = frappe.utils.now()
	deleted, touched = [], {"Company", "Transaction Deletion Record", *MASTERS, *created}
	# Fiscal years first, while their company rows still show which run they belong to.
	for fy in created.get("Fiscal Year", []):
		if frappe.db.exists("Fiscal Year", fy) and _review_only(fy, prefix):
			frappe.delete_doc("Fiscal Year", fy, force=True, ignore_permissions=True)
			deleted.append(("Fiscal Year", fy))
	for company in frappe.get_all("Company", {"company_name": ("like", f"{prefix} %")}, pluck="name"):
		tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
		tdr.insert(ignore_permissions=True)
		if hasattr(tdr, "generate_to_delete_list"):  # v16+: the list is built before submit
			tdr.generate_to_delete_list()
			tdr.reload()
		tdr.process_in_single_transaction = True
		tdr.submit()
		tdr.reload()
		if tdr.status == "Queued":  # v15: submit only queues; start the tasks here
			tdr.start_deletion_tasks()
			tdr.reload()
		touched.update(row.doctype_name for row in tdr.doctypes)
		if tdr.status != "Completed":
			raise RuntimeError(
				f"Transaction Deletion Record {tdr.name} for {company}: {tdr.status} {tdr.error_log or ''}"
			)
		frappe.db.delete("Fiscal Year Company", {"company": company})
		frappe.delete_doc("Company", company, force=True, ignore_permissions=True)
		_drop_doc("Transaction Deletion Record", tdr.name)
		deleted.append(("Company", company))

	frappe.db.delete("Item Price", {"item_code": ("like", f"{prefix} %")})
	for doctype in MASTERS:
		for name in frappe.get_all(doctype, {"name": ("like", f"{prefix} %")}, pluck="name"):
			frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
			deleted.append((doctype, name))

	for doctype, names in sorted(created.items()):
		if doctype == "Fiscal Year":
			continue
		for name in names:
			if frappe.db.exists(doctype, name):
				frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
				deleted.append((doctype, name))

	# Trails of records that no longer exist and were written during the run.
	for doctype, ref_dt, ref_name in TRAILS if since else ():
		for row in frappe.get_all(doctype, {"creation": (">=", since)}, ["name", ref_dt, ref_name]):
			if row[ref_dt] in touched and row[ref_name] and not frappe.db.exists(row[ref_dt], row[ref_name]):
				frappe.db.delete(doctype, {"name": row.name})
	frappe.db.delete(
		"Deleted Document", {"creation": (">=", started), "deleted_doctype": ("in", sorted(touched))}
	)
	return remaining_review_data(prefix, created)


def remaining_review_data(prefix, created):
	left = {}
	for doctype in ("Company", *MASTERS):
		field = "company_name" if doctype == "Company" else "name"
		found = frappe.get_all(doctype, {field: ("like", f"{prefix} %")}, pluck="name")
		if found:
			left[doctype] = found
	for doctype in ("GL Entry", "Payment Ledger Entry", "Stock Ledger Entry"):
		count = frappe.db.count(doctype, {"company": ("like", f"{prefix} %")})
		if count:
			left[doctype] = count
	for doctype, names in created.items():
		found = [
			n
			for n in names
			if frappe.db.exists(doctype, n) and (doctype != "Fiscal Year" or _review_only(n, prefix))
		]
		if found:
			left[doctype] = found
	return left


def _review_only(fy, prefix):
	"""True when every company the fiscal year is limited to belongs to this run."""
	companies = frappe.get_all("Fiscal Year Company", {"parent": fy}, pluck="company")
	return all(c.startswith(f"{prefix} ") for c in companies)


def _drop_doc(doctype, name):
	"""Delete a document if it still exists (deleting a company removes some of its records)."""
	if not frappe.db.exists(doctype, name):
		return
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus == 1:
		doc.cancel()
	frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
