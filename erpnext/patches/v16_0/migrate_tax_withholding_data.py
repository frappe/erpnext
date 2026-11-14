# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import defaultdict
from uuid import uuid7

import frappe
from frappe.query_builder.functions import Count, IfNull, Max, Sum
from frappe.utils import create_batch, flt, now
from pypika.terms import Bracket

# Names per IN list, kept below max_allowed_packet, and invoices per supplier group, so memory stays bounded
BATCH_SIZE = 50000


def execute():
	# Entries are rebuilt from the v15 data, so once that is gone nothing can be rebuilt or cleaned up
	if not (
		frappe.db.table_exists("Tax Withheld Vouchers", cached=False)
		and frappe.db.table_exists("Advance Tax", cached=False)
		and frappe.db.has_column("Purchase Invoice", "tax_withholding_category")
		and frappe.db.has_column("Purchase Invoice", "base_tax_withholding_net_total")
	):
		return

	tds_accounts = get_tds_accounts()
	if not tds_accounts:
		return

	tax_rate_map = get_tax_rate_map()
	column_cache = get_column_cache()
	party_tax_id_cache, party_categories = get_party_details(column_cache)
	skip_docs = get_docs_with_entries()

	# Clean up existing migration entries, except on documents the new flow has already used
	used_docs = defaultdict(list)
	for doctype, name in skip_docs:
		used_docs[doctype].append(name)

	twe = frappe.qb.DocType("Tax Withholding Entry")
	delete_query = frappe.qb.from_(twe).delete().where(twe.created_by_migration == 1)

	# One column per test, so the list is searched sorted; a (parenttype, parent) pair checks every item
	for doctype, names in used_docs.items():
		delete_query = delete_query.where((twe.parenttype != doctype) | twe.parent.notin(names))

	delete_query.run()

	# Purchase Invoice migration also handles Payment Entry TDS (allocated and unallocated)
	paid_journals = set()
	for suppliers in get_party_groups("Supplier", column_cache, party_tax_id_cache):
		purchase_migrator = PurchaseInvoiceMigrator(
			tds_accounts,
			tax_rate_map,
			party_tax_id_cache,
			party_categories,
			skip_docs,
			suppliers,
		)
		purchase_migrator.migrate()
		paid_journals.update(
			name for doctype, name in purchase_migrator.tds_paid_by_other if doctype == "Journal Entry"
		)

	# v15 advance rows have no withholding flag and an Add row is a reversal; skipped payments need it too
	pe = frappe.qb.DocType("Payment Entry")
	atc = frappe.qb.DocType("Advance Taxes and Charges")
	(
		frappe.qb.update(atc)
		.set(atc.is_tax_withholding_account, 1)
		.where(atc.parenttype == "Payment Entry")
		.where(atc.add_deduct_tax == "Deduct")
		.where(atc.account_head.isin(tds_accounts["all_accounts"]))
		.where(
			atc.parent.isin(
				frappe.qb.from_(pe)
				.select(pe.name)
				.where(pe.docstatus == 1)
				.where(pe.party_type == "Supplier")
				.where(pe.apply_tds == 1)
			)
		)
		.run()
	)

	for customers in get_party_groups("Customer", column_cache, party_tax_id_cache):
		migrate_sales_invoices(tds_accounts, tax_rate_map, party_tax_id_cache, skip_docs, customers)

	migrate_journal_entries(
		tds_accounts,
		tax_rate_map,
		party_tax_id_cache,
		skip_docs,
		paid_journals,
		party_categories,
	)

	copy_category_to_items_for_purchase(column_cache)
	copy_category_to_items_for_sales(column_cache)


def get_party_groups(party_type, column_cache, party_tax_id_cache):
	invoice = frappe.qb.DocType("Purchase Invoice" if party_type == "Supplier" else "Sales Invoice")
	party_field = invoice.supplier if party_type == "Supplier" else invoice.customer
	invoice_counts = dict(
		frappe.qb.from_(invoice)
		.select(party_field, Count("*"))
		.where(invoice.docstatus == 1)
		.groupby(party_field)
		.run()
	)

	# Suppliers without invoices still need a group for the TDS on their payments
	if party_type == "Supplier":
		for key_type, party in party_tax_id_cache:
			if key_type == party_type:
				invoice_counts.setdefault(party, 0)

	# v15 counted all parties with the same PAN together, and nothing across PANs
	parties_by_pan = defaultdict(list)
	for party in invoice_counts:
		pan = column_cache[party_type]["pan"] and party_tax_id_cache.get((party_type, party))
		parties_by_pan[pan or party].append(party)

	group, group_invoices = [], 0
	for parties in parties_by_pan.values():
		invoices = sum(invoice_counts[party] for party in parties)
		if group and (group_invoices + invoices > BATCH_SIZE or len(group) + len(parties) > BATCH_SIZE):
			yield group
			group, group_invoices = [], 0

		group.extend(parties)
		group_invoices += invoices

	if group:
		yield group


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
		"Purchase Invoice Item": {
			"tax_withholding_category": frappe.db.has_column(
				"Purchase Invoice Item", "tax_withholding_category"
			),
		},
		"Sales Invoice Item": {
			"tax_withholding_category": frappe.db.has_column(
				"Sales Invoice Item", "tax_withholding_category"
			),
		},
	}


def get_party_details(column_cache):
	tax_ids, categories = {}, {}

	# Suppliers and customers are read up front; other party types have no tax id or category to use
	for party_type in ("Supplier", "Customer"):
		tax_id_field = next((f for f in ("pan", "tax_id") if column_cache[party_type][f]), None)
		fields = ["name", "tax_withholding_category", *([tax_id_field] if tax_id_field else [])]
		for row in frappe.get_all(party_type, fields=fields):
			tax_ids[(party_type, row.name)] = row.get(tax_id_field) if tax_id_field else None
			categories[(party_type, row.name)] = row.tax_withholding_category

	return tax_ids, categories


def get_tds_accounts():
	twa = frappe.qb.DocType("Tax Withholding Account")

	result = (
		frappe.qb.from_(twa).select(twa.account, twa.company, twa.parent.as_("category")).run(as_dict=True)
	)

	if not result:
		return None

	account_map = {}
	for row in result:
		key = (row.company, row.account)
		if key in account_map:
			# An account shared by several categories identifies none
			account_map[key] = None
		else:
			account_map[key] = row.category

	return {"account_map": account_map, "all_accounts": list({row.account for row in result})}


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


def get_docs_with_entries():
	# The new flow adjusts the entries of the documents it references, so neither side can be rebuilt
	twe = frappe.qb.DocType("Tax Withholding Entry")

	rows = (
		frappe.qb.from_(twe)
		.select(
			twe.parenttype,
			twe.parent,
			twe.taxable_doctype,
			twe.taxable_name,
			twe.withholding_doctype,
			twe.withholding_name,
		)
		.where(twe.created_by_migration == 0)
		.where(twe.docstatus == 1)
		.distinct()
		.run(as_dict=True)
	)

	docs = set()
	for row in rows:
		for doctype, name in (
			(row.parenttype, row.parent),
			(row.taxable_doctype, row.taxable_name),
			(row.withholding_doctype, row.withholding_name),
		):
			if doctype and name:
				docs.add((doctype, name))

	# Entries the user overrode on the new flow are theirs, even where they removed all of them
	for doctype in ("Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry"):
		docs.update(
			(doctype, name)
			for name in frappe.get_all(
				doctype, filters={"override_tax_withholding_entries": 1, "docstatus": 1}, pluck="name"
			)
		)

	return docs


def get_tax_rate_for_date(tax_rate_map, category, posting_date):
	if not category or category not in tax_rate_map or not posting_date:
		return 0, False

	for rate in tax_rate_map[category]:
		if rate.from_date and rate.to_date and rate.from_date <= posting_date <= rate.to_date:
			return (rate.tax_withholding_rate, bool(rate.tax_on_excess_amount))

	return 0, False


def determine_status(taxable_name, withholding_name, under_withheld_reason, is_duplicate=False):
	if is_duplicate:
		return "Duplicate"

	# A reason for not deducting settles the entry
	if under_withheld_reason:
		return "Settled"

	if taxable_name and withholding_name:
		return "Settled"

	if taxable_name and not withholding_name:
		return "Under Withheld"

	if withholding_name and not taxable_name:
		return "Over Withheld"

	return ""


def bulk_insert_entries(all_entries):
	if not all_entries:
		return

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
		"lower_deduction_certificate",
		"currency",
		"conversion_rate",
		"created_by_migration",
	]

	current_time = now()
	current_user = frappe.session.user

	values = []
	for (parent_doctype, parent_name), entries in all_entries.items():
		for idx, entry in enumerate(entries, start=1):
			status = determine_status(
				entry.get("taxable_name"),
				entry.get("withholding_name"),
				entry.get("under_withheld_reason"),
				entry.get("is_duplicate", False),
			)

			values.append(
				(
					# Never one of the existing 10 character hash names, so no check against the table
					str(uuid7()),
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
					entry.get("lower_deduction_certificate", ""),
					entry.get("currency", ""),
					flt(entry.get("conversion_rate"), 9) or 1,
					1,  # created_by_migration
				)
			)

	if values:
		frappe.db.bulk_insert("Tax Withholding Entry", fields, values, ignore_duplicates=True)


class PurchaseInvoiceMigrator:
	def __init__(
		self,
		tds_accounts,
		tax_rate_map,
		party_tax_id_cache,
		party_categories,
		skip_docs,
		suppliers,
	):
		self.tds_accounts = tds_accounts
		self.tax_rate_map = tax_rate_map
		self.party_tax_id_cache = party_tax_id_cache
		self.party_categories = party_categories
		self.skip_docs = skip_docs
		self.suppliers = suppliers

		self.all_tds_accounts = tds_accounts["all_accounts"]

		self._invoices_with_tds = []
		self._all_withheld_vouchers = []
		self._all_advance_taxes = []
		self._pe_tds_entries = []
		self._threshold_invoices = []

		self.invoice_taxes = {}  # {invoice_name: {"info": row, "tax_rows": [], "tds_total": float}}
		self.withheld_by_invoice = defaultdict(list)  # {parent_invoice: [vouchers]}
		self.advance_by_invoice = defaultdict(list)  # {parent_invoice: [advance_taxes]}
		self.pe_allocated = defaultdict(float)  # {pe_name: total_allocated}
		self.pe_taxes = {}  # {pe_name: {"info": row, "tax_rows": [], "tds_total": float}}
		self.invoice_info = {}  # {invoice_name: row}
		self.nil_certificates = defaultdict(list)  # {(supplier, company, category): [certificates]}

		self.invoices_with_advance_tax = set()
		self.tds_paid_by_other = set()

		self.pe_dates = {}
		self.pi_dates = {}
		self._pi_names_for_dates = set()
		self._pe_names_for_dates = set()

		self.all_entries = {}  # {(doctype, name): [entries]}

	def migrate(self):
		self._fetch_data()
		self._build_lookups()
		self._fetch_dates()
		self._process_invoices()
		self._process_pe_overwithheld()
		# Skipped documents are still processed, as they may hold the entries of other documents
		bulk_insert_entries(
			{key: rows for key, rows in self.all_entries.items() if key not in self.skip_docs}
		)

	def _fetch_data(self):
		pi = frappe.qb.DocType("Purchase Invoice")
		ptc = frappe.qb.DocType("Purchase Taxes and Charges")
		twv = frappe.qb.DocType("Tax Withheld Vouchers")
		at = frappe.qb.DocType("Advance Tax")
		pe = frappe.qb.DocType("Payment Entry")
		atc = frappe.qb.DocType("Advance Taxes and Charges")

		# v15 ticked its TDS rows, so a row on an account since removed from the category still counts
		tds_row = ptc.account_head.isin(self.all_tds_accounts) | (
			(ptc.is_tax_withholding_account == 1) & (ptc.base_tax_amount_after_discount_amount != 0)
		)

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
				pi.apply_tds,
				pi.currency,
				pi.conversion_rate,
				ptc.account_head,
				ptc.add_deduct_tax,
				ptc.base_tax_amount_after_discount_amount,
			)
			.where(pi.docstatus == 1)
			.where(pi.supplier.isin(self.suppliers))
			.where(tds_row)
			.run(as_dict=True)
		)

		# Only for TDS invoices, to split it over the vouchers it paid for; v15 listed them until TDS started
		self._all_withheld_vouchers = (
			frappe.qb.from_(twv)
			.select(twv.parent, twv.voucher_type, twv.voucher_name, twv.taxable_amount)
			.where(twv.parenttype == "Purchase Invoice")
			.where(
				twv.parent.isin(
					frappe.qb.from_(ptc)
					.join(pi)
					.on(ptc.parent == pi.name)
					.select(ptc.parent)
					.where(pi.docstatus == 1)
					.where(pi.supplier.isin(self.suppliers))
					.where(tds_row)
				)
			)
			.run(as_dict=True)
		)

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
				pi.apply_tds,
				pi.currency,
				pi.conversion_rate,
			)
			.where(at.parenttype == "Purchase Invoice")
			.where(at.reference_type == "Payment Entry")
			.where(pi.docstatus == 1)
			.where(pi.supplier.isin(self.suppliers))
			.run(as_dict=True)
		)

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
			.where(pe.party_type == "Supplier")
			.where(pe.party.isin(self.suppliers))
			.where(pe.apply_tds == 1)
			.where(atc.account_head.isin(self.all_tds_accounts))
			.run(as_dict=True)
		)

		# Invoices v15 counted towards the threshold, with or without TDS of their own
		self._threshold_invoices = (
			frappe.qb.from_(pi)
			.select(
				pi.name,
				pi.supplier,
				pi.company,
				pi.posting_date,
				pi.base_net_total,
				pi.base_tax_withholding_net_total,
				pi.tax_withholding_category,
				pi.is_return,
				pi.apply_tds,
				pi.currency,
				pi.conversion_rate,
			)
			.where(pi.docstatus == 1)
			.where(pi.supplier.isin(self.suppliers))
			.where(pi.is_opening == "No")
			.where(pi.apply_tds == 1)
			.where(IfNull(pi.tax_withholding_category, "") != "")
			.run(as_dict=True)
		)

		ldc = frappe.qb.DocType("Lower Deduction Certificate")
		for row in (
			frappe.qb.from_(ldc)
			.select(
				ldc.name,
				ldc.supplier,
				ldc.pan_no,
				ldc.company,
				ldc.tax_withholding_category,
				ldc.valid_from,
				ldc.valid_upto,
				ldc.certificate_limit.as_("balance"),
			)
			.where(ldc.rate == 0)
			.run(as_dict=True)
		):
			# v15 applied a certificate to every supplier with its PAN
			for party in {row.pan_no, row.supplier} - {None, ""}:
				self.nil_certificates[(party, row.company, row.tax_withholding_category)].append(row)

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
			amount = flt(row.base_tax_amount_after_discount_amount)
			self.invoice_taxes[inv_name]["tds_total"] += amount if row.add_deduct_tax == "Deduct" else -amount

	def _build_withheld_vouchers_lookup(self):
		for row in self._all_withheld_vouchers:
			self.withheld_by_invoice[row.parent].append(row)

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

		for row in self._all_advance_taxes:
			if row.parent not in self.invoice_info:
				self.invoice_info[row.parent] = row

		for row in self._threshold_invoices:
			if row.name not in self.invoice_info:
				self.invoice_info[row.name] = row

	def _fetch_dates(self):
		pe = frappe.qb.DocType("Payment Entry")
		pi = frappe.qb.DocType("Purchase Invoice")

		for batch in create_batch(list(self._pe_names_for_dates), BATCH_SIZE):
			self.pe_dates.update(
				frappe.qb.from_(pe).select(pe.name, pe.posting_date).where(pe.name.isin(batch)).run()
			)

		for batch in create_batch(list(self._pi_names_for_dates), BATCH_SIZE):
			self.pi_dates.update(
				frappe.qb.from_(pi).select(pi.name, pi.posting_date).where(pi.name.isin(batch)).run()
			)

	def _process_invoices(self):
		all_invoice_names = (
			set(self.invoice_taxes.keys())
			| self.invoices_with_advance_tax
			| {row.name for row in self._threshold_invoices}
		)

		# TDS invoices first so the ones they paid for are known, then by date, as v15 used certificate limits
		for invoice_name in sorted(
			all_invoice_names,
			key=lambda name: (name not in self.invoice_taxes, self.invoice_info[name].posting_date, name),
		):
			self._process_invoice(invoice_name)

	def _process_invoice(self, invoice_name):
		info = self.invoice_info.get(invoice_name)
		if not info:
			return

		ctx = self._build_invoice_context(invoice_name, info)
		entries = []

		entries.extend(self._process_advance_taxes(invoice_name, ctx))

		if ctx["total_tds_in_invoice"]:
			entries.extend(self._process_invoice_tds(invoice_name, ctx))

		else:
			entries.extend(self._process_underwithheld(invoice_name, ctx))

		if entries:
			self._add_entries("Purchase Invoice", invoice_name, entries)

	def _build_invoice_context(self, invoice_name, info):
		category = info.tax_withholding_category
		if not category and invoice_name in self.invoice_taxes:
			for tax_row in self.invoice_taxes[invoice_name]["tax_rows"]:
				account_key = (info.company, tax_row.account_head)
				category = self.tds_accounts["account_map"].get(account_key)
				if category:
					break

		party_type = "Supplier"
		party = info.supplier

		# Like the v15 Tax Withholding Details report, fall back to the supplier's category
		category = category or self.party_categories.get((party_type, party))
		tax_id = self.party_tax_id_cache.get((party_type, party))
		tax_rate, tax_on_excess = get_tax_rate_for_date(self.tax_rate_map, category, info.posting_date)

		current_taxable = abs(info.base_tax_withholding_net_total or info.base_net_total)

		has_tds = invoice_name in self.invoice_taxes
		tds_total = self.invoice_taxes[invoice_name]["tds_total"] if has_tds else 0

		# Below zero on a bill that is not a return, the TDS rows gave TDS back
		total_tds_in_invoice = tds_total if tds_total < 0 and not info.is_return else abs(tds_total)

		advance_taxes = self.advance_by_invoice.get(invoice_name, [])
		withheld_vouchers = self.withheld_by_invoice.get(invoice_name, [])

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
				# The invoice amount already includes the part taxed through the advance
				ctx["current_taxable"] = max(0, ctx["current_taxable"] - taxable_for_allocation)
			else:
				taxable_for_allocation = ctx["current_taxable"]

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

			entry_in_pe = entry_in_pi.copy()
			entry_in_pe["is_duplicate"] = True
			self._add_entries("Payment Entry", pe_name, [entry_in_pe])

		return entries

	def _process_invoice_tds(self, invoice_name, ctx):
		entries = []
		info = ctx["info"]
		tax_rate = ctx["tax_rate"]

		# TDS given back is the bill's own, as in the ledger, with nothing to split or exempt
		if ctx["total_tds_in_invoice"] < 0:
			return [
				self._create_entry(
					ctx,
					taxable_amount=ctx["current_taxable"],
					withholding_amount=ctx["total_tds_in_invoice"],
					taxable_doctype="Purchase Invoice",
					taxable_name=invoice_name,
					taxable_date=info.posting_date,
					withholding_doctype="Purchase Invoice",
					withholding_name=invoice_name,
					withholding_date=info.posting_date,
				)
			]

		tds_for_past = 0
		tds_for_current_and_past = abs(ctx["total_tds_in_invoice"])

		if not ctx["tax_on_excess"] and ctx["past_taxable_total"] > 0 and tax_rate:
			tds_for_past = flt(ctx["past_taxable_total"] * tax_rate / 100, 2)

			# v15 listed vouchers until the threshold was crossed, so TDS below their share did not tax them
			if tds_for_past > tds_for_current_and_past + 1:
				tds_for_past = 0

		tds_for_current = max(0, tds_for_current_and_past - tds_for_past)

		if tds_for_current:
			if tax_rate:
				calc_taxable = flt(tds_for_current * 100 / tax_rate, 2)
			else:
				calc_taxable = ctx["current_taxable"]

			# v15 counted only invoices with apply_tds towards the threshold
			if ctx["tax_on_excess"] and info.apply_tds and calc_taxable < ctx["current_taxable"]:
				taxable_exemption_amount = flt(ctx["current_taxable"] - calc_taxable, 2)

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

		if tds_for_past:
			entries.extend(self._process_withheld_vouchers(invoice_name, ctx))

		return entries

	def _process_withheld_vouchers(self, invoice_name, ctx):
		entries = []
		info = ctx["info"]
		tax_rate = ctx["tax_rate"]

		for voucher in ctx["withheld_vouchers"]:
			# v15 listed nil rate certificate invoices with no taxable amount, so nothing was paid for them
			if voucher.voucher_name == invoice_name or not flt(voucher.taxable_amount):
				continue

			self.tds_paid_by_other.add((voucher.voucher_type, voucher.voucher_name))
			voucher_date = self.pi_dates.get(voucher.voucher_name) or info.posting_date
			voucher_taxable = flt(voucher.taxable_amount)
			voucher_tds = flt(voucher_taxable * tax_rate / 100, 2) if tax_rate else 0

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

			entry_in_past = entry_in_current.copy()
			entry_in_past["is_duplicate"] = True
			self._add_entries(voucher.voucher_type, voucher.voucher_name, [entry_in_past])

		return entries

	def _process_underwithheld(self, invoice_name, ctx):
		# Paid by another invoice, or the advance covered the whole invoice; v15 summed only the items with
		# Apply TDS, so a zero total means nothing on the bill counted towards the threshold
		if (
			("Purchase Invoice", invoice_name) in self.tds_paid_by_other
			or not ctx["current_taxable"]
			or not ctx["info"].apply_tds
			or not ctx["info"].base_tax_withholding_net_total
		):
			return []

		info = ctx["info"]
		entries = []
		taxable = ctx["current_taxable"]
		values = {
			"withholding_amount": 0,
			"taxable_doctype": "Purchase Invoice",
			"taxable_name": invoice_name,
			"taxable_date": info.posting_date,
			"withholding_doctype": "",
			"withholding_name": "",
			"withholding_date": None,
		}

		# v15 counted nil rate certificate invoices as zero; the new flow tracks its limit on these rows
		certificates = self.nil_certificates.get(
			(ctx["tax_id"], info.company, ctx["category"])
		) or self.nil_certificates.get((info.supplier, info.company, ctx["category"]), [])
		for ldc in certificates:
			if not (ldc.valid_from <= info.posting_date <= ldc.valid_upto):
				continue

			# A return gives back the limit its invoice used
			covered = taxable if info.is_return else min(taxable, ldc.balance)
			ldc.balance += covered if info.is_return else -covered
			if covered:
				entries.append(
					self._create_entry(
						ctx,
						taxable_amount=covered,
						tax_rate=0,
						under_withheld_reason="Lower Deduction Certificate",
						lower_deduction_certificate=ldc.name,
						**values,
					)
				)
				taxable -= covered
			break

		if taxable:
			entries.append(
				self._create_entry(
					ctx,
					taxable_amount=taxable,
					under_withheld_reason="Threshold Exemption" if ctx["tax_on_excess"] else "",
					**values,
				)
			)

		return entries

	def _process_pe_overwithheld(self):
		for pe_name, data in self.pe_taxes.items():
			info = data["info"]
			total_tds = data["tds_total"]

			if not total_tds:
				continue

			total_allocated = self.pe_allocated.get(pe_name, 0)
			unallocated_tds = total_tds - total_allocated

			if unallocated_tds <= 0:
				continue

			category = info.tax_withholding_category

			party_type = info.party_type
			party = info.party
			tax_id = self.party_tax_id_cache.get((party_type, party))
			tax_rate, _ = get_tax_rate_for_date(self.tax_rate_map, category, info.posting_date)

			if tax_rate:
				unallocated_taxable = flt(unallocated_tds * 100 / tax_rate, 2)
			else:
				unallocated_taxable = info.paid_amount

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


def migrate_sales_invoices(tds_accounts, tax_rate_map, party_tax_id_cache, skip_docs, customers):
	gle = frappe.qb.DocType("GL Entry")
	si = frappe.qb.DocType("Sales Invoice")
	cust = frappe.qb.DocType("Customer")

	tcs_accounts_list = tds_accounts["all_accounts"]

	tcs_gl = (
		frappe.qb.from_(gle)
		.select(
			gle.voucher_no,
			Sum(gle.credit - gle.debit).as_("total_tcs"),
			Max(gle.account).as_("account"),
		)
		.where(gle.voucher_type == "Sales Invoice")
		.where(gle.is_cancelled == 0)
		.where(gle.account.isin(tcs_accounts_list))
		.groupby(gle.voucher_no)
	).as_("tcs_gl")

	tcs_entries = (
		frappe.qb.from_(si)
		.left_join(tcs_gl)
		.on(tcs_gl.voucher_no == si.name)
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
			IfNull(tcs_gl.total_tcs, 0).as_("total_tcs"),
			tcs_gl.account,
		)
		.where(si.docstatus == 1)
		.where(si.is_opening == "No")
		.where(si.customer.isin(customers))
		# Without a category or a TCS row there is no rate, so the invoice would be skipped below
		.where((IfNull(cust.tax_withholding_category, "") != "") | tcs_gl.account.isnotnull())
		.run(as_dict=True)
	)

	all_entries = {}
	category_wise_invoices = defaultdict(list)

	for row in tcs_entries:
		if ("Sales Invoice", row.invoice_name) in skip_docs:
			continue

		total_tcs = row.total_tcs
		net_grand_total = abs(row.base_grand_total - total_tcs)

		category = row.tax_withholding_category
		if not category:
			account_key = (row.company, row.account)
			category = tds_accounts["account_map"].get(account_key)

		party_type = "Customer"
		party = row.customer
		tax_id = party_tax_id_cache.get((party_type, party))

		tax_rate, _ = get_tax_rate_for_date(tax_rate_map, category, row.posting_date)

		if not tax_rate:
			continue

		calculated_taxable = 0
		if tax_rate and total_tcs:
			calculated_taxable = flt(total_tcs * 100 / tax_rate, 2)

		if row.is_return:
			total_tcs = -abs(total_tcs)
			calculated_taxable = -abs(calculated_taxable)

		entries = []
		values = {
			"company": row.company,
			"party_type": party_type,
			"party": party,
			"tax_id": tax_id,
			"tax_withholding_category": category,
			"tax_rate": tax_rate,
			"taxable_doctype": "Sales Invoice",
			"taxable_name": row.invoice_name,
			"taxable_date": row.posting_date,
			"withholding_doctype": "Sales Invoice",
			"withholding_name": row.invoice_name,
			"withholding_date": row.posting_date,
			"currency": row.currency,
			"conversion_rate": row.conversion_rate or 1,
		}

		# v15 always charged TCS on the excess
		if abs(calculated_taxable) < net_grand_total:
			taxable_exemption_amount = flt(net_grand_total - abs(calculated_taxable), 2)

			if row.is_return:
				taxable_exemption_amount = -abs(taxable_exemption_amount)

			entries.append(
				{
					**values,
					"taxable_amount": taxable_exemption_amount,
					"withholding_amount": 0,
					"under_withheld_reason": "Threshold Exemption",
				}
			)

		if total_tcs:
			entries.append({**values, "taxable_amount": calculated_taxable, "withholding_amount": total_tcs})

		all_entries[("Sales Invoice", row.invoice_name)] = entries
		category_wise_invoices[category].append(row.invoice_name)

	bulk_insert_entries(all_entries)

	for category, invoices in category_wise_invoices.items():
		for batch in create_batch(invoices, BATCH_SIZE):
			frappe.db.set_value(
				"Sales Invoice Item",
				{"parent": ("in", batch), "parenttype": "Sales Invoice"},
				{"tax_withholding_category": category, "apply_tds": 1},
				update_modified=False,
			)

	for batch in create_batch([name for _doctype, name in all_entries], BATCH_SIZE):
		frappe.db.set_value("Sales Invoice", {"name": ("in", batch)}, {"apply_tds": 1}, update_modified=False)

	# Without the flag v15 never set, the new flow adds a second TCS row; skipped invoices need it too
	for batch in create_batch([row.invoice_name for row in tcs_entries if row.account], BATCH_SIZE):
		frappe.db.set_value(
			"Sales Taxes and Charges",
			{
				"parent": ("in", batch),
				"parenttype": "Sales Invoice",
				"account_head": ("in", tcs_accounts_list),
			},
			"is_tax_withholding_account",
			1,
			update_modified=False,
		)


def migrate_journal_entries(
	tds_accounts,
	tax_rate_map,
	party_tax_id_cache,
	skip_docs,
	paid_journals,
	party_categories,
):
	gle = frappe.qb.DocType("GL Entry")
	je = frappe.qb.DocType("Journal Entry")
	jea = frappe.qb.DocType("Journal Entry Account")

	all_tds_accounts = tds_accounts["all_accounts"]

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
			je.total_debit,
		)
		.where(gle.voucher_type == "Journal Entry")
		.where(gle.is_cancelled == 0)
		.where(je.docstatus == 1)
		.where(gle.account.isin(all_tds_accounts))
		.run(as_dict=True)
	)

	je_names = list({row.journal_entry for row in tds_gl_entries})
	je_parties = {}
	for batch in create_batch(je_names, BATCH_SIZE):
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
			.where(jea.parent.isin(batch))
			.where(jea.party_type.isnotnull())
			.where(jea.party_type != "")
			.where(jea.party.isnotnull())
			.where(jea.party != "")
			.where(jea.account.notin(all_tds_accounts))  # Exclude TDS account rows
			.run(as_dict=True)
		)
		for row in jea_party_rows:
			if row.parent not in je_parties:
				je_parties[row.parent] = (row.party_type, row.party, row.account_currency, row.exchange_rate)

	je_taxes = {}
	for row in tds_gl_entries:
		if row.journal_entry not in je_taxes:
			je_taxes[row.journal_entry] = {"info": row, "gl_rows": []}
		je_taxes[row.journal_entry]["gl_rows"].append(row)

	all_entries = {}
	category_wise_jes = defaultdict(set)
	journals_with_tds = []

	for je_name, data in je_taxes.items():
		info = data["info"]

		# Journals hold TDS only, never TCS
		total_tds = sum(flt(row.credit) - flt(row.debit) for row in data["gl_rows"])

		# A net debit is TDS paid to the government
		if total_tds <= 0:
			continue

		journals_with_tds.append(je_name)
		if ("Journal Entry", je_name) in skip_docs:
			continue

		party_type = None
		party = None
		account_currency = ""
		exchange_rate = 1

		if je_name in je_parties:
			party_type, party, account_currency, exchange_rate = je_parties[je_name]

		# Category in the v15 report's order: the account's only one, the journal's, then the party's default
		category = None
		for gl_row in data["gl_rows"]:
			category = tds_accounts["account_map"].get((info.company, gl_row.account))
			if category:
				break

		category = category or info.tax_withholding_category
		category = category or party_categories.get((party_type, party))

		tax_id = party_tax_id_cache.get((party_type, party))
		tax_rate, tax_on_excess = get_tax_rate_for_date(tax_rate_map, category, info.posting_date)

		calculated_taxable = 0
		if tax_rate and total_tds:
			calculated_taxable = min(flt(total_tds * 100 / tax_rate, 2), info.total_debit)

		entries = []
		values = {
			"company": info.company,
			"party_type": party_type,
			"party": party,
			"tax_id": tax_id,
			"tax_withholding_category": category,
			"tax_rate": tax_rate,
			"taxable_doctype": "Journal Entry",
			"taxable_name": je_name,
			"taxable_date": info.posting_date,
			"withholding_doctype": "Journal Entry",
			"withholding_name": je_name,
			"withholding_date": info.posting_date,
			"currency": account_currency or "",
			"conversion_rate": flt(exchange_rate, 9) or 1,
		}

		if tax_on_excess and calculated_taxable < info.total_debit:
			entries.append(
				{
					**values,
					"taxable_amount": flt(info.total_debit - abs(calculated_taxable), 2),
					"withholding_amount": 0,
					"under_withheld_reason": "Threshold Exemption",
				}
			)

		entries.append({**values, "taxable_amount": calculated_taxable, "withholding_amount": total_tds})
		all_entries[("Journal Entry", je_name)] = entries

		category_wise_jes[category].add(je_name)

	# v15 counted journals without TDS but taxed them only in categories not on excess; untaxed ones stay open
	tds_jea = frappe.qb.DocType("Journal Entry Account", alias="tds_jea")
	journals_without_tds = (
		frappe.qb.from_(je)
		.join(jea)
		.on(jea.parent == je.name)
		.select(
			je.name,
			je.company,
			je.posting_date,
			je.tax_withholding_category,
			jea.party,
			Max(jea.account_currency).as_("account_currency"),
			Max(jea.exchange_rate).as_("exchange_rate"),
			Sum(jea.credit - jea.debit).as_("amount"),
		)
		.where(je.docstatus == 1)
		.where(je.is_opening == "No")
		.where(je.apply_tds == 1)
		.where(IfNull(je.tax_withholding_category, "") != "")
		.where(jea.party_type == "Supplier")
		.where(IfNull(jea.reference_type, "") != "Purchase Invoice")
		# v15 ticked the TDS row it added, which may be on an account since removed from the category
		.where(
			je.name.notin(
				frappe.qb.from_(tds_jea)
				.select(tds_jea.parent)
				.where(tds_jea.parenttype == "Journal Entry")
				.where(tds_jea.is_tax_withholding_account == 1)
				.where(tds_jea.credit != tds_jea.debit)
			)
		)
		.groupby(je.name, je.company, je.posting_date, je.tax_withholding_category, jea.party)
		.run(as_dict=True)
	)

	for row in journals_without_tds:
		if (
			not row.amount
			or row.name in je_taxes
			or row.name in paid_journals
			or ("Journal Entry", row.name) in skip_docs
		):
			continue

		tax_rate, tax_on_excess = get_tax_rate_for_date(
			tax_rate_map, row.tax_withholding_category, row.posting_date
		)
		if tax_on_excess:
			continue

		all_entries.setdefault(("Journal Entry", row.name), []).append(
			{
				"company": row.company,
				"party_type": "Supplier",
				"party": row.party,
				"tax_id": party_tax_id_cache.get(("Supplier", row.party)),
				"tax_withholding_category": row.tax_withholding_category,
				"taxable_amount": row.amount,
				"tax_rate": tax_rate,
				"withholding_amount": 0,
				"taxable_doctype": "Journal Entry",
				"taxable_name": row.name,
				"taxable_date": row.posting_date,
				"withholding_doctype": "",
				"withholding_name": "",
				"withholding_date": None,
				"currency": row.account_currency or "",
				"conversion_rate": flt(row.exchange_rate, 9) or 1,
			}
		)

	bulk_insert_entries(all_entries)

	for category, je_names in category_wise_jes.items():
		for batch in create_batch(list(je_names), BATCH_SIZE):
			frappe.db.set_value(
				"Journal Entry",
				{"name": ("in", batch)},
				{"apply_tds": 1, "tax_withholding_category": category},
				update_modified=False,
			)

	# Only the deduction row (a debit pays TDS, a party row is the party's own); skipped journals need it too
	for batch in create_batch(journals_with_tds, BATCH_SIZE):
		frappe.db.set_value(
			"Journal Entry Account",
			{
				"parent": ("in", batch),
				"parenttype": "Journal Entry",
				"account": ("in", all_tds_accounts),
				"credit": (">", 0),
				"party": ("is", "not set"),
			},
			"is_tax_withholding_account",
			1,
			update_modified=False,
		)


def copy_category_to_items_for_purchase(column_cache):
	parent_doctype = "Purchase Invoice"
	item_doctype = "Purchase Invoice Item"

	item_cols = column_cache.get(item_doctype, {})

	if not item_cols.get("tax_withholding_category"):
		return

	parent = frappe.qb.DocType(parent_doctype)
	item = frappe.qb.DocType(item_doctype, alias="item")

	# Subquery and unqualified column: Postgres supports neither UPDATE ... JOIN nor alias.column in SET
	(
		frappe.qb.update(item)
		.set(
			"tax_withholding_category",
			Bracket(
				frappe.qb.from_(parent)
				.select(parent.tax_withholding_category)
				.where(parent.name == item.parent)
			),
		)
		.where(
			item.parent.isin(
				frappe.qb.from_(parent)
				.select(parent.name)
				.where(IfNull(parent.tax_withholding_category, "") != "")
			)
		)
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

	invoice_category = (
		frappe.qb.from_(parent)
		.join(customer)
		.on(parent.customer == customer.name)
		.select(customer.tax_withholding_category)
		.where(parent.name == item.parent)
	)

	# Subquery and unqualified column: Postgres supports neither UPDATE ... JOIN nor alias.column in SET
	(
		frappe.qb.update(item)
		.set("tax_withholding_category", Bracket(invoice_category))
		.where(
			item.parent.isin(
				frappe.qb.from_(parent)
				.join(customer)
				.on(parent.customer == customer.name)
				.select(parent.name)
				.where(IfNull(customer.tax_withholding_category, "") != "")
			)
		)
		.where(IfNull(item.tax_withholding_category, "") == "")
		.run()
	)
