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
transaction count. All amounts are in AED (foreign-currency mirrors are
emitted alongside when the source invoice is non-AED).
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

		if self.status != "Error":
			self.error_message = None

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
				pass
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

		if self.file_type != "VAT":
			frappe.throw(_("FAF generation for {0} is not yet implemented").format(self.file_type))

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
		tax_code_map = {
			t: _resolve_tax_code(t)
			for t in {item.item_tax_template for items in items_by_invoice.values() for item in items}
			if t
		}

		company_currency = _company_currency(self.company)

		total_purchase_aed = 0.0
		total_vat_aed = 0.0
		line_count = 0

		for inv in invoices:
			supplier_trn = supplier_trn_map.get(inv.supplier, "")
			fcy_code, fcy_factor = _fcy_for_invoice(inv.currency, inv.conversion_rate, company_currency)

			for item in items_by_invoice.get(inv.name, []):
				net_aed = flt(item.base_net_amount, 2)
				vat_aed = flt(item.tax_amount or 0, 2)
				net_fcy = flt((item.net_amount or 0) if fcy_code != "XXX" else 0, 2)
				vat_fcy = flt(vat_aed / fcy_factor if fcy_factor else 0, 2) if fcy_code != "XXX" else 0.0

				writer.writerow(
					[
						_clean(inv.supplier_name),
						supplier_trn,
						_format_date(inv.posting_date),
						inv.name,
						inv.permit_no or "",
						item.idx,
						_clean(item.description or item.item_name or ""),
						_money(net_aed),
						_money(vat_aed),
						tax_code_map.get(item.item_tax_template, "SR"),
						fcy_code,
						_money(net_fcy),
						_money(vat_fcy),
					]
				)
				total_purchase_aed += net_aed
				total_vat_aed += vat_aed
				line_count += 1

		writer.writerow(
			[
				"PurcDataEnd",
				_money(total_purchase_aed),
				_money(total_vat_aed),
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
		tax_code_map = {
			t: _resolve_tax_code(t)
			for t in {item.item_tax_template for items in items_by_invoice.values() for item in items}
			if t
		}

		company_currency = _company_currency(self.company)

		total_supply_aed = 0.0
		total_vat_aed = 0.0
		line_count = 0

		for inv in invoices:
			customer_trn = customer_trn_map.get(inv.customer, "")
			customer_country = customer_country_map.get(inv.customer) or DEFAULT_COUNTRY
			fcy_code, fcy_factor = _fcy_for_invoice(inv.currency, inv.conversion_rate, company_currency)

			for item in items_by_invoice.get(inv.name, []):
				net_aed = flt(item.base_net_amount, 2)
				vat_aed = flt(item.tax_amount or 0, 2)
				net_fcy = flt((item.net_amount or 0) if fcy_code != "XXX" else 0, 2)
				vat_fcy = flt(vat_aed / fcy_factor if fcy_factor else 0, 2) if fcy_code != "XXX" else 0.0

				if item.is_zero_rated:
					tax_code = "ZR"
				elif item.is_exempt:
					tax_code = "EX"
				else:
					tax_code = tax_code_map.get(item.item_tax_template, "SR")

				writer.writerow(
					[
						_clean(inv.customer_name),
						customer_trn,
						_format_date(inv.posting_date),
						inv.name,
						item.idx,
						_clean(item.description or item.item_name or ""),
						_money(net_aed),
						_money(vat_aed),
						tax_code,
						_clean(customer_country),
						fcy_code,
						_money(net_fcy),
						_money(vat_fcy),
					]
				)
				total_supply_aed += net_aed
				total_vat_aed += vat_aed
				line_count += 1

		writer.writerow(
			[
				"SuppDataEnd",
				_money(total_supply_aed),
				_money(total_vat_aed),
				line_count,
			]
		)
		return line_count

	def _write_gl_listing(self, writer):
		"""Emit General Ledger per Appendix 5 with end-of-table totals row."""
		writer.writerow(["GLDataStart"])

		entries = frappe.get_all(
			"GL Entry",
			filters={
				"company": self.company,
				"posting_date": ["between", [self.from_date, self.to_date]],
				"is_cancelled": 0,
			},
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
		)
		if not entries:
			writer.writerow(["GLDataEnd", _money(0), _money(0), 0, "AED"])
			return 0

		account_names = list({e.account for e in entries if e.account})
		account_name_map = _bulk_party_field("Account", account_names, "account_name")

		if self.include_opening_balance:
			running_balance = _opening_balances_by_account(self.company, self.from_date, account_names)
		else:
			running_balance = {}

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

		for entry in entries:
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

		writer.writerow(
			[
				"GLDataEnd",
				_money(total_debit),
				_money(total_credit),
				count,
				"AED",
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
	"""Return ``{party_name: country}`` taken from each party's first address with a country."""
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


def _resolve_tax_code(item_tax_template):
	"""Derive FTA tax code (SR/ZR/EX/RC/IG/OA/IA) from one Item Tax Template.

	Uses the Item Tax row's ``tax_category`` if it matches an FTA code;
	otherwise defaults to ``SR`` (Standard Rated). Setting ``tax_category``
	on each Item Tax is the supported way to control this — there is no
	heuristic fallback on the template name.
	"""
	if not item_tax_template:
		return "SR"

	tax_category = frappe.db.get_value(
		"Item Tax",
		{"item_tax_template": item_tax_template},
		"tax_category",
	)
	if tax_category and tax_category in _FTA_TAX_CODES:
		return tax_category
	return "SR"
