# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Max
from frappe.utils import flt, get_datetime, get_link_to_form, getdate, nowtime, today
from frappe.utils.caching import request_cache

from erpnext.stock.utils import get_valuation_method


class ItemStandardCost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		company: DF.Link
		effective_date: DF.Date
		item_code: DF.Link
		naming_series: DF.Literal["ISC-.YYYY.-"]
		revaluation_entry: DF.Link | None
		standard_rate: DF.Currency
	# end: auto-generated types

	def validate(self):
		self.validate_item()
		self.validate_effective_date()
		self.validate_rate()
		self.warn_backdated_transactions_will_be_blocked()

	def warn_backdated_transactions_will_be_blocked(self):
		# Heads-up while creating (R2 enforces it later on every stock voucher): once this rate is
		# effective, the item's stock transactions cannot be dated before the effective date.
		if not self.is_new():
			return
		frappe.msgprint(
			_(
				"Once this Standard Cost is submitted, stock transactions for Item {0} in {1} cannot be posted with a date before the Effective Date {2}. Post any backdated entries before submitting."
			).format(
				get_link_to_form("Item", self.item_code),
				frappe.bold(self.company),
				frappe.bold(frappe.format(self.effective_date, "Date")),
			),
			title=_("Backdated Entries Will Be Blocked"),
			indicator="orange",
			alert=True,
		)

	def validate_item(self):
		if not frappe.get_cached_value("Item", self.item_code, "is_stock_item"):
			frappe.throw(_("{0} is not a stock item.").format(frappe.bold(self.item_code)))

		if get_valuation_method(self.item_code, self.company) != "Standard Cost":
			frappe.throw(
				_("Valuation Method of Item {0} must be set to 'Standard Cost'.").format(
					get_link_to_form("Item", self.item_code)
				)
			)

	def validate_effective_date(self):
		# Standard cost is set "as of now"; future-dating would leave a gap where new receipts
		# are valued at a rate that is not yet effective.
		if getdate(self.effective_date) > getdate(today()):
			frappe.throw(_("Effective Date cannot be a future date."))

		# Effective dates must be strictly increasing so the rate history can be read by date.
		last = self.get_last_standard_cost()
		if last and getdate(self.effective_date) <= getdate(last.effective_date):
			frappe.throw(
				_("Effective Date must be after {0} (the last Standard Cost {1}).").format(
					frappe.bold(frappe.format(last.effective_date, "Date")),
					get_link_to_form("Item Standard Cost", last.name),
				)
			)

	def validate_rate(self):
		if flt(self.standard_rate) <= 0:
			frappe.throw(_("Standard Valuation Rate must be greater than zero."))

		if self.get_last_standard_cost() is None:
			# First-ever rate for this item+company: only allowed when no stock movement exists,
			# so the item starts its life under Standard Cost (no historical revaluation needed).
			if self.has_any_sle():
				frappe.throw(
					_(
						"Standard Cost can only be set up for {0} in {1} before any stock transaction exists."
					).format(get_link_to_form("Item", self.item_code), frappe.bold(self.company))
				)
			return

		# R1: a rate change must be effective on/after the latest stock activity, so the
		# revaluation entry it creates never sits behind existing transactions.
		last_sle_date = self.get_last_sle_date()
		if last_sle_date and getdate(self.effective_date) < getdate(last_sle_date):
			frappe.throw(
				_("Effective Date cannot be before the last stock transaction date {0}.").format(
					frappe.bold(frappe.format(last_sle_date, "Date"))
				)
			)

	def on_submit(self):
		# This record is now the effective rate. Drop any request-cached lookup that may have read the
		# previous (or missing) rate earlier in the request, so the revaluation below — and anything
		# else in this request — reads the newly submitted rate.
		clear_item_standard_rate_cache()

		# When a Stock Reconciliation captured this rate (opening entry or rate change), it has set
		# revaluation_entry to itself and performs the revaluation. Don't spawn another one.
		if self.revaluation_entry:
			return

		self.create_revaluation_entry()

	def before_cancel(self):
		self.validate_no_stock_activity_on_or_after_effective_date()

	def has_stock_activity_on_or_after_effective_date(self):
		"""Is there any live stock transaction for this item on or after the effective date, other than
		the revaluation Stock Reconciliation this record created? Such transactions are valued at this
		standard rate, so this record cannot be safely cancelled while they exist."""
		sle = frappe.qb.DocType("Stock Ledger Entry")
		query = (
			frappe.qb.from_(sle)
			.select(sle.name)
			.where(
				(sle.item_code == self.item_code)
				& (sle.company == self.company)
				& (sle.is_cancelled == 0)
				# posting_datetime (indexed) is preferred over posting_date; get_datetime on the date gives
				# the start of the effective date, so this matches everything on or after it.
				& (sle.posting_datetime >= get_datetime(self.effective_date))
			)
			.limit(1)
		)

		# The revaluation reco this record created posts on the effective date; exclude it, it is
		# reversed together with this document in on_cancel.
		if self.revaluation_entry:
			query = query.where(sle.voucher_no != self.revaluation_entry)

		return bool(query.run())

	def validate_no_stock_activity_on_or_after_effective_date(self):
		"""A submitted Item Standard Cost can be cancelled only when no stock transaction exists for the
		item on or after its effective date, other than the revaluation Stock Reconciliation it created.
		Later transactions are valued at this standard rate, so cancelling it would corrupt their
		valuation and force a repost."""
		if self.has_stock_activity_on_or_after_effective_date():
			frappe.throw(
				_(
					"Item Standard Cost cannot be cancelled because stock transactions exist for Item {0} on or after the Effective Date {1}. Cancel those transactions first."
				).format(
					get_link_to_form("Item", self.item_code),
					frappe.bold(frappe.format(self.effective_date, "Date")),
				)
			)

	def on_cancel(self):
		# Drop the cached standard rate first: this record is now cancelled, so the revaluation reversal
		# below (and anything else in this request) must re-read the previous effective rate, not this one.
		clear_item_standard_rate_cache()

		# Set when this cancellation was triggered by the source reconciliation itself (it is already
		# cancelling); reversing revaluation_entry would loop back into that same reconciliation.
		if self.flags.from_source_reconciliation:
			return

		# Reverse the revaluation this record created.
		if self.revaluation_entry:
			reco = frappe.get_doc("Stock Reconciliation", self.revaluation_entry)
			if reco.docstatus == 1:
				reco.flags.via_item_standard_cost = True
				reco.cancel()

	def create_revaluation_entry(self):
		"""Revalue on-hand stock to the new standard rate via a Stock Reconciliation.

		Submitted atomically: if the reconciliation cannot be submitted (closed period, frozen
		accounts, etc.) the exception propagates and this submission is rolled back."""
		balances = self.get_warehouse_wise_balance()
		if not balances:
			return

		reco = frappe.new_doc("Stock Reconciliation")
		reco.company = self.company
		reco.purpose = "Stock Reconciliation"
		reco.posting_date = self.effective_date
		reco.posting_time = self.get_revaluation_posting_time()
		reco.set_posting_time = 1
		for row in balances:
			reco.append(
				"items",
				{
					"item_code": self.item_code,
					"warehouse": row.warehouse,
					"qty": row.actual_qty,
					"valuation_rate": self.standard_rate,
				},
			)

		reco.flags.via_item_standard_cost = True
		reco.insert()
		reco.submit()

		self.db_set("revaluation_entry", reco.name)

	def get_revaluation_posting_time(self):
		"""Post the revaluation after the day's last stock movement.

		The reconciliation asserts the current on-hand quantity (Bin.actual_qty). If it were posted
		before later same-day movements, it would backdate that quantity ahead of them and corrupt the
		qty/value timeline. Using the time of the last SLE on the effective date (the reconciliation
		sorts after it on creation) keeps the snapshot at the correct point; if there is no movement
		that day, the current time is safe since no later movement can exist."""
		sle = frappe.qb.DocType("Stock Ledger Entry")
		result = (
			frappe.qb.from_(sle)
			.select(Max(sle.posting_datetime))
			.where(
				(sle.item_code == self.item_code)
				& (sle.company == self.company)
				& (sle.is_cancelled == 0)
				& (sle.posting_date == getdate(self.effective_date))
			)
		).run()

		last_datetime = result[0][0] if result and result[0][0] else None
		# Keep microsecond precision: posting_datetime is compared at microsecond granularity, so a
		# truncated time would sort the reco before a same-second movement. Matching the exact time
		# lets the later creation order the reco after it.
		return get_datetime(last_datetime).strftime("%H:%M:%S.%f") if last_datetime else nowtime()

	def get_warehouse_wise_balance(self):
		bin_table = frappe.qb.DocType("Bin")
		warehouse = frappe.qb.DocType("Warehouse")
		return (
			frappe.qb.from_(bin_table)
			.inner_join(warehouse)
			.on(bin_table.warehouse == warehouse.name)
			.select(bin_table.warehouse, bin_table.actual_qty)
			.where(
				(bin_table.item_code == self.item_code)
				& (warehouse.company == self.company)
				& (bin_table.actual_qty != 0)
			)
		).run(as_dict=True)

	def get_last_standard_cost(self):
		records = frappe.get_all(
			"Item Standard Cost",
			filters={
				"item_code": self.item_code,
				"company": self.company,
				"docstatus": 1,
				"name": ("!=", self.name),
			},
			fields=["name", "effective_date"],
			order_by="effective_date desc, creation desc",
			limit=1,
		)
		return records[0] if records else None

	def get_last_sle_date(self):
		sle = frappe.qb.DocType("Stock Ledger Entry")
		result = (
			frappe.qb.from_(sle)
			.select(Max(sle.posting_date))
			.where(
				(sle.item_code == self.item_code) & (sle.company == self.company) & (sle.is_cancelled == 0)
			)
		).run()
		return result[0][0] if result and result[0][0] else None

	def has_any_sle(self):
		return bool(
			frappe.db.exists(
				"Stock Ledger Entry",
				{"item_code": self.item_code, "company": self.company, "is_cancelled": 0},
			)
		)


@request_cache
def get_item_standard_rate(item_code, company, posting_date=None):
	"""Return the standard valuation rate effective for `item_code` in `company` as of
	`posting_date` (defaults to today) — i.e. the latest submitted Item Standard Cost whose
	effective date is on or before the posting date."""
	posting_date = posting_date or today()

	rate = frappe.get_all(
		"Item Standard Cost",
		filters={
			"item_code": item_code,
			"company": company,
			"docstatus": 1,
			"effective_date": ("<=", getdate(posting_date)),
		},
		fields=["standard_rate"],
		order_by="effective_date desc, creation desc",
		limit=1,
		pluck="standard_rate",
	)

	return flt(rate[0]) if rate else None


def has_item_standard_cost(item_code, company):
	"""True if a submitted Item Standard Cost exists for the item in the company (any effective date).
	Used to tell an opening Stock Reconciliation (no standard rate yet, rate is editable) apart from a
	later one (standard rate owned by Item Standard Cost, only quantity may be adjusted)."""
	return bool(
		frappe.db.exists(
			"Item Standard Cost",
			{"item_code": item_code, "company": company, "docstatus": 1},
		)
	)


def clear_item_standard_rate_cache():
	"""Drop the request-cached results of `get_item_standard_rate` so reads after a new Item Standard
	Cost is submitted see the fresh rate instead of a value cached earlier in the same request."""
	cache = getattr(frappe.local, "request_cache", None)
	if cache:
		cache.pop(get_item_standard_rate.__wrapped__, None)


def get_purchase_price_variance_account(item_code, company):
	"""Resolve the Purchase Price Variance account for a Standard Cost item: the per-company
	Item Default override if set, otherwise the Company default."""
	account = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"purchase_price_variance_account",
	)

	if not account:
		account = frappe.get_cached_value("Company", company, "default_purchase_price_variance_account")

	if not account:
		frappe.throw(
			_(
				"Please set a Purchase Price Variance Account for Item {0} or a Default Purchase Price Variance Account in Company {1}."
			).format(get_link_to_form("Item", item_code), frappe.bold(company))
		)

	return account


def get_manufacturing_variance_account(item_code, company):
	"""Resolve the Manufacturing Variance account for a Standard Cost item: the per-company Item Default
	override if set, otherwise the Company default. During Manufacture/Repack this account absorbs the
	difference between the consumed (raw material + additional) cost and the finished good's standard rate."""
	account = frappe.db.get_value(
		"Item Default",
		{"parent": item_code, "company": company},
		"manufacturing_variance_account",
	)

	if not account:
		account = frappe.get_cached_value("Company", company, "default_manufacturing_variance_account")

	if not account:
		frappe.throw(
			_(
				"Please set a Manufacturing Variance Account for Item {0} or a Default Manufacturing Variance Account in Company {1}."
			).format(get_link_to_form("Item", item_code), frappe.bold(company))
		)

	return account


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_standard_cost_items(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None
):
	"""Link-field query for Item Standard Cost: only items whose effective valuation method is
	'Standard Cost' — i.e. the item is explicitly Standard Cost, or it has no valuation method of its
	own and the applicable default (Company, else Stock Settings) is Standard Cost. This mirrors
	get_valuation_method, so every shown item also passes validate_item."""
	company = (filters or {}).get("company")
	if company:
		default_method = frappe.get_cached_value("Company", company, "valuation_method")
	else:
		default_method = frappe.db.get_single_value("Stock Settings", "valuation_method")

	if default_method == "Standard Cost":
		# Items with no method of their own inherit the Standard Cost default.
		valuation_condition = "and ifnull(item.valuation_method, '') in ('', 'Standard Cost')"
	else:
		valuation_condition = "and item.valuation_method = 'Standard Cost'"

	return frappe.db.sql(  # nosemgrep
		f"""
		select item.name, item.item_name
		from `tabItem` item
		where item.is_stock_item = 1
			and item.disabled = 0
			and item.has_variants = 0
			{valuation_condition}
			and ({searchfield} like %(txt)s or item.item_name like %(txt)s)
		order by
			(case when item.name like %(txt)s then 0 else 1 end),
			item.name
		limit %(page_len)s offset %(start)s
		""",
		{"txt": f"%{txt}%", "start": start, "page_len": page_len},
	)
