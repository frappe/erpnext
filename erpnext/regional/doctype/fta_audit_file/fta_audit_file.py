# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
FTA Audit File DocType Controller

Owns generation of FTA Audit Files (FAF) for UAE VAT compliance per the
FTA "Requirements Document for Tax Accounting Software" (October 2017),
Appendix 5.

A conformant VAT FAF contains four CSV tables in this order, each
delimited by an explicit start/end marker row:

  1. Company Information      (CompInfoStart .. CompInfoEnd)
  2. Purchase Listing         (PurcDataStart .. PurcDataEnd)
  3. Supply Listing           (SuppDataStart .. SuppDataEnd)
  4. General Ledger           (GLDataStart   .. GLDataEnd)

The footer of each transactional table carries running totals plus a
transaction count. Primary amount columns are in the company's accounting
currency (typically AED for a UAE-registered entity); foreign-currency
mirrors are emitted alongside when the source invoice is in a different
currency.
"""

import csv
import io

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today
from frappe.utils.file_manager import save_file

FAF_VERSION = "FAFv1.0.0"
DEFAULT_COUNTRY = "United Arab Emirates"
DEFAULT_DATE = "31-12-9999"
PRODUCT_VERSION = "ERPNext"

# Number of GL Entry rows read into memory per batch when streaming the
# General Ledger section. Large UAE companies routinely produce hundreds
# of thousands of GL entries per year; reading them all into a single list
# would push the background worker over its memory limit.
GL_PAGE_SIZE = 5000

# Inputs that define what the FAF file represents. Once the file has been
# Generated or Submitted, changing any of these would silently desync the
# attached CSV from the form, so we lock them.
LOCKED_INPUT_FIELDS = (
	"company",
	"from_date",
	"to_date",
	"file_type",
	"include_opening_balance",
	"tax_agency_name",
	"tan",
	"tax_agent_name",
	"taan",
)
LOCKED_STATUSES = ("Generated", "Submitted")
IN_FLIGHT_STATUSES = ("Queued", "Generating")


class FTAAuditFile(Document):
	def validate(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date"))

		if not frappe.db.get_value("Company", self.company, "tax_id"):
			frappe.throw(
				_("Company {0} does not have a Tax ID (TRN). Please set the Tax ID in Company.").format(
					self.company
				)
			)

		self._guard_locked_fields()

		if self.status != "Error":
			self.error_message = None

	def _guard_locked_fields(self):
		"""Block edits to FAF inputs once the file is Generated or Submitted.

		The status field alone is read-only in the UI, but a user with write
		permission can still patch fields via REST or scripts; this enforces
		immutability server-side so the attached CSV always matches the form.
		"""
		if self.is_new():
			return

		previous_status = self.get_db_value("status")
		if previous_status not in LOCKED_STATUSES:
			return

		changed = [f for f in LOCKED_INPUT_FIELDS if self.has_value_changed(f)]
		if changed:
			frappe.throw(
				_("Cannot modify {0} after the FAF has been {1}.").format(", ".join(changed), previous_status)
			)

	@frappe.whitelist()
	def generate_faf(self):
		"""Queue FAF generation as a background job.

		Returns immediately with status ``Queued``. The actual generation
		runs in ``_run_generation`` on the ``long`` queue (Frappe's
		``enqueue_doc`` re-fetches a fresh doc inside the worker) and
		updates ``status``, ``faf_file``, ``generation_log``, and
		``error_message`` when complete.

		Under ``frappe.flags.in_test`` the job runs synchronously so tests
		can assert on the post-generation state without polling.
		"""
		# `@frappe.whitelist()` gates network access but not document write
		# permission; without this explicit check, a user with read-only
		# access could still trigger generation via REST.
		self.check_permission("write")

		# Re-read status from DB so two concurrent button clicks can't both
		# enqueue a job — the second one sees Queued/Generating and bails.
		current_status = frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		if current_status in IN_FLIGHT_STATUSES:
			frappe.throw(_("FAF generation is already {0} for this document.").format(current_status))
		if current_status in ("Generated", "Submitted"):
			# UI hides the Generate/Retry button for Generated and Submitted;
			# enforce the same lifecycle on the REST endpoint so a direct
			# call cannot silently overwrite the attached CSV.
			frappe.throw(_("FAF is already {0}; create a new document to regenerate.").format(current_status))

		self.status = "Queued"
		self.generation_log = ""
		self.error_message = None
		self.save()

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_run_generation",
			queue="long",
			timeout=1500,
			enqueue_after_commit=True,
			now=bool(frappe.flags.in_test),
		)

		return {
			"success": True,
			"message": _("FAF generation has been queued. The status will update when complete."),
			"docname": self.name,
			"status": self.status,
		}

	@frappe.whitelist()
	def mark_as_submitted(self):
		"""Mark the FAF as submitted to the FTA portal (manual record)."""
		self.check_permission("write")
		if self.status != "Generated":
			frappe.throw(_("Only Generated files can be marked as Submitted"))
		self.status = "Submitted"
		self.save()
		return {"success": True, "message": _("FAF marked as submitted")}

	def _run_generation(self):
		"""Background entry point. Invoked via ``frappe.enqueue_doc`` from
		``generate_faf`` (or synchronously under ``frappe.flags.in_test``).

		Broad ``except`` is intentional: a long-running batch op records
		the failure on the doc itself (status/error_message/log) so the
		user sees what went wrong without the request 500'ing. The
		exception is re-raised so the queue marks the job as failed and
		the traceback is written to the Error Log.
		"""
		try:
			self.status = "Generating"
			self.save()

			result = self._build_faf()
			self.faf_file = result["file_url"]
			self.generation_log = result["log"]
			self.status = "Generated"
			self.save()
		except Exception as e:
			try:
				err_doc = frappe.get_doc(self.doctype, self.name)
				err_doc.status = "Error"
				err_doc.error_message = str(e)
				err_doc.generation_log = (err_doc.generation_log or "") + f"\n\nError: {e}"
				err_doc.save()
			except Exception:
				# Don't lose the original failure if persisting the Error
				# state itself fails (e.g. row lock, validation regression);
				# log the secondary failure with context, then re-raise the
				# original ``e`` below so the job is still marked failed.
				frappe.log_error(
					title=_("FAF Error-state persistence failed"),
					message=f"{self.doctype} {self.name}\n\n{frappe.get_traceback()}",
				)
			frappe.log_error(
				title=_("FAF Generation Error"),
				message=frappe.get_traceback(),
			)
			raise

	def _build_faf(self):
		"""Build the FAF CSV per Appendix 5 and attach it to this document."""
		log_entries = []

		def log(msg):
			log_entries.append(msg)

		log(f"Starting FAF generation for {self.company}")
		log(f"Period: {self.from_date} to {self.to_date}")
		log(f"File Type: {self.file_type}")

		output = io.StringIO()
		writer = csv.writer(output)

		self._write_company_info(writer)
		log("Company Information written")

		purchase_count = self._write_purchase_listing(writer)
		log(f"Purchase Listing written: {purchase_count} line items")

		supply_count = self._write_supply_listing(writer)
		log(f"Supply Listing written: {supply_count} line items")

		gl_count = self._write_gl_listing(writer)
		log(f"General Ledger written: {gl_count} entries")

		csv_content = output.getvalue()
		output.close()

		file_name = f"FAF_{self.company}_{self.from_date}_to_{self.to_date}.csv".replace(" ", "_")
		file_doc = save_file(
			fname=file_name,
			content=csv_content.encode("utf-8"),
			dt="FTA Audit File",
			dn=self.name,
			is_private=1,
		)

		log(f"FAF file generated: {file_name}")
		log("Generation completed successfully")

		return {"file_url": file_doc.file_url, "log": "\n".join(log_entries)}

	def _write_company_info(self, writer):
		"""Emit ``CompInfoStart`` + body row + ``CompInfoEnd`` per Appendix 5."""
		writer.writerow(["CompInfoStart"])

		info = (
			frappe.db.get_value(
				"Company",
				self.company,
				["company_name", "company_name_in_arabic", "tax_id"],
				as_dict=True,
			)
			or {}
		)

		writer.writerow(
			[
				_clean(info.get("company_name") or self.company),
				_clean(info.get("company_name_in_arabic") or ""),
				info.get("tax_id") or "",
				_clean(self.tax_agency_name or ""),
				_clean(self.tan or ""),
				_clean(self.tax_agent_name or ""),
				_clean(self.taan or ""),
				_format_date(self.from_date),
				_format_date(self.to_date),
				_format_date(today()),
				PRODUCT_VERSION,
				FAF_VERSION,
			]
		)

		writer.writerow(["CompInfoEnd"])

	def _write_purchase_listing(self, writer):
		"""Emit Purchase Listing per Appendix 5 with end-of-table totals row."""
		writer.writerow(["PurcDataStart"])

		invoices = frappe.get_all(
			"Purchase Invoice",
			filters={
				"company": self.company,
				"posting_date": ["between", [self.from_date, self.to_date]],
				"docstatus": 1,
			},
			fields=[
				"name",
				"supplier",
				"supplier_name",
				"posting_date",
				"permit_no",
				"currency",
				"conversion_rate",
			],
			order_by="posting_date asc, name asc",
		)
		if not invoices:
			writer.writerow(["PurcDataEnd", _money(0), _money(0), 0])
			return 0

		invoice_names = [inv.name for inv in invoices]
		supplier_names = list({inv.supplier for inv in invoices if inv.supplier})

		supplier_trn_map = _bulk_party_field("Supplier", supplier_names, "tax_id")
		items_by_invoice = _bulk_invoice_items(
			"Purchase Invoice Item",
			invoice_names,
			[
				"parent",
				"idx",
				"item_name",
				"description",
				"base_net_amount",
				"net_amount",
				"tax_amount",
				"item_tax_template",
			],
		)
		tax_code_bands = _bulk_tax_code_bands(
			{
				item.item_tax_template
				for items in items_by_invoice.values()
				for item in items
				if item.item_tax_template
			}
		)

		company_currency = _company_currency(self.company)

		total_purchase_company = 0.0
		total_vat_company = 0.0
		line_count = 0

		for inv in invoices:
			supplier_trn = supplier_trn_map.get(inv.supplier, "")
			fcy_code, fcy_factor = _fcy_for_invoice(inv.currency, inv.conversion_rate, company_currency)

			for item in items_by_invoice.get(inv.name, []):
				# base_net_amount is company-currency; tax_amount is a UAE
				# custom field with options="currency" and therefore stored
				# in the document's invoice currency. Multiply by the
				# conversion rate to land in company currency.
				net_company = flt(item.base_net_amount, 2)
				vat_invoice = flt(item.tax_amount or 0, 2)
				vat_company = flt(vat_invoice * fcy_factor, 2)
				net_fcy = flt(item.net_amount or 0, 2) if fcy_code != "XXX" else 0.0
				vat_fcy = vat_invoice if fcy_code != "XXX" else 0.0

				writer.writerow(
					[
						_clean(inv.supplier_name),
						supplier_trn,
						_format_date(inv.posting_date),
						inv.name,
						inv.permit_no or "",
						item.idx,
						_clean(item.description or item.item_name or ""),
						_money(net_company),
						_money(vat_company),
						_resolve_tax_code(item.item_tax_template, inv.posting_date, tax_code_bands),
						fcy_code,
						_money(net_fcy),
						_money(vat_fcy),
					]
				)
				total_purchase_company += net_company
				total_vat_company += vat_company
				line_count += 1

		writer.writerow(
			[
				"PurcDataEnd",
				_money(total_purchase_company),
				_money(total_vat_company),
				line_count,
			]
		)
		return line_count

	def _write_supply_listing(self, writer):
		"""Emit Supply Listing per Appendix 5 with end-of-table totals row."""
		writer.writerow(["SuppDataStart"])

		invoices = frappe.get_all(
			"Sales Invoice",
			filters={
				"company": self.company,
				"posting_date": ["between", [self.from_date, self.to_date]],
				"docstatus": 1,
			},
			fields=[
				"name",
				"customer",
				"customer_name",
				"posting_date",
				"currency",
				"conversion_rate",
			],
			order_by="posting_date asc, name asc",
		)
		if not invoices:
			writer.writerow(["SuppDataEnd", _money(0), _money(0), 0])
			return 0

		invoice_names = [inv.name for inv in invoices]
		customer_names = list({inv.customer for inv in invoices if inv.customer})

		customer_trn_map = _bulk_party_field("Customer", customer_names, "tax_id")
		customer_country_map = _bulk_party_country("Customer", customer_names)
		items_by_invoice = _bulk_invoice_items(
			"Sales Invoice Item",
			invoice_names,
			[
				"parent",
				"idx",
				"item_name",
				"description",
				"base_net_amount",
				"net_amount",
				"tax_amount",
				"item_tax_template",
				"is_zero_rated",
				"is_exempt",
			],
		)
		tax_code_bands = _bulk_tax_code_bands(
			{
				item.item_tax_template
				for items in items_by_invoice.values()
				for item in items
				if item.item_tax_template
			}
		)

		company_currency = _company_currency(self.company)

		total_supply_company = 0.0
		total_vat_company = 0.0
		line_count = 0

		for inv in invoices:
			customer_trn = customer_trn_map.get(inv.customer, "")
			customer_country = customer_country_map.get(inv.customer) or DEFAULT_COUNTRY
			fcy_code, fcy_factor = _fcy_for_invoice(inv.currency, inv.conversion_rate, company_currency)

			for item in items_by_invoice.get(inv.name, []):
				# See _write_purchase_listing for the currency convention:
				# tax_amount is invoice-currency, base_net_amount is
				# company-currency, and fcy_factor converts invoice → company.
				net_company = flt(item.base_net_amount, 2)
				vat_invoice = flt(item.tax_amount or 0, 2)
				vat_company = flt(vat_invoice * fcy_factor, 2)
				net_fcy = flt(item.net_amount or 0, 2) if fcy_code != "XXX" else 0.0
				vat_fcy = vat_invoice if fcy_code != "XXX" else 0.0

				if item.is_zero_rated:
					tax_code = "ZR"
				elif item.is_exempt:
					tax_code = "EX"
				else:
					tax_code = _resolve_tax_code(item.item_tax_template, inv.posting_date, tax_code_bands)

				writer.writerow(
					[
						_clean(inv.customer_name),
						customer_trn,
						_format_date(inv.posting_date),
						inv.name,
						item.idx,
						_clean(item.description or item.item_name or ""),
						_money(net_company),
						_money(vat_company),
						tax_code,
						_clean(customer_country),
						fcy_code,
						_money(net_fcy),
						_money(vat_fcy),
					]
				)
				total_supply_company += net_company
				total_vat_company += vat_company
				line_count += 1

		writer.writerow(
			[
				"SuppDataEnd",
				_money(total_supply_company),
				_money(total_vat_company),
				line_count,
			]
		)
		return line_count

	def _write_gl_listing(self, writer):
		"""Emit General Ledger per Appendix 5 with end-of-table totals row.

		GL Entry rows are streamed in pages of ``GL_PAGE_SIZE`` to keep
		memory bounded for multi-year exports on large companies; the
		running-balance, account-name, and totals state survives across
		pages so the output is identical to a single-fetch implementation.
		"""
		writer.writerow(["GLDataStart"])

		company_currency = _company_currency(self.company)
		base_filters = {
			"company": self.company,
			"posting_date": ["between", [self.from_date, self.to_date]],
			"is_cancelled": 0,
		}

		# Opening balances need every account that posts in the period up
		# front; without that flag we cache account names lazily as we
		# encounter them in each batch.
		if self.include_opening_balance:
			accounts_in_period = frappe.get_all(
				"GL Entry", filters=base_filters, pluck="account", distinct=True
			)
			running_balance = _opening_balances_by_account(self.company, self.from_date, accounts_in_period)
			account_name_map = _bulk_party_field("Account", accounts_in_period, "account_name")
		else:
			running_balance = {}
			account_name_map = {}

		source_type_map = {
			"Sales Invoice": "AR",
			"Purchase Invoice": "AP",
			"Journal Entry": "General Journal",
			"Payment Entry": "Cash Receipt",
			"Stock Entry": "Inventory",
			"Delivery Note": "Inventory Sale",
			"Purchase Receipt": "Purchases",
		}

		total_debit = 0.0
		total_credit = 0.0
		count = 0
		start = 0

		while True:
			batch = frappe.get_all(
				"GL Entry",
				filters=base_filters,
				fields=[
					"name",
					"posting_date",
					"account",
					"remarks",
					"against",
					"voucher_no",
					"voucher_type",
					"debit",
					"credit",
				],
				order_by="posting_date asc, creation asc",
				limit_start=start,
				limit_page_length=GL_PAGE_SIZE,
			)
			if not batch:
				break

			# Backfill the account-name cache for accounts new to this batch.
			new_accounts = [e.account for e in batch if e.account and e.account not in account_name_map]
			if new_accounts:
				account_name_map.update(_bulk_party_field("Account", new_accounts, "account_name"))

			for entry in batch:
				account_name = account_name_map.get(entry.account) or entry.account
				source_type = source_type_map.get(entry.voucher_type, entry.voucher_type or "")
				debit = flt(entry.debit, 2)
				credit = flt(entry.credit, 2)

				running_balance[entry.account] = running_balance.get(entry.account, 0.0) + debit - credit
				balance = flt(running_balance[entry.account], 2)

				writer.writerow(
					[
						_format_date(entry.posting_date),
						entry.account,
						_clean(account_name),
						_clean(entry.remarks or ""),
						_clean(entry.against or ""),
						entry.voucher_no,
						entry.voucher_no,
						source_type,
						_money(debit),
						_money(credit),
						_money(balance),
					]
				)
				total_debit += debit
				total_credit += credit
				count += 1

			if len(batch) < GL_PAGE_SIZE:
				break
			start += GL_PAGE_SIZE

		writer.writerow(
			[
				"GLDataEnd",
				_money(total_debit),
				_money(total_credit),
				count,
				company_currency,
			]
		)
		return count


def _clean(value):
	"""Sanitize a string for FAF CSV.

	The spec mandates that the delimiter (``,``) must not appear inside any
	field. We follow Microsoft Dynamics 365's UAE FAF convention and
	substitute ``;`` so the original separator stays visible in the data.
	Embedded newlines are stripped because they would otherwise break the
	CSV row structure.
	"""
	if value is None:
		return ""
	return str(value).replace(",", ";").replace("\n", " ").replace("\r", " ").strip()


def _format_date(d):
	"""Format a date as DD-MM-YYYY per FTA spec; missing values become 31-12-9999."""
	if not d:
		return DEFAULT_DATE
	return getdate(d).strftime("%d-%m-%Y")


def _money(value):
	"""Format a numeric field as ``Decimal[14,2]`` per FTA spec.

	Python's ``csv.writer`` calls ``str()`` on numeric values, which
	strips trailing zeros (``0.00`` → ``"0.0"``). The spec mandates two
	decimal places everywhere a Decimal[14,2] field is emitted, so we
	pre-format to a string here.
	"""
	return f"{flt(value):.2f}"


def _company_currency(company):
	return frappe.db.get_value("Company", company, "default_currency") or "AED"


def _fcy_for_invoice(invoice_currency, conversion_rate, company_currency):
	"""Resolve foreign-currency code + conversion factor for an invoice.

	Returns ``("XXX", 1.0)`` when the invoice is in the company's home
	currency (no FCY columns to populate); otherwise the ISO 4217 code
	plus the conversion factor (rate to company currency).
	"""
	if not invoice_currency or invoice_currency == company_currency:
		return ("XXX", 1.0)
	return (invoice_currency, flt(conversion_rate) or 1.0)


def _bulk_party_field(doctype, names, field):
	"""Return ``{name: field_value}`` for the given names. Empty input → empty dict."""
	if not names:
		return {}
	rows = frappe.get_all(
		doctype,
		filters={"name": ["in", names]},
		fields=["name", field],
	)
	return {r["name"]: (r.get(field) or "") for r in rows}


def _bulk_party_country(party_doctype, party_names):
	"""Return ``{party_name: country}`` for each party.

	Picks deterministically when a party has multiple addresses: prefer the
	one flagged ``is_primary_address``, then ``is_shipping_address``, then
	the lowest address name. Without this ordering, MariaDB would return
	rows in storage-engine order and the FAF would be non-reproducible
	across runs.
	"""
	if not party_names:
		return {}

	dl = frappe.qb.DocType("Dynamic Link")
	addr = frappe.qb.DocType("Address")
	rows = (
		frappe.qb.from_(dl)
		.inner_join(addr)
		.on(addr.name == dl.parent)
		.where(dl.link_doctype == party_doctype)
		.where(dl.parenttype == "Address")
		.where(dl.link_name.isin(party_names))
		.where(addr.country.isnotnull())
		.where(addr.country != "")
		.select(dl.link_name, addr.country)
		.orderby(addr.is_primary_address, order=frappe.qb.desc)
		.orderby(addr.is_shipping_address, order=frappe.qb.desc)
		.orderby(addr.name)
		.run(as_dict=True)
	)
	out = {}
	for r in rows:
		out.setdefault(r["link_name"], r["country"])
	return out


def _opening_balances_by_account(company, period_start, accounts):
	"""Net pre-period balance per account: sum(debit) - sum(credit) before ``period_start``.

	Returns ``{account: net}`` where net is debit-positive (positive for
	asset/expense accounts that carry a debit balance, negative for
	liability/equity/revenue accounts that carry a credit balance).
	Single aggregated SQL via ``frappe.qb`` — one query regardless of the
	number of accounts. Cancelled GL entries are excluded.
	"""
	if not accounts:
		return {}

	from frappe.query_builder.functions import Sum

	gle = frappe.qb.DocType("GL Entry")
	rows = (
		frappe.qb.from_(gle)
		.where(gle.company == company)
		.where(gle.posting_date < period_start)
		.where(gle.is_cancelled == 0)
		.where(gle.account.isin(accounts))
		.groupby(gle.account)
		.select(
			gle.account,
			Sum(gle.debit).as_("debit"),
			Sum(gle.credit).as_("credit"),
		)
		.run(as_dict=True)
	)
	return {r["account"]: flt(r.get("debit") or 0) - flt(r.get("credit") or 0) for r in rows}


def _bulk_invoice_items(child_doctype, invoice_names, fields):
	"""Return ``{parent_invoice: [items...]}`` for the given invoice names."""
	if not invoice_names:
		return {}
	items = frappe.get_all(
		child_doctype,
		filters={"parent": ["in", invoice_names]},
		fields=fields,
		order_by="parent asc, idx asc",
	)
	out = {}
	for item in items:
		out.setdefault(item["parent"], []).append(item)
	return out


_FTA_TAX_CODES = ("SR", "ZR", "EX", "RC", "IG", "OA", "IA")


def _bulk_tax_code_bands(item_tax_templates):
	"""Return ``{template: [(valid_from, tax_category), ...]}`` sorted desc by valid_from.

	One ``Item Tax Template`` can have multiple ``Item Tax`` rows with
	different ``valid_from`` dates (e.g. tax code changing on a regulator
	cutover). Fetching them all up-front lets ``_resolve_tax_code`` pick
	the row that was in force on each invoice's posting date without an
	extra DB hit per line item.
	"""
	if not item_tax_templates:
		return {}
	rows = frappe.get_all(
		"Item Tax",
		filters={"item_tax_template": ["in", list(item_tax_templates)]},
		fields=["item_tax_template", "tax_category", "valid_from"],
		order_by="valid_from desc",
	)
	out = {}
	for r in rows:
		out.setdefault(r["item_tax_template"], []).append((r.get("valid_from"), r.get("tax_category")))
	return out


def _resolve_tax_code(item_tax_template, posting_date, bands_map):
	"""Derive FTA tax code (SR/ZR/EX/RC/IG/OA/IA) from one Item Tax Template.

	Picks the Item Tax row whose ``valid_from`` is the most recent value
	that is still on or before ``posting_date``; rows with no
	``valid_from`` are treated as always-valid and used only as a
	fallback. Defaults to ``SR`` (Standard Rated) when nothing matches or
	the chosen ``tax_category`` isn't one of the FTA codes.
	"""
	if not item_tax_template:
		return "SR"

	bands = bands_map.get(item_tax_template) or []
	posting = getdate(posting_date) if posting_date else None
	fallback_category = None
	for valid_from, tax_category in bands:
		if valid_from is None:
			fallback_category = fallback_category or tax_category
			continue
		if posting is None or getdate(valid_from) <= posting:
			return tax_category if tax_category in _FTA_TAX_CODES else "SR"

	if fallback_category and fallback_category in _FTA_TAX_CODES:
		return fallback_category
	return "SR"
