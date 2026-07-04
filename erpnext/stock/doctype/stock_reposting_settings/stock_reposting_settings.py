# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_to_date,
	get_datetime,
	get_link_to_form,
	get_time_str,
	getdate,
	time_diff_in_hours,
	today,
)
from frappe.utils.user import get_users_with_role


class StockRepostingSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		do_not_fetch_incoming_rate_from_serial_no: DF.Check
		enable_parallel_reposting: DF.Check
		enable_separate_reposting_for_gl: DF.Check
		end_time: DF.Time | None
		item_based_reposting: DF.Check
		limit_reposting_timeslot: DF.Check
		limits_dont_apply_on: DF.Literal[
			"", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
		]
		no_of_parallel_reposting: DF.Int
		notify_reposting_error_to_role: DF.Link | None
		repost_incorrect_valuation_entries: DF.Check
		start_time: DF.Time | None
	# end: auto-generated types

	def validate(self):
		self.set_minimum_reposting_time_slot()

	def before_save(self):
		self.reset_parallel_reposting_settings()

	def reset_parallel_reposting_settings(self):
		if not self.item_based_reposting and self.enable_parallel_reposting:
			self.enable_parallel_reposting = 0

		if self.enable_parallel_reposting and not self.no_of_parallel_reposting:
			self.no_of_parallel_reposting = 4

	def set_minimum_reposting_time_slot(self):
		"""Ensure that timeslot for reposting is at least 12 hours."""
		if not self.limit_reposting_timeslot:
			return

		start_time = get_datetime(self.start_time)
		end_time = get_datetime(self.end_time)

		if start_time > end_time:
			end_time = add_to_date(end_time, days=1, as_datetime=True)

		diff = time_diff_in_hours(end_time, start_time)

		if diff < 10:
			self.end_time = get_time_str(add_to_date(self.start_time, hours=10, as_datetime=True))

	@frappe.whitelist(methods=["POST"])
	def convert_to_item_wh_reposting(self):
		"""Convert Transaction reposting to Item Warehouse based reposting if Item Based Reposting has enabled."""

		reposting_data = get_reposting_entries()

		vouchers = [d.voucher_no for d in reposting_data]

		item_warehouses = {}

		for ledger in get_stock_ledgers(vouchers):
			key = (ledger.item_code, ledger.warehouse)
			if key not in item_warehouses:
				item_warehouses[key] = ledger.posting_date
			elif frappe.utils.getdate(item_warehouses.get(key)) > frappe.utils.getdate(ledger.posting_date):
				item_warehouses[key] = ledger.posting_date

		for key, posting_date in item_warehouses.items():
			item_code, warehouse = key
			create_repost_item_valuation(item_code, warehouse, posting_date)

		for row in reposting_data:
			frappe.db.set_value("Repost Item Valuation", row.name, "status", "Skipped")

		self.db_set("item_based_reposting", 1)
		frappe.msgprint(_("Item Warehouse based reposting has been enabled."))


def get_reposting_entries():
	return frappe.get_all(
		"Repost Item Valuation",
		fields=["voucher_no", "name"],
		filters={"status": ("in", ["Queued", "In Progress"]), "docstatus": 1, "based_on": "Transaction"},
	)


def get_stock_ledgers(vouchers):
	return frappe.get_all(
		"Stock Ledger Entry",
		fields=["item_code", "warehouse", "posting_date", "posting_time", "posting_datetime"],
		filters={"voucher_no": ("in", vouchers)},
	)


def create_repost_item_valuation(item_code, warehouse, posting_date):
	frappe.get_doc(
		{
			"doctype": "Repost Item Valuation",
			"company": frappe.get_cached_value("Warehouse", warehouse, "company"),
			"posting_date": posting_date,
			"based_on": "Item and Warehouse",
			"posting_time": "00:00:01",
			"item_code": item_code,
			"warehouse": warehouse,
			"allow_negative_stock": True,
			"status": "Queued",
		}
	).submit()


def repost_incorrect_valuation_entries():
	"""Weekly scheduler entry point.

	When `repost_incorrect_valuation_entries` is enabled in Stock Reposting Settings, scan each
	company's Stock Ledger Variance and Stock and Account Value Comparison reports for incorrect stock
	valuation in the current financial year and auto-create reposts to correct them. Journal Entries are
	never reposted, and warehouses pointing at a non-'Stock' account are reported to System Managers
	instead. Disabled by default; does nothing unless explicitly turned on."""
	if not frappe.db.get_single_value("Stock Reposting Settings", "repost_incorrect_valuation_entries"):
		return

	for company in frappe.get_all("Company", pluck="name"):
		# The Stock Ledger Variance scan runs the invariant check for every item-warehouse, so process
		# each company as its own long-running background job rather than blocking the weekly scheduler.
		frappe.enqueue(
			repost_incorrect_valuation_entries_for_company,
			queue="long",
			job_id=f"repost_incorrect_valuation::{company}",
			deduplicate=True,
			company=company,
		)


def repost_incorrect_valuation_entries_for_company(company):
	"""Detect and repost incorrect stock valuation for a single company, limited to the current
	financial year, using two reports:

	1. Stock Ledger Variance - item-warehouses whose ledger valuation is internally inconsistent
	   (typically a wrong previous-SLE pick). Fixed with an Item & Warehouse repost.
	2. Stock and Account Value Comparison - vouchers whose stock value does not match the accounting
	   ledger. Reposted via the report's own logic (Journal Entries are excluded - ERPNext does not
	   repost them). If a voucher's warehouse points at an account that is not of type 'Stock',
	   reposting can never clear the difference, so System Managers are notified instead."""
	from erpnext.accounts.utils import get_fiscal_year

	fy_start_date = get_fiscal_year(today(), company=company)[1]

	_repost_stock_ledger_variance(company, fy_start_date)
	_repost_stock_account_value_comparison(company, fy_start_date)


def _repost_stock_ledger_variance(company, fy_start_date):
	from erpnext.stock.report.stock_ledger_variance.stock_ledger_variance import (
		get_data as get_stock_ledger_variance,
	)

	created = []
	for row in get_stock_ledger_variance({"company": company}) or []:
		row = frappe._dict(row)

		# Only correct issues that originate in the current financial year.
		if not row.posting_date or getdate(row.posting_date) < getdate(fy_start_date):
			continue

		# Avoid piling up duplicate reposts week over week for the same item-warehouse.
		if has_pending_valuation_repost(company, row.item_code, row.warehouse):
			continue

		create_repost_item_valuation(row.item_code, row.warehouse, row.posting_date)
		created.append(row)

	if created:
		frappe.logger("stock_reposting").info(
			f"Auto-reposted {len(created)} incorrect-valuation item-warehouse(s) for {company}: "
			+ ", ".join(f"{d.item_code} @ {d.warehouse} from {d.posting_date}" for d in created)
		)

	return created


def _repost_stock_account_value_comparison(company, fy_start_date):
	import erpnext

	# Stock vs accounting values only exist under perpetual inventory.
	if not erpnext.is_perpetual_inventory_enabled(company):
		return

	from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
		create_reposting_entries,
	)
	from erpnext.stock.report.stock_and_account_value_comparison.stock_and_account_value_comparison import (
		get_data as get_value_comparison,
	)

	to_repost = []
	misconfigured = []  # (voucher_type, voucher_no, warehouse, account)

	# Scope the report's DB scan to the current financial year (see get_data) instead of loading every
	# voucher ever posted and filtering in Python afterwards.
	comparison_filters = frappe._dict(company=company, from_date=fy_start_date, as_on_date=today())
	for row in get_value_comparison(comparison_filters) or []:
		row = frappe._dict(row)

		# ERPNext does not repost Journal Entries (GL-only postings have no stock ledger to repost).
		if row.voucher_type == "Journal Entry":
			continue

		# Only correct issues that originate in the current financial year.
		if not row.posting_date or getdate(row.posting_date) < getdate(fy_start_date):
			continue

		# If a warehouse on this voucher is mapped to an account that is not of type 'Stock', reposting
		# can never reconcile stock vs accounting value - flag it for a human instead of reposting.
		# Only flag accounts with a concrete, non-'Stock' type. An unset/blank account_type is treated as
		# "unknown" - reposting may well reconcile it - so we don't skip the voucher or email a false alarm.
		wrong_accounts = [
			(warehouse, account)
			for warehouse, account, account_type in get_voucher_warehouse_accounts(row.voucher_no, company)
			if account_type and account_type != "Stock"
		]
		if wrong_accounts:
			misconfigured.extend(
				(row.voucher_type, row.voucher_no, warehouse, account)
				for warehouse, account in wrong_accounts
			)
			continue

		to_repost.append(row)

	if to_repost:
		# create_reposting_entries reposts Purchase Receipt/Invoice transaction-wise and everything else
		# item-warehouse-wise, and de-duplicates against existing reposts.
		create_reposting_entries(to_repost, company)
		frappe.logger("stock_reposting").info(
			f"Auto-reposted {len(to_repost)} stock/account value mismatch voucher(s) for {company}."
		)

	if misconfigured:
		notify_incorrect_stock_account(company, misconfigured)


def get_voucher_warehouse_accounts(voucher_no, company):
	"""Return (warehouse, account, account_type) for each distinct warehouse the voucher posted stock
	into, so the caller can verify the account is a 'Stock' asset account."""
	warehouses = frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_no": voucher_no, "is_cancelled": 0},
		pluck="warehouse",
		distinct=True,
	)

	rows = []
	for warehouse in {w for w in warehouses if w}:
		account = frappe.get_cached_value("Warehouse", warehouse, "account") or frappe.get_cached_value(
			"Company", company, "default_inventory_account"
		)
		account_type = frappe.get_cached_value("Account", account, "account_type") if account else None
		rows.append((warehouse, account, account_type))

	return rows


def notify_incorrect_stock_account(company, misconfigured):
	"""Email System Managers about warehouse accounts that are not of type 'Stock', which keep stock
	and accounting values from reconciling even after reposting."""
	recipients = get_users_with_role("System Manager")
	if not recipients:
		return

	items = "".join(
		"<li>{} {} &rarr; {}: {}</li>".format(
			voucher_type,
			get_link_to_form(voucher_type, voucher_no),
			warehouse,
			account or _("No account set"),
		)
		for voucher_type, voucher_no, warehouse, account in misconfigured
	)

	subject = _("Incorrect Stock Asset Account in {0}").format(company)
	message = (
		_("Stock and accounting values could not be reconciled by reposting for {0}.").format(
			frappe.bold(company)
		)
		+ "<br><br>"
		+ _(
			"The warehouse account(s) below are not of type 'Stock'. Please set a correct Stock asset account on the warehouse (Account Type must be 'Stock'):"
		)
		+ f"<ul>{items}</ul>"
	)

	frappe.sendmail(recipients=recipients, subject=subject, message=message)


def has_pending_valuation_repost(company, item_code, warehouse):
	"""True if an Item & Warehouse repost for this item-warehouse is already queued or running, so the
	weekly job does not stack duplicate reposts."""
	return bool(
		frappe.db.exists(
			"Repost Item Valuation",
			{
				"company": company,
				"item_code": item_code,
				"warehouse": warehouse,
				"based_on": "Item and Warehouse",
				"status": ("in", ["Queued", "In Progress"]),
				"docstatus": 1,
			},
		)
	)
