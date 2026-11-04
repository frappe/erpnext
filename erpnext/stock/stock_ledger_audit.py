# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Min
from frappe.utils import add_days, cint, get_datetime, now_datetime, today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check import (
	SLE_FIELDS,
	add_invariant_check_fields,
	is_sle_has_correct_data,
)

RECENT_CHANGES_DAYS = 7


def audit_recent_stock_ledger_entries():
	enqueue_company_audits(changed_since=add_days(now_datetime(), -RECENT_CHANGES_DAYS))


def audit_stock_ledger_entries():
	enqueue_company_audits()


def enqueue_company_audits(changed_since=None):
	for company in frappe.get_all("Company", pluck="name"):
		frappe.enqueue(
			audit_company_stock_ledger_entries,
			queue="long",
			timeout=3600,
			job_id=f"audit_stock_ledger_entries::{company}",
			deduplicate=True,
			company=company,
			changed_since=changed_since,
		)


def audit_company_stock_ledger_entries(company, changed_since=None):
	fiscal_years = get_fiscal_year(today(), company=company, boolean=True)
	if fiscal_years:
		StockLedgerAudit(company, fiscal_years[0][1], changed_since).run()


class StockLedgerAudit:
	def __init__(self, company, from_date, changed_since=None):
		self.company = company
		self.from_datetime = get_datetime(from_date)
		self.changed_since = changed_since
		self.float_precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 3
		self.currency_precision = (
			cint(frappe.db.get_single_value("System Settings", "currency_precision")) or self.float_precision
		)
		self.item_warehouses_in_repost = self.get_item_warehouses_in_repost()

	def run(self):
		for (item_code, warehouse), from_datetime in self.get_audit_start_datetimes().items():
			self.audit(item_code, warehouse, from_datetime)

	def audit(self, item_code, warehouse, from_datetime):
		if (item_code, warehouse) in self.item_warehouses_in_repost:
			return

		sle = self.get_first_incorrect_sle(item_code, warehouse, from_datetime)
		if sle and not self.has_scheduler_repost(sle):
			self.create_repost(sle)

	def get_audit_start_datetimes(self):
		if not self.changed_since:
			return dict.fromkeys(self.get_item_warehouses(), self.from_datetime)

		start_datetimes = {}
		for item_code, warehouse, changed_from in self.get_changed_item_warehouses():
			key = (item_code, warehouse)
			from_datetime = max(get_datetime(changed_from), self.from_datetime)
			start_datetimes[key] = min(from_datetime, start_datetimes.get(key, from_datetime))

		return start_datetimes

	def get_item_warehouses(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		return (
			frappe.qb.from_(sle)
			.select(sle.item_code, sle.warehouse)
			.distinct()
			.where(
				(sle.company == self.company)
				& (sle.posting_datetime >= self.from_datetime)
				& (sle.is_cancelled == 0)
			)
		).run()

	def get_changed_item_warehouses(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		repost = frappe.qb.DocType("Repost Item Valuation")
		new_entries = (
			frappe.qb.from_(sle)
			.select(sle.item_code, sle.warehouse, Min(sle.posting_datetime))
			.where((sle.company == self.company) & (sle.modified >= self.changed_since))
			.groupby(sle.item_code, sle.warehouse)
		).run()
		finished_reposts = self.get_reposted_item_warehouses(
			repost.status.isin(["Completed", "Failed"]) & (repost.modified >= self.changed_since)
		)

		return [*new_entries, *finished_reposts]

	def get_item_warehouses_in_repost(self):
		repost = frappe.qb.DocType("Repost Item Valuation")
		reposts = self.get_reposted_item_warehouses(repost.status.isin(["Queued", "In Progress"]))
		return {row[:2] for row in reposts}

	def get_reposted_item_warehouses(self, condition):
		repost = frappe.qb.DocType("Repost Item Valuation")
		sle = frappe.qb.DocType("Stock Ledger Entry")
		condition &= (repost.company == self.company) & (repost.docstatus == 1)

		item_reposts = (
			frappe.qb.from_(repost)
			.select(repost.item_code, repost.warehouse, repost.posting_date)
			.where(condition & (repost.based_on == "Item and Warehouse"))
		).run()

		voucher_reposts = (
			frappe.qb.from_(repost)
			.inner_join(sle)
			.on((sle.voucher_type == repost.voucher_type) & (sle.voucher_no == repost.voucher_no))
			.select(sle.item_code, sle.warehouse, sle.posting_datetime)
			.distinct()
			.where(condition & (repost.based_on == "Transaction"))
		).run()

		return [*item_reposts, *voucher_reposts]

	def get_first_incorrect_sle(self, item_code, warehouse, from_datetime):
		sles = frappe.get_all(
			"Stock Ledger Entry",
			fields=[*SLE_FIELDS, "item_code", "warehouse"],
			filters={
				"item_code": item_code,
				"warehouse": warehouse,
				"is_cancelled": 0,
				"posting_datetime": (">=", from_datetime),
			},
			order_by="posting_datetime, creation",
		)

		filters = frappe._dict(item_code=item_code, warehouse=warehouse)
		add_invariant_check_fields(sles, filters, self.get_opening_sle(item_code, warehouse, from_datetime))

		for sle in sles:
			if not is_sle_has_correct_data(sle, self.float_precision, self.currency_precision):
				return sle

	def get_opening_sle(self, item_code, warehouse, from_datetime):
		return frappe.db.get_value(
			"Stock Ledger Entry",
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"is_cancelled": 0,
				"posting_datetime": ("<", from_datetime),
			},
			["qty_after_transaction", "stock_value"],
			order_by="posting_datetime desc, creation desc",
			as_dict=True,
		)

	def has_scheduler_repost(self, sle):
		return frappe.db.exists(
			"Repost Item Valuation",
			{
				"created_by_scheduler": 1,
				"docstatus": 1,
				"item_code": sle.item_code,
				"warehouse": sle.warehouse,
				"posting_date": sle.posting_date,
				"posting_time": sle.posting_time,
			},
		)

	def create_repost(self, sle):
		frappe.db.savepoint("stock_ledger_audit")
		try:
			frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Item and Warehouse",
					"company": self.company,
					"item_code": sle.item_code,
					"warehouse": sle.warehouse,
					"posting_date": sle.posting_date,
					"posting_time": sle.posting_time,
					"created_by_scheduler": 1,
				}
			).submit()
		except frappe.ValidationError:
			frappe.db.rollback(save_point="stock_ledger_audit")
			frappe.log_error(
				_("Unable to repost incorrect Stock Ledger Entry {0}").format(sle.name),
				reference_doctype="Stock Ledger Entry",
				reference_name=sle.name,
			)
