# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Migration patch for Tax Withholding Entry data.

This patch migrates historical TDS/TCS data from the old structure to the new
Tax Withholding Entry child table structure.

Old Structure:
- Purchase Invoice: taxes table (is_tax_withholding_account), tax_withheld_vouchers, advance_tax
- Sales Invoice: taxes table (TDS amount without is_tax_withholding_account checkbox)
- Payment Entry: advance_taxes_and_charges table with allocated_amount
- Journal Entry: accounts table with is_tax_withholding_account (but not reliable)

New Structure:
- All doctypes: tax_withholding_entries child table with detailed tracking
"""

from collections import defaultdict

import frappe
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Max, Sum
from frappe.utils import flt, now


def execute():
	tds_accounts = get_tds_accounts()
	if not tds_accounts:
		return

	tax_rate_map = get_tax_rate_map()
	column_cache = get_column_cache()
	party_tax_id_cache = {}

	# Clean up any existing migration entries
	frappe.db.delete("Tax Withholding Entry", filters={"created_by_migration": 1})

	# Migrate data from each document type
	# Purchase Invoice migration also handles Payment Entry TDS (allocated and unallocated)
	PurchaseInvoiceMigrator(tds_accounts, tax_rate_map, column_cache, party_tax_id_cache).migrate()
	migrate_sales_invoices(tds_accounts, tax_rate_map, column_cache, party_tax_id_cache)
	migrate_journal_entries(tds_accounts, tax_rate_map, column_cache, party_tax_id_cache)

	# Copy tax_withholding_category to item level
	copy_category_to_items_for_purchase(column_cache)
	copy_category_to_items_for_sales(column_cache)


def get_column_cache():
	return {
		"Supplier": {
			"pan": frappe.db.has_column("Supplier", "pan"),
			"tax_id": frappe.db.has_column("Supplier", "tax_id"),
		},
		"Customer": {
			"pan": frappe.db.has_column("Customer", "pan"),
			"tax_id": frappe.db.has_column("Customer", "tax_id"),
		},
		"Purchase Invoice": {
			"tax_withholding_category": frappe.db.has_column("Purchase Invoice", "tax_withholding_category"),
		},
		"Purchase Invoice Item": {
			"tax_withholding_category": frappe.db.has_column(
				"Purchase Invoice Item", "tax_withholding_category"
			),
		},
		"Sales Invoice": {
			"tax_withholding_category": frappe.db.has_column("Sales Invoice", "tax_withholding_category"),
		},
		"Sales Invoice Item": {
			"tax_withholding_category": frappe.db.has_column(
				"Sales Invoice Item", "tax_withholding_category"
			),
		},
	}


def get_tds_accounts():
	twa = frappe.qb.DocType("Tax Withholding Account")

	result = (
		frappe.qb.from_(twa).select(twa.account, twa.company, twa.parent.as_("category")).run(as_dict=True)
	)

	if not result:
		return None

	# Build lookup: {(company, account): category}
	# If account has multiple categories, set to None (ambiguous)
	account_map = {}
	for row in result:
		key = (row.company, row.account)
		if key in account_map:
			# Multiple categories use same account - ambiguous
			account_map[key] = None
		else:
			account_map[key] = row.category

	# Also build account set by company for quick lookup
	accounts_by_company = {}
	for row in result:
		accounts_by_company.setdefault(row.company, set()).add(row.account)

	return {"account_map": account_map, "accounts_by_company": accounts_by_company}


def get_tax_rate_map():
	twr = frappe.qb.DocType("Tax Withholding Rate")
	twc = frappe.qb.DocType("Tax Withholding Category")

	rates = (
		frappe.qb.from_(twr)
		.join(twc)
		.on(twr.parent == twc.name)
		.select(
			twr.parent,
			twr.tax_withholding_rate,
			twr.from_date,
			twr.to_date,
			twc.tax_on_excess_amount,
		)
		.run(as_dict=True)
	)

	rate_map = {}
	for rate in rates:
		rate_map.setdefault(rate.parent, []).append(rate)

	return rate_map


def get_tax_rate_for_date(tax_rate_map, category, posting_date):
	if not category or category not in tax_rate_map or not posting_date:
		return 0, False

	for rate in tax_rate_map[category]:
		if rate.from_date and rate.to_date and rate.from_date <= posting_date <= rate.to_date:
			return (rate.tax_withholding_rate, bool(rate.tax_on_excess_amount))

	return 0, False


def get_party_tax_id(party_type, party, column_cache, party_tax_id_cache):
	if not party:
		return None

	cache_key = (party_type, party)
	if cache_key in party_tax_id_cache:
		return party_tax_id_cache[cache_key]

	tax_id = None
	doctype_cols = column_cache.get(party_type, {})

	if doctype_cols.get("pan"):
		tax_id = frappe.db.get_value(party_type, party, "pan")
	elif doctype_cols.get("tax_id"):
		tax_id = frappe.db.get_value(party_type, party, "tax_id")

	party_tax_id_cache[cache_key] = tax_id
	return tax_id


def determine_status(taxable_name, withholding_name, under_withheld_reason, is_duplicate=False):
	"""Determine the status of a Tax Withholding Entry."""
	if is_duplicate:
		return "Duplicate"

	# If under_withheld_reason is specified, it's settled (legitimate reason for under deduction)
	if under_withheld_reason:
		return "Settled"

	# If both taxable and withholding are specified, it's settled
	if taxable_name and withholding_name:
		return "Settled"

	# If only taxable is specified, it's under withheld (tax not yet deducted)
	if taxable_name and not withholding_name:
		return "Under Withheld"

	# If only withholding is specified, it's over withheld (deducted but no taxable doc)
	if withholding_name and not taxable_name:
		return "Over Withheld"

	return ""


def bulk_insert_entries(all_entries):
	"""
	Bulk insert Tax Withholding Entries.
	all_entries: dict of {(parent_doctype, parent_name): [entries]}
	"""
	if not all_entries:
		return

	# Get existing names to avoid collisions
	existing_names = set(frappe.get_all("Tax Withholding Entry", pluck="name"))

	def generate_unique_name():
		while True:
			name = frappe.generate_hash(length=10)
			if name not in existing_names:
				existing_names.add(name)
				return name

	# Prepare all entries with proper fields
	fields = [
		"name",
		"creation",
		"modified",
		"modified_by",
		"owner",
		"docstatus",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
		"company",
		"party_type",
		"party",
		"tax_id",
		"tax_withholding_category",
		"tax_withholding_group",
		"taxable_amount",
		"tax_rate",
		"withholding_amount",
		"taxable_doctype",
		"taxable_name",
		"taxable_date",
		"withholding_doctype",
		"withholding_name",
		"withholding_date",
		"status",
		"under_withheld_reason",
		"currency",
		"conversion_rate",
		"created_by_migration",
	]

	current_time = now()
	current_user = frappe.session.user

	values = []
	for (parent_doctype, parent_name), entries in all_entries.items():
		for idx, entry in enumerate(entries, start=1):
			# Determine status
			status = determine_status(
				entry.get("taxable_name"),
				entry.get("withholding_name"),
				entry.get("under_withheld_reason"),
				entry.get("is_duplicate", False),
			)

			values.append(
				(
					generate_unique_name(),  # name
					current_time,  # creation
					current_time,  # modified
					current_user,  # modified_by
					current_user,  # owner
					1,  # docstatus (submitted)
					parent_name,  # parent
					"tax_withholding_entries",  # parentfield
					parent_doctype,  # parenttype
					idx,  # idx
					entry.get("company"),
					entry.get("party_type"),
					entry.get("party"),
					entry.get("tax_id"),
					entry.get("tax_withholding_category"),
					entry.get("tax_withholding_group", ""),
					flt(entry.get("taxable_amount"), 2),
					flt(entry.get("tax_rate"), 4),
					flt(entry.get("withholding_amount"), 2),
					entry.get("taxable_doctype", ""),
					entry.get("taxable_name", ""),
					entry.get("taxable_date"),
					entry.get("withholding_doctype", ""),
					entry.get("withholding_name", ""),
					entry.get("withholding_date"),
					status,
					entry.get("under_withheld_reason", ""),
					entry.get("currency", ""),
					flt(entry.get("conversion_rate"), 9) or 1,
					1,  # created_by_migration
				)
			)

	if values:
		frappe.db.bulk_insert("Tax Withholding Entry", fields, values, ignore_duplicates=True)


# =============================================================================
# PURCHASE INVOICE MIGRATION
# =============================================================================


class PurchaseInvoiceMigrator:
	def __init__(self, tds_accounts, tax_rate_map, column_cache, party_tax_id_cache):
		self.tds_accounts = tds_accounts
		self.tax_rate_map = tax_rate_map
		self.column_cache = column_cache
		self.party_tax_id_cache = party_tax_id_cache

		# Build TDS account set
		self.all_tds_accounts = set()
		for accounts in tds_accounts["accounts_by_company"].values():
			self.all_tds_accounts.update(accounts)

		# Raw query results
		self._invoices_with_tds = []
		self._all_withheld_vouchers = []
		self._all_advance_taxes = []
		self._pe_tds_entries = []

		# Lookups
		self.invoice_taxes = {}  # {invoice_name: {"info": row, "tax_rows": [], "tds_total": float}}
		self.withheld_by_invoice = defaultdict(list)  # {parent_invoice: [vouchers]}
		self.advance_by_invoice = defaultdict(list)  # {parent_invoice: [advance_taxes]}
		self.pe_allocated = defaultdict(float)  # {pe_name: total_allocated}
		self.pe_taxes = {}  # {pe_name: {"info": row, "tax_rows": [], "tds_total": float}}
		self.invoice_info = {}  # {invoice_name: row}

		# Sets for tracking
		self.invoices_with_twv = set()
		self.invoices_with_advance_tax = set()
		self.tds_paid_by_other = {}  # {taxable_invoice: withholding_invoice}

		# Date lookups
		self.pe_dates = {}
		self.pi_dates = {}
		self._pi_names_for_dates = set()
		self._pe_names_for_dates = set()

		# Output
		self.all_entries = {}  # {(doctype, name): [entries]}

	def migrate(self):
		if not self.all_tds_accounts:
			return

		self._fetch_data()
		self._build_lookups()
		self._fetch_dates()
		self._process_invoices()
		self._process_pe_overwithheld()
		bulk_insert_entries(self.all_entries)

	# -------------------------------------------------------------------------
	# Data Fetching
	# -------------------------------------------------------------------------

	def _fetch_data(self):
		pi = frappe.qb.DocType("Purchase Invoice")
		ptc = frappe.qb.DocType("Purchase Taxes and Charges")
		twv = frappe.qb.DocType("Tax Withheld Vouchers")
		at = frappe.qb.DocType("Advance Tax")
		pe = frappe.qb.DocType("Payment Entry")
		atc = frappe.qb.DocType("Advance Taxes and Charges")

		# Query 1: Invoices with TDS in taxes table
		self._invoices_with_tds = (
			frappe.qb.from_(pi)
			.join(ptc)
			.on(ptc.parent == pi.name)
			.select(
				pi.name,
				pi.supplier,
				pi.company,
				pi.posting_date,
				pi.base_net_total,
				pi.base_tax_withholding_net_total,
				pi.tax_withholding_category,
				pi.is_return,
				pi.currency,
				pi.conversion_rate,
				ptc.account_head,
				ptc.base_tax_amount_after_discount_amount,
			)
			.where(pi.docstatus == 1)
			.where(ptc.account_head.isin(list(self.all_tds_accounts)))
			.run(as_dict=True)
		)

		# Query 2: Tax withheld vouchers
		self._all_withheld_vouchers = (
			frappe.qb.from_(twv)
			# JV / PE withholding possible
			.left_join(pi)
			.on(twv.parent == pi.name)
			.select(
				twv.parent,
				twv.voucher_type,
				twv.voucher_name,
				twv.taxable_amount,
				pi.supplier,
				pi.company,
				pi.posting_date,
				pi.base_net_total,
				pi.base_tax_withholding_net_total,
				pi.tax_withholding_category,
				pi.is_return,
				pi.currency,
				pi.conversion_rate,
			)
			.where(twv.parenttype == "Purchase Invoice")
			.where(pi.docstatus == 1)
			.run(as_dict=True)
		)

		# Query 3: Advance taxes with PI info
		self._all_advance_taxes = (
			frappe.qb.from_(at)
			.join(pi)
			.on(at.parent == pi.name)
			.select(
				at.parent,
				at.reference_type,
				at.reference_name,
				at.account_head,
				at.allocated_amount,
				pi.supplier,
				pi.company,
				pi.posting_date,
				pi.base_net_total,
				pi.base_tax_withholding_net_total,
				pi.tax_withholding_category,
				pi.is_return,
				pi.currency,
				pi.conversion_rate,
			)
			.where(at.parenttype == "Purchase Invoice")
			.where(at.reference_type == "Payment Entry")
			.where(pi.docstatus == 1)
			.run(as_dict=True)
		)

		# Query 4: Payment Entries with TDS
		self._pe_tds_entries = (
			frappe.qb.from_(pe)
			.join(atc)
			.on(atc.parent == pe.name)
			.select(
				pe.name.as_("payment_entry"),
				pe.party_type,
				pe.party,
				pe.company,
				pe.posting_date,
				pe.paid_amount,
				pe.tax_withholding_category,
				pe.paid_from_account_currency,
				pe.paid_to_account_currency,
				pe.source_exchange_rate,
				pe.target_exchange_rate,
				pe.payment_type,
				atc.account_head,
				atc.base_tax_amount,
				atc.add_deduct_tax,
			)
			.where(pe.docstatus == 1)
			.where(pe.apply_tds == 1)
			.where(atc.account_head.isin(list(self.all_tds_accounts)))
			.run(as_dict=True)
		)

	# -------------------------------------------------------------------------
	# Lookup Building
	# -------------------------------------------------------------------------

	def _build_lookups(self):
		self._build_invoice_taxes_lookup()
		self._build_withheld_vouchers_lookup()
		self._build_advance_taxes_lookup()
		self._build_pe_taxes_lookup()
		self._build_invoice_info_lookup()

	def _build_invoice_taxes_lookup(self):
		for row in self._invoices_with_tds:
			inv_name = row.name
			if inv_name not in self.invoice_taxes:
				self.invoice_taxes[inv_name] = {"info": row, "tax_rows": [], "tds_total": 0}

			self.invoice_taxes[inv_name]["tax_rows"].append(row)
			self.invoice_taxes[inv_name]["tds_total"] += abs(flt(row.base_tax_amount_after_discount_amount))

	def _build_withheld_vouchers_lookup(self):
		for row in self._all_withheld_vouchers:
			self.withheld_by_invoice[row.parent].append(row)
			self.invoices_with_twv.add(row.parent)

			# Track cross-invoice TDS payment
			if row.voucher_name != row.parent and row.parent in self.invoice_taxes:
				if row.voucher_name not in self.tds_paid_by_other:
					self.tds_paid_by_other[row.voucher_name] = row.parent

			if row.voucher_type != "Purchase Invoice":
				continue

			self._pi_names_for_dates.add(row.voucher_name)

	def _build_advance_taxes_lookup(self):
		for row in self._all_advance_taxes:
			self.advance_by_invoice[row.parent].append(row)
			pe_name = row.reference_name
			self.pe_allocated[pe_name] += flt(row.allocated_amount)
			self._pe_names_for_dates.add(pe_name)
			self.invoices_with_advance_tax.add(row.parent)

	def _build_pe_taxes_lookup(self):
		for row in self._pe_tds_entries:
			pe_name = row.payment_entry
			self._pe_names_for_dates.add(pe_name)

			if pe_name not in self.pe_taxes:
				self.pe_taxes[pe_name] = {"info": row, "tax_rows": [], "tds_total": 0}

			self.pe_taxes[pe_name]["tax_rows"].append(row)
			amount = abs(flt(row.base_tax_amount))

			if row.add_deduct_tax == "Deduct":
				self.pe_taxes[pe_name]["tds_total"] += amount
			else:
				self.pe_taxes[pe_name]["tds_total"] -= amount

	def _build_invoice_info_lookup(self):
		for row in self._invoices_with_tds:
			if row.name not in self.invoice_info:
				self.invoice_info[row.name] = row

		for row in self._all_withheld_vouchers:
			if row.parent not in self.invoice_info:
				self.invoice_info[row.parent] = row

		for row in self._all_advance_taxes:
			if row.parent not in self.invoice_info:
				self.invoice_info[row.parent] = row

	def _fetch_dates(self):
		pe = frappe.qb.DocType("Payment Entry")
		pi = frappe.qb.DocType("Purchase Invoice")

		if self._pe_names_for_dates:
			pe_date_rows = (
				frappe.qb.from_(pe)
				.select(pe.name, pe.posting_date)
				.where(pe.name.isin(list(self._pe_names_for_dates)))
				.run(as_dict=True)
			)
			self.pe_dates = {row.name: row.posting_date for row in pe_date_rows}

		if self._pi_names_for_dates:
			pi_date_rows = (
				frappe.qb.from_(pi)
				.select(pi.name, pi.posting_date)
				.where(pi.name.isin(list(self._pi_names_for_dates)))
				.run(as_dict=True)
			)
			self.pi_dates = {row.name: row.posting_date for row in pi_date_rows}

	# -------------------------------------------------------------------------
	# Invoice Processing
	# -------------------------------------------------------------------------

	def _process_invoices(self):
		all_invoice_names = (
			set(self.invoice_taxes.keys()) | self.invoices_with_twv | self.invoices_with_advance_tax
		)

		for invoice_name in all_invoice_names:
			self._process_invoice(invoice_name)

	def _process_invoice(self, invoice_name):
		info = self.invoice_info.get(invoice_name)
		if not info:
			return

		# Build context for this invoice
		ctx = self._build_invoice_context(invoice_name, info)
		entries = []

		# Process advance tax allocations (PE -> PI)
		entries.extend(self._process_advance_taxes(invoice_name, ctx))

		# Process TDS paid in current invoice
		if ctx["total_tds_in_invoice"]:
			entries.extend(self._process_invoice_tds(invoice_name, ctx))

		# Handle under-withheld (TWV exists but no TDS)
		elif invoice_name in self.invoices_with_twv:
			entry = self._process_underwithheld(invoice_name, ctx)
			if entry:
				entries.append(entry)

		if entries:
			self._add_entries("Purchase Invoice", invoice_name, entries)

	def _build_invoice_context(self, invoice_name, info):
		# Get category
		category = info.tax_withholding_category
		if not category and invoice_name in self.invoice_taxes:
			for tax_row in self.invoice_taxes[invoice_name]["tax_rows"]:
				account_key = (info.company, tax_row.account_head)
				category = self.tds_accounts["account_map"].get(account_key)
				if category:
					break

		# Get party info
		party_type = "Supplier"
		party = info.supplier
		tax_id = get_party_tax_id(party_type, party, self.column_cache, self.party_tax_id_cache)
		tax_rate, tax_on_excess = get_tax_rate_for_date(self.tax_rate_map, category, info.posting_date)

		# Current invoice's taxable amount
		current_taxable = abs(info.base_tax_withholding_net_total or info.base_net_total)

		# Get TDS total
		has_tds = invoice_name in self.invoice_taxes
		total_tds_in_invoice = abs(self.invoice_taxes[invoice_name]["tds_total"]) if has_tds else 0

		# Get related data
		advance_taxes = self.advance_by_invoice.get(invoice_name, [])
		withheld_vouchers = self.withheld_by_invoice.get(invoice_name, [])

		# Calculate past taxable from withheld vouchers
		past_taxable_total = sum(
			flt(v.taxable_amount) for v in withheld_vouchers if v.voucher_name != invoice_name
		)

		return {
			"info": info,
			"category": category,
			"party_type": party_type,
			"party": party,
			"tax_id": tax_id,
			"tax_rate": tax_rate,
			"tax_on_excess": tax_on_excess,
			"current_taxable": current_taxable,
			"past_taxable_total": past_taxable_total,
			"total_tds_in_invoice": total_tds_in_invoice,
			"advance_taxes": advance_taxes,
			"withheld_vouchers": withheld_vouchers,
		}

	def _process_advance_taxes(self, invoice_name, ctx):
		entries = []
		info = ctx["info"]

		for adv_tax in ctx["advance_taxes"]:
			pe_name = adv_tax.reference_name
			pe_date = self.pe_dates.get(pe_name)
			allocated_amount = flt(adv_tax.allocated_amount)

			if allocated_amount <= 0:
				continue

			if ctx["tax_rate"]:
				taxable_for_allocation = flt(allocated_amount * 100 / ctx["tax_rate"], 2)
			else:
				taxable_for_allocation = ctx["current_taxable"]

			ctx["current_taxable"] += taxable_for_allocation

			# Entry in Purchase Invoice
			entry_in_pi = self._create_entry(
				ctx,
				taxable_amount=taxable_for_allocation,
				withholding_amount=allocated_amount,
				taxable_doctype="Purchase Invoice",
				taxable_name=invoice_name,
				taxable_date=info.posting_date,
				withholding_doctype="Payment Entry",
				withholding_name=pe_name,
				withholding_date=pe_date,
			)
			entries.append(entry_in_pi)

			# Duplicate entry in Payment Entry
			entry_in_pe = entry_in_pi.copy()
			entry_in_pe["is_duplicate"] = True
			self._add_entries("Payment Entry", pe_name, [entry_in_pe])

		return entries

	def _process_invoice_tds(self, invoice_name, ctx):
		entries = []
		info = ctx["info"]
		tax_rate = ctx["tax_rate"]

		tds_for_past = 0
		tds_for_current_and_past = abs(ctx["total_tds_in_invoice"])

		# Calculate TDS split between current and past invoices
		if not ctx["tax_on_excess"] and ctx["past_taxable_total"] > 0 and tax_rate:
			tds_for_past = flt(ctx["past_taxable_total"] * tax_rate / 100, 2)
			tds_for_current = max(0, tds_for_current_and_past - tds_for_past)
		else:
			tds_for_current = tds_for_current_and_past

		# Entry for current invoice
		if tds_for_current:
			if tax_rate:
				calc_taxable = flt(tds_for_current * 100 / tax_rate, 2)
			else:
				calc_taxable = ctx["current_taxable"]

			# Handle threshold exemption for tax_on_excess categories
			if ctx["tax_on_excess"] and calc_taxable < ctx["current_taxable"]:
				taxable_exemption_amount = flt(ctx["current_taxable"] - calc_taxable, 2)

				# Create threshold exemption entry (no TDS on threshold amount)
				threshold_entry = self._create_entry(
					ctx,
					taxable_amount=taxable_exemption_amount,
					withholding_amount=0,
					taxable_doctype="Purchase Invoice",
					taxable_name=invoice_name,
					taxable_date=info.posting_date,
					withholding_doctype="Purchase Invoice",
					withholding_name=invoice_name,
					withholding_date=info.posting_date,
					under_withheld_reason="Threshold Exemption",
				)
				entries.append(threshold_entry)

			main_entry = self._create_entry(
				ctx,
				taxable_amount=calc_taxable,
				withholding_amount=tds_for_current,
				taxable_doctype="Purchase Invoice",
				taxable_name=invoice_name,
				taxable_date=info.posting_date,
				withholding_doctype="Purchase Invoice",
				withholding_name=invoice_name,
				withholding_date=info.posting_date,
			)
			entries.append(main_entry)

		# Process withheld vouchers (TDS for past invoices paid here)
		if tds_for_past:
			entries.extend(self._process_withheld_vouchers(invoice_name, ctx))

		return entries

	def _process_withheld_vouchers(self, invoice_name, ctx):
		entries = []
		info = ctx["info"]
		tax_rate = ctx["tax_rate"]

		for voucher in ctx["withheld_vouchers"]:
			if voucher.voucher_name == invoice_name:
				continue

			voucher_date = self.pi_dates.get(voucher.voucher_name) or info.posting_date
			voucher_taxable = flt(voucher.taxable_amount)
			voucher_tds = flt(voucher_taxable * tax_rate / 100, 2) if tax_rate else 0

			# Entry in current invoice
			entry_in_current = self._create_entry(
				ctx,
				taxable_amount=voucher_taxable,
				withholding_amount=voucher_tds,
				taxable_doctype=voucher.voucher_type,
				taxable_name=voucher.voucher_name,
				taxable_date=voucher_date,
				withholding_doctype="Purchase Invoice",
				withholding_name=invoice_name,
				withholding_date=info.posting_date,
			)
			entries.append(entry_in_current)

			# Duplicate entry in past invoice
			entry_in_past = entry_in_current.copy()
			entry_in_past["is_duplicate"] = True
			self._add_entries(voucher.voucher_type, voucher.voucher_name, [entry_in_past])

		return entries

	def _process_underwithheld(self, invoice_name, ctx):
		# Skip if TDS was paid by another invoice
		if invoice_name in self.tds_paid_by_other:
			return None

		info = ctx["info"]
		taxable = info.base_tax_withholding_net_total or info.base_net_total

		tax_on_excess = ctx["tax_on_excess"]
		under_withheld_reason = "Threshold Exemption" if tax_on_excess else ""

		return self._create_entry(
			ctx,
			taxable_amount=taxable,
			withholding_amount=0,
			taxable_doctype="Purchase Invoice",
			taxable_name=invoice_name,
			taxable_date=info.posting_date,
			withholding_doctype="",
			withholding_name="",
			withholding_date=None,
			under_withheld_reason=under_withheld_reason,
		)

	# -------------------------------------------------------------------------
	# Payment Entry Over-Withheld Processing
	# -------------------------------------------------------------------------

	def _process_pe_overwithheld(self):
		for pe_name, data in self.pe_taxes.items():
			info = data["info"]
			total_tds = data["tds_total"]

			if not total_tds:
				continue

			# Calculate unallocated TDS
			total_allocated = self.pe_allocated.get(pe_name, 0)
			unallocated_tds = total_tds - total_allocated

			if unallocated_tds <= 0:
				continue

			# Get category
			category = info.tax_withholding_category

			party_type = info.party_type
			party = info.party
			tax_id = get_party_tax_id(party_type, party, self.column_cache, self.party_tax_id_cache)
			tax_rate, _ = get_tax_rate_for_date(self.tax_rate_map, category, info.posting_date)

			if tax_rate:
				unallocated_taxable = flt(unallocated_tds * 100 / tax_rate, 2)
			else:
				unallocated_taxable = info.paid_amount

			# Get currency and conversion rate based on payment type
			if info.payment_type == "Receive":
				currency = info.paid_from_account_currency
				conversion_rate = info.source_exchange_rate or 1
			else:
				currency = info.paid_to_account_currency
				conversion_rate = info.target_exchange_rate or 1

			entry = {
				"company": info.company,
				"party_type": party_type,
				"party": party,
				"tax_id": tax_id,
				"tax_withholding_category": category,
				"taxable_amount": unallocated_taxable,
				"tax_rate": tax_rate,
				"withholding_amount": unallocated_tds,
				"taxable_doctype": "",
				"taxable_name": "",
				"taxable_date": None,
				"withholding_doctype": "Payment Entry",
				"withholding_name": pe_name,
				"withholding_date": info.posting_date,
				"currency": currency,
				"conversion_rate": conversion_rate,
			}

			self._add_entries("Payment Entry", pe_name, [entry])

	# -------------------------------------------------------------------------
	# Helper Methods
	# -------------------------------------------------------------------------

	def _create_entry(self, ctx, **kwargs):
		is_return = ctx["info"].is_return

		if is_return:
			if "taxable_amount" in kwargs:
				kwargs["taxable_amount"] = -kwargs["taxable_amount"]
			if "withholding_amount" in kwargs:
				kwargs["withholding_amount"] = -kwargs["withholding_amount"]

		return {
			"company": ctx["info"].company,
			"party_type": ctx["party_type"],
			"party": ctx["party"],
			"tax_id": ctx["tax_id"],
			"tax_withholding_category": ctx["category"],
			"tax_rate": ctx["tax_rate"],
			"currency": ctx["info"].currency,
			"conversion_rate": ctx["info"].conversion_rate or 1,
			**kwargs,
		}

	def _add_entries(self, parent_doctype, parent_name, entries):
		key = (parent_doctype, parent_name)
		if key not in self.all_entries:
			self.all_entries[key] = []

		self.all_entries[key].extend(entries)


# =============================================================================
# SALES INVOICE MIGRATION
# =============================================================================


def migrate_sales_invoices(tds_accounts, tax_rate_map, column_cache, party_tax_id_cache):
	"""
	Migrate Sales Invoice TCS data.

	Sales Invoice TCS is simpler - only tax on excess amount for current invoice.
	No tax_withheld_vouchers or advance_tax tables.
	Tax is identified from GL Entry on TCS accounts.
	"""
	gle = frappe.qb.DocType("GL Entry")
	si = frappe.qb.DocType("Sales Invoice")
	cust = frappe.qb.DocType("Customer")

	# Build conditions for TCS accounts
	all_tcs_accounts = set()
	for _company, accounts in tds_accounts["accounts_by_company"].items():
		all_tcs_accounts.update(accounts)

	if not all_tcs_accounts:
		return

	# Get Sales Invoices with TCS amounts aggregated
	# Use conditional sum to aggregate TCS amounts only from TCS accounts
	tcs_accounts_list = list(all_tcs_accounts)

	tcs_entries = (
		frappe.qb.from_(si)
		.left_join(gle)
		.on((gle.voucher_no == si.name) & (gle.voucher_type == "Sales Invoice") & (gle.is_cancelled == 0))
		.join(cust)
		.on(si.customer == cust.name)
		.select(
			si.name.as_("invoice_name"),
			si.posting_date,
			si.customer,
			si.company,
			si.base_grand_total,
			si.is_return,
			si.currency,
			si.conversion_rate,
			cust.tax_withholding_category,
			Sum(Case().when(gle.account.isin(tcs_accounts_list), gle.credit - gle.debit).else_(0)).as_(
				"total_tcs"
			),
			Max(Case().when(gle.account.isin(tcs_accounts_list), gle.account).else_(None)).as_("account"),
		)
		.where(si.docstatus == 1)
		.groupby(si.name)
		.run(as_dict=True)
	)

	all_entries = {}
	category_wise_invoices = defaultdict(list)

	for row in tcs_entries:
		total_tcs = row.total_tcs
		net_grand_total = abs(row.base_grand_total - total_tcs)

		# Get category
		category = row.tax_withholding_category
		if not category:
			account_key = (row.company, row.account)
			category = tds_accounts["account_map"].get(account_key)

		# Party info
		party_type = "Customer"
		party = row.customer
		tax_id = get_party_tax_id(party_type, party, column_cache, party_tax_id_cache)

		tax_rate, _ = get_tax_rate_for_date(tax_rate_map, category, row.posting_date)

		if not tax_rate:
			continue

		# Back-calculate taxable amount
		calculated_taxable = 0
		if tax_rate and total_tcs:
			calculated_taxable = flt(total_tcs * 100 / tax_rate, 2)

		# For returns, amounts are negative
		if row.is_return:
			total_tcs = -abs(total_tcs)
			calculated_taxable = -abs(calculated_taxable)

		entries = []

		# Handle threshold exemption for categories
		# NOTE: Default tax_on_excess is True for Sales Invoice
		if abs(calculated_taxable) < net_grand_total:
			taxable_exemption_amount = flt(net_grand_total - abs(calculated_taxable), 2)

			if row.is_return:
				taxable_exemption_amount = -abs(taxable_exemption_amount)

			threshold_entry = {
				"company": row.company,
				"party_type": party_type,
				"party": party,
				"tax_id": tax_id,
				"tax_withholding_category": category,
				"taxable_amount": taxable_exemption_amount,
				"tax_rate": tax_rate,
				"withholding_amount": 0,
				"taxable_doctype": "Sales Invoice",
				"taxable_name": row.invoice_name,
				"taxable_date": row.posting_date,
				"withholding_doctype": "Sales Invoice",
				"withholding_name": row.invoice_name,
				"withholding_date": row.posting_date,
				"under_withheld_reason": "Threshold Exemption",
				"currency": row.currency,
				"conversion_rate": row.conversion_rate or 1,
			}
			entries.append(threshold_entry)

		entry = {
			"company": row.company,
			"party_type": party_type,
			"party": party,
			"tax_id": tax_id,
			"tax_withholding_category": category,
			"taxable_amount": calculated_taxable,
			"tax_rate": tax_rate,
			"withholding_amount": total_tcs,
			"taxable_doctype": "Sales Invoice",
			"taxable_name": row.invoice_name,
			"taxable_date": row.posting_date,
			"withholding_doctype": "Sales Invoice",
			"withholding_name": row.invoice_name,
			"withholding_date": row.posting_date,
			"currency": row.currency,
			"conversion_rate": row.conversion_rate or 1,
		}
		entries.append(entry)

		all_entries[("Sales Invoice", row.invoice_name)] = entries
		category_wise_invoices[category].append(row.invoice_name)

	bulk_insert_entries(all_entries)

	# Update Sales Invoice and Sales Invoice Item
	for category, invoices in category_wise_invoices.items():
		frappe.db.set_value("Sales Invoice", {"name": ("in", invoices)}, {"apply_tds": 1})
		frappe.db.set_value(
			"Sales Invoice Item",
			{"parent": ("in", invoices), "parenttype": "Sales Invoice"},
			{"tax_withholding_category": category, "apply_tds": 1},
		)


# =============================================================================
# JOURNAL ENTRY MIGRATION
# =============================================================================


def migrate_journal_entries(tds_accounts, tax_rate_map, column_cache, party_tax_id_cache):
	"""
	Migrate Journal Entry TDS data.

	For Journal Entry, we rely on GL Entry to identify TDS transactions.
	Party info is obtained from JE Account rows that are NOT TDS accounts.
	"""
	gle = frappe.qb.DocType("GL Entry")
	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")

	# Build conditions for TDS accounts
	all_tds_accounts = set()
	for _company, accounts in tds_accounts["accounts_by_company"].items():
		all_tds_accounts.update(accounts)

	if not all_tds_accounts:
		return

	# Get Journal Entries with TDS entries in GL
	tds_gl_entries = (
		frappe.qb.from_(gle)
		.join(je)
		.on(gle.voucher_no == je.name)
		.select(
			gle.voucher_no.as_("journal_entry"),
			gle.account,
			gle.credit,
			gle.debit,
			gle.posting_date,
			je.company,
			je.tax_withholding_category,
			je.voucher_type,
			je.total_debit,
		)
		.where(gle.voucher_type == "Journal Entry")
		.where(gle.is_cancelled == 0)
		.where(je.docstatus == 1)
		.where(gle.account.isin(list(all_tds_accounts)))
		.run(as_dict=True)
	)

	# Get all JE parties in bulk - only from non-TDS account rows
	je_names = list({row.journal_entry for row in tds_gl_entries})
	je_parties = {}
	if je_names:
		# Get party from JE Account rows that are NOT TDS accounts
		jea_party_rows = (
			frappe.qb.from_(jea)
			.select(
				jea.parent,
				jea.party_type,
				jea.party,
				jea.account,
				jea.account_currency,
				jea.exchange_rate,
			)
			.where(jea.parent.isin(je_names))
			.where(jea.party_type.isnotnull())
			.where(jea.party_type != "")
			.where(jea.party.isnotnull())
			.where(jea.party != "")
			.where(jea.account.notin(list(all_tds_accounts)))  # Exclude TDS account rows
			.run(as_dict=True)
		)
		for row in jea_party_rows:
			if row.parent not in je_parties:
				je_parties[row.parent] = (row.party_type, row.party, row.account_currency, row.exchange_rate)

	# Group by journal entry
	je_taxes = {}
	for row in tds_gl_entries:
		if row.journal_entry not in je_taxes:
			je_taxes[row.journal_entry] = {"info": row, "gl_rows": []}
		je_taxes[row.journal_entry]["gl_rows"].append(row)

	all_entries = {}
	category_wise_jes = defaultdict(set)

	for je_name, data in je_taxes.items():
		info = data["info"]

		# Assume TCS not allowed in Journal Entry
		# Calculate total TDS (credit - debit)
		total_tds = sum(flt(row.credit) - flt(row.debit) for row in data["gl_rows"])

		if total_tds <= 0:
			# Ignore TDS payment entries
			continue

		# Get category
		category = info.tax_withholding_category
		if not category:
			for gl_row in data["gl_rows"]:
				account_key = (info.company, gl_row.account)
				category = tds_accounts["account_map"].get(account_key)
				if category:
					break

		# Get party from JE accounts (non-TDS rows)
		party_type = None
		party = None
		account_currency = ""
		exchange_rate = 1

		if je_name in je_parties:
			party_type, party, account_currency, exchange_rate = je_parties[je_name]

		tax_id = get_party_tax_id(party_type, party, column_cache, party_tax_id_cache) if party else None
		tax_rate, tax_on_excess = get_tax_rate_for_date(tax_rate_map, category, info.posting_date)

		# Back-calculate taxable amount
		calculated_taxable = 0
		if tax_rate and total_tds:
			calculated_taxable = min(flt(total_tds * 100 / tax_rate, 2), info.total_debit)

		entries = []

		# Handle threshold exemption for tax_on_excess categories
		if tax_on_excess and calculated_taxable < info.total_debit:
			taxable_exemption_amount = flt(info.total_debit - abs(calculated_taxable), 2)
			threshold_entry = {
				"company": info.company,
				"party_type": party_type,
				"party": party,
				"tax_id": tax_id,
				"tax_withholding_category": category,
				"taxable_amount": taxable_exemption_amount,
				"tax_rate": tax_rate,
				"withholding_amount": 0,
				"taxable_doctype": "Journal Entry",
				"taxable_name": je_name,
				"taxable_date": info.posting_date,
				"withholding_doctype": "Journal Entry",
				"withholding_name": je_name,
				"withholding_date": info.posting_date,
				"under_withheld_reason": "Threshold Exemption",
				"currency": account_currency or "",
				"conversion_rate": flt(exchange_rate, 9) or 1,
			}
			entries.append(threshold_entry)

		entry = {
			"company": info.company,
			"party_type": party_type,
			"party": party,
			"tax_id": tax_id,
			"tax_withholding_category": category,
			"taxable_amount": calculated_taxable,
			"tax_rate": tax_rate,
			"withholding_amount": total_tds,
			"taxable_doctype": "Journal Entry",
			"taxable_name": je_name,
			"taxable_date": info.posting_date,
			"withholding_doctype": "Journal Entry",
			"withholding_name": je_name,
			"withholding_date": info.posting_date,
			"currency": account_currency or "",
			"conversion_rate": flt(exchange_rate, 9) or 1,
		}
		entries.append(entry)
		all_entries[("Journal Entry", je_name)] = entries

		category_wise_jes[category].add(je_name)

	bulk_insert_entries(all_entries)

	for category, je_names in category_wise_jes.items():
		frappe.db.set_value(
			"Journal Entry",
			{"name": ("in", list(je_names))},
			{"apply_tds": 1, "tax_withholding_category": category},
		)


# =============================================================================
# ITEM LEVEL CATEGORY COPY
# =============================================================================


def copy_category_to_items_for_purchase(column_cache):
	parent_doctype = "Purchase Invoice"
	item_doctype = "Purchase Invoice Item"

	parent_cols = column_cache.get(parent_doctype, {})
	item_cols = column_cache.get(item_doctype, {})

	if not parent_cols.get("tax_withholding_category"):
		return

	if not item_cols.get("tax_withholding_category"):
		return

	parent = frappe.qb.DocType(parent_doctype)
	item = frappe.qb.DocType(item_doctype, alias="item")

	(
		frappe.qb.update(item)
		.join(parent)
		.on(item.parent == parent.name)
		.set(item.tax_withholding_category, parent.tax_withholding_category)
		.where(parent.tax_withholding_category.isnotnull())
		.where(parent.tax_withholding_category != "")
		.where(item.apply_tds == 1)
		.where(IfNull(item.tax_withholding_category, "") == "")
		.run()
	)


def copy_category_to_items_for_sales(column_cache):
	parent_doctype = "Sales Invoice"
	item_doctype = "Sales Invoice Item"

	item_cols = column_cache.get(item_doctype, {})

	if not item_cols.get("tax_withholding_category"):
		return

	parent = frappe.qb.DocType(parent_doctype)
	item = frappe.qb.DocType(item_doctype, alias="item")
	customer = frappe.qb.DocType("Customer", alias="customer")

	(
		frappe.qb.update(item)
		.join(parent)
		.on(item.parent == parent.name)
		.join(customer)
		.on(parent.customer == customer.name)
		.set(item.tax_withholding_category, customer.tax_withholding_category)
		.where(customer.tax_withholding_category.isnotnull())
		.where(customer.tax_withholding_category != "")
		.where(IfNull(item.tax_withholding_category, "") == "")
		.run()
	)
