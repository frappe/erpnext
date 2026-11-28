# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import io
import json
import re
from datetime import datetime
from itertools import pairwise

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt, getdate
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)

from erpnext.accounts.doctype.bank_account.bank_account import _set_closing_balance_as_per_statement


class BankStatementImportLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.bank_statement_import_log_column_map.bank_statement_import_log_column_map import (
			BankStatementImportLogColumnMap,
		)

		bank_account: DF.Link
		closing_balance: DF.Currency
		column_mapping: DF.Table[BankStatementImportLogColumnMap]
		currency: DF.Link | None
		detected_amount_format: DF.Literal[
			"Separate columns for withdrawal and deposit",
			'Amount column has "CR"/"DR" values',
			"Amount column has positive/negative values",
			'Transaction type column has "CR"/"DR" values',
			'Transaction type column has "Deposit"/"Withdrawal" values',
			'Transaction type column has "C"/"D" values',
		]
		detected_date_format: DF.Data | None
		detected_header_index: DF.Int
		detected_transaction_ending_index: DF.Int
		detected_transaction_starting_index: DF.Int
		end_date: DF.Date | None
		file: DF.Attach
		number_of_transactions: DF.Int
		pdf_tables: DF.JSON | None
		start_date: DF.Date | None
		status: DF.Literal["Not Started", "Completed"]
		total_credit_transactions: DF.Int
		total_credits: DF.Currency
		total_debit_transactions: DF.Int
		total_debits: DF.Currency
	# end: auto-generated types

	def before_validate(self):
		self.set_currency()

	def set_currency(self):
		account = frappe.get_cached_value("Bank Account", self.bank_account, "account")
		self.currency = frappe.get_cached_value("Account", account, "account_currency")

	def validate(self):
		if not self.is_new() and self.has_value_changed("file"):
			self.validate_file_access()

		if not frappe.has_permission("Bank Transaction", "write"):
			frappe.throw(
				_("You do not have permission to import bank transactions"), title=_("Permission Denied")
			)
		if not frappe.has_permission("Bank Transaction", "create"):
			frappe.throw(
				_("You do not have permission to import bank transactions"), title=_("Permission Denied")
			)

		if not frappe.has_permission("Bank Transaction", "submit"):
			frappe.throw(
				_("You do not have permission to import and submit bank transactions"),
				title=_("Permission Denied"),
			)

		is_company_account, disabled = frappe.get_value(
			"Bank Account", self.bank_account, ["is_company_account", "disabled"]
		)
		if not is_company_account:
			frappe.throw(
				_("The bank account is not a company account. Please select a company account"),
				title=_("Invalid Bank Account"),
			)

		if disabled:
			frappe.throw(
				_("The bank account is disabled. Please enable it"), title=_("Disabled Bank Account")
			)

	def before_insert(self):
		# before_insert reads the file before validate runs
		self.validate_file_access()
		if self.is_pdf():
			tables = self.prepare_pdf_tables()
			self.set_pdf_summary(tables)
		else:
			data = self.get_data()
			self.set_file_properties(data)

	def after_insert(self):
		# Page images are attached here (not in before_insert) because the final docname is
		# only assigned after before_insert runs - attaching earlier links them to the
		# temporary name the client sends.
		if self.is_pdf():
			self.attach_pdf_page_images()

	def set_file_properties(self, raw_data: list[list]):
		self.set_header_row_index(raw_data)
		self.set_column_mapping(raw_data)
		self.recompute_properties(raw_data)

	def recompute_properties(self, raw_data: list[list]):
		"""
		Recompute everything that depends on the header row and column mapping: transaction
		row range, date/amount format, closing balance and totals. Called both during initial
		detection and after the user overrides the mapping or header row.
		"""
		transaction_rows, transaction_starting_index, transaction_ending_index = self.get_transaction_rows(
			raw_data
		)

		self.detected_transaction_starting_index = transaction_starting_index
		self.detected_transaction_ending_index = transaction_ending_index

		self.number_of_transactions = len(transaction_rows)

		date_format, amount_format = get_file_properties(transaction_rows)

		self.detected_amount_format = amount_format
		self.detected_date_format = date_format

		self.set_closing_balance(transaction_rows)

		self.set_total_debits_and_credits(transaction_rows=transaction_rows)

	def set_total_debits_and_credits(self, transaction_rows: list):
		"""
		Given the transaction rows, try to set the total debits and credits
		"""

		total_debits = 0
		total_credits = 0
		debit_transactions = 0
		credit_transactions = 0

		final_transactions = self.get_final_transactions(transaction_rows=transaction_rows)

		for transaction in final_transactions:
			withdrawal = transaction.get("withdrawal", 0) or 0
			deposit = transaction.get("deposit", 0) or 0
			if withdrawal > 0:
				total_debits += withdrawal
				debit_transactions += 1
			if deposit > 0:
				total_credits += deposit
				credit_transactions += 1

		self.total_debits = total_debits
		self.total_credits = total_credits
		self.total_debit_transactions = debit_transactions
		self.total_credit_transactions = credit_transactions

	def get_file_doc(self):
		return frappe.get_doc("File", {"file_url": self.file})

	def validate_file_access(self):
		self.get_file_doc().check_permission("read")

	def get_file_extension(self):
		return self.get_file_doc().get_extension()[1].lower()

	def is_pdf(self):
		return self.get_file_extension() == ".pdf"

	def get_statement_password(self):
		"""Decrypted PDF password stored on the linked Bank Account (if any)."""
		if not self.bank_account:
			return None

		from frappe.utils.password import get_decrypted_password

		return get_decrypted_password(
			"Bank Account", self.bank_account, "statement_password", raise_exception=False
		)

	def get_data(self):
		"""
		Extract the data from a tabular (CSV/XLSX/XLS) attached file as a list of rows.

		PDFs are not handled here - they go through the multi-table PDF pipeline
		(`prepare_pdf_tables`) since a PDF can yield several tables with differing shapes.
		"""

		file_doc = self.get_file_doc()

		extension = self.get_file_extension()
		content = file_doc.get_content()

		if extension not in (".csv", ".xlsx", ".xls"):
			frappe.throw(
				_("Import template should be of type .csv, .xlsx, .xls or .pdf"),
				title=_("Invalid File Type"),
			)

		if extension == ".csv":
			data = read_csv_content(content)
		elif extension == ".xlsx":
			data = read_xlsx_file_from_attached_file(fcontent=content)
		elif extension == ".xls":
			data = read_xls_file_from_attached_file(content)

		return data

	def set_header_row_index(self, data: list[list[str]]):
		"""
		Given the data, try to get the row index of the header row.
		"""

		self.detected_header_index, _ = detect_header_row(data)

	def set_column_mapping(self, data: list[list[str]]):
		"""
		Given the header row, try to map each column index to a standard variable, or set it to "Do not import"
		"""

		self.set_column_mapping_from_columns(detect_column_mapping(data[self.detected_header_index]))

	def set_column_mapping_from_columns(self, columns: list[dict]):
		"""Replace the column_mapping child table from a list of column dicts."""
		self.column_mapping = []

		for col in columns:
			index = col["index"]
			# header_text is mandatory on the child table; fall back to a readable placeholder
			# for headerless tables (content-guessed columns) and user overrides.
			self.append(
				"column_mapping",
				{
					"header_text": col.get("header_text") or _("Column {0}").format(index + 1),
					"variable": col.get("variable") or f"column_{index}",
					"maps_to": col.get("maps_to", "Do not import"),
					"index": index,
				},
			)

	def apply_column_mapping(self, columns: list[dict]):
		"""Persist a user-overridden column mapping and recompute the derived properties."""
		self.set_column_mapping_from_columns(columns)
		self.recompute_properties(self.get_data())

	def apply_header_index(self, header_index: int):
		"""
		Set (or clear, with -1) the header row for a tabular statement.

		The existing column mapping is preserved; it is only re-derived when a header row is
		selected AND that row resolves to a meaningful mapping. Clearing the header (no header
		row) never discards the user's mapping.
		"""
		raw_data = self.get_data()

		if 0 <= header_index < len(raw_data):
			self.detected_header_index = header_index
			candidate = detect_column_mapping(raw_data[header_index])
			if is_meaningful_mapping(candidate):
				self.set_column_mapping_from_columns(candidate)
		else:
			self.detected_header_index = -1

		self.recompute_properties(raw_data)

	def get_transaction_rows(self, data: list[list[str]]):
		"""
		Given the data, header index and column mapping, try to get the transaction rows
		"""

		column_mapping: dict[str, int] = {}
		for column in self.column_mapping:
			if column.maps_to != "Do not import":
				column_mapping[column.maps_to] = column.index

		return extract_transaction_rows(data, column_mapping, self.detected_header_index)

	def set_closing_balance(self, transactions: list):
		"""
		Given the transactions and date format, try to get the statement start date, end date and closing balance
		"""

		self.start_date, self.end_date, self.closing_balance = get_statement_period(
			transactions, self.detected_date_format
		)

	def get_final_transactions(self, transaction_rows: list):
		"""
		Given the parameters detected in the statement (including overrides) try to get the final transactions
		"""

		return compute_final_transactions(
			transaction_rows, self.detected_date_format, self.detected_amount_format
		)

	# ------------------------------------------------------------------ #
	# PDF statement handling
	# ------------------------------------------------------------------ #

	def get_pdf_tables(self) -> list[dict]:
		"""The stored per-table PDF extraction data, parsed from the JSON field."""
		if not self.pdf_tables:
			return []
		if isinstance(self.pdf_tables, str):
			return json.loads(self.pdf_tables)
		return self.pdf_tables

	def prepare_pdf_tables(self) -> list[dict]:
		"""
		Extract each table from the PDF (kept separate, never merged), rasterize the
		pages so the user can confirm tables visually, and run a best-effort per-table
		column mapping. The result is stored as JSON on `pdf_tables`.

		The rendered page images are stashed on the instance and only saved as File docs
		in `after_insert` (see `attach_pdf_page_images`), once the final docname exists.
		"""
		content = self.get_file_doc().get_content()
		password = self.get_statement_password()

		tables = extract_pdf_tables(content, password)

		# Rasterize only the pages that actually produced tables, once each.
		pages = {table["page"] for table in tables}
		page_images = render_pdf_pages(content, password, pages)

		self.flags._pending_page_images = {page: png for page, (png, _scale) in page_images.items()}
		page_scales = {page: scale for page, (_png, scale) in page_images.items()}

		for table in tables:
			table["page_image"] = None  # filled in after_insert
			table["render_scale"] = page_scales.get(table["page"])

			# Best-effort auto mapping. Headers are often missing in PDFs - fall back to
			# guessing from the column contents. The user can correct this afterwards.
			header_index, score = detect_header_row(table["rows"])
			if score >= 2:
				table["header_index"] = header_index
				table["column_mapping"] = detect_column_mapping(table["rows"][header_index])
			else:
				table["header_index"] = None
				table["column_mapping"] = guess_column_mapping_by_content(table["rows"])

			final_transactions, table["date_format"], table["amount_format"] = build_table_transactions(table)
			table["included"] = should_include_table(table, final_transactions)

		self.pdf_tables = json.dumps(tables)
		return tables

	def attach_pdf_page_images(self):
		"""Persist the rendered page images (rendered in `prepare_pdf_tables`) as private
		Files attached to this log, and write their URLs back into `pdf_tables`."""
		pending = getattr(self.flags, "_pending_page_images", None)
		if not pending:
			return

		page_urls = {page: self.save_page_image(png, page) for page, png in pending.items()}

		tables = self.get_pdf_tables()
		for table in tables:
			table["page_image"] = page_urls.get(table["page"])

		self.db_set("pdf_tables", json.dumps(tables), update_modified=False)
		self.flags._pending_page_images = None

	def save_page_image(self, png_bytes: bytes, page_number: int) -> str:
		"""Save a rendered page as a private File attached to this log; return its URL."""
		return (
			frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"statement-{self.name}-page-{page_number}.png",
					"is_private": 1,
					"content": png_bytes,
					"attached_to_doctype": self.doctype,
					"attached_to_name": self.name,
				}
			)
			.insert(ignore_permissions=True)
			.file_url
		)

	def get_pdf_final_transactions(self) -> list[dict]:
		"""Union of transactions across all included PDF tables."""
		final_transactions = []
		for table in self.get_pdf_tables():
			if not table.get("included", True):
				continue
			table_transactions, _df, _af = build_table_transactions(table)
			final_transactions.extend(table_transactions)
		return final_transactions

	def set_pdf_summary(self, tables: list[dict]) -> list[dict]:
		"""Compute the doc-level summary fields from the union of included PDF tables."""
		final_transactions = []
		date_format = None
		amount_format = None

		for table in tables:
			if not table.get("included", True):
				continue
			table_transactions, df, af = build_table_transactions(table)
			final_transactions.extend(table_transactions)
			if table_transactions and date_format is None:
				date_format, amount_format = df, af

		self.detected_date_format = date_format or "%d/%m/%Y"
		self.detected_amount_format = amount_format or "Separate columns for withdrawal and deposit"
		self.number_of_transactions = len(final_transactions)

		total_debits = total_credits = 0
		debit_transactions = credit_transactions = 0

		for transaction in final_transactions:
			withdrawal = transaction.get("withdrawal", 0) or 0
			deposit = transaction.get("deposit", 0) or 0
			if withdrawal > 0:
				total_debits += withdrawal
				debit_transactions += 1
			if deposit > 0:
				total_credits += deposit
				credit_transactions += 1

		self.total_debits = total_debits
		self.total_credits = total_credits
		self.total_debit_transactions = debit_transactions
		self.total_credit_transactions = credit_transactions
		self.start_date, self.end_date, self.closing_balance = get_statement_period(
			final_transactions, "%Y-%m-%d"
		)

		return final_transactions

	def apply_pdf_tables(self, tables: list[dict]):
		"""
		Persist the user's per-table edits (column mapping, include/exclude) and
		recompute the summary so the preview stays in sync.
		"""
		self.pdf_tables = json.dumps(tables)
		self.set_pdf_summary(tables)
		self.save()

	@frappe.whitelist(methods=["POST"])
	def insert_transactions(self):
		if self.status == "Completed":
			return

		company, account, is_company_account, disabled = frappe.get_value(
			"Bank Account", self.bank_account, ["company", "account", "is_company_account", "disabled"]
		)
		if not is_company_account:
			frappe.throw(
				_("The bank account is not a company account. Please select a company account"),
				title=_("Invalid Bank Account"),
			)

		if disabled:
			frappe.throw(
				_("The bank account is disabled. Please enable it"), title=_("Disabled Bank Account")
			)

		currency = frappe.get_value("Account", account, "account_currency")

		progress = 0

		if self.is_pdf():
			final_transactions = self.get_pdf_final_transactions()
		else:
			raw_data = self.get_data()
			transaction_rows, _starting_index, _ending_index = self.get_transaction_rows(raw_data)
			final_transactions = self.get_final_transactions(transaction_rows=transaction_rows)

		final_rows = final_transactions
		# rows of an overlapping statement that are already imported, known by their reference
		already_imported = get_imported_transactions(self.bank_account, final_transactions)
		new_transactions = [
			transaction
			for transaction in final_transactions
			if get_transaction_key(transaction) not in already_imported
		]
		skipped = len(final_transactions) - len(new_transactions)
		final_transactions = new_transactions
		total_transactions = len(final_transactions)

		for transaction in final_transactions:
			bank_tx = frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": transaction.get("date"),
					"status": "Unreconciled",
					"bank_account": self.bank_account,
					"withdrawal": transaction.get("withdrawal"),
					"deposit": transaction.get("deposit"),
					"description": transaction.get("description"),
					"reference_number": transaction.get("reference"),
					"transaction_type": transaction.get("transaction_type"),
					"included_fee": abs(get_float_amount(transaction.get("included_fee")) or 0),
					"excluded_fee": abs(get_float_amount(transaction.get("excluded_fee")) or 0),
					"bank_party_name": transaction.get("party_name"),
					"bank_party_account_number": transaction.get("party_account_number"),
					"bank_party_iban": transaction.get("party_iban"),
					"currency": currency,
					"company": company,
				}
			)
			bank_tx.insert()
			bank_tx.submit()
			progress += 1

			frappe.publish_realtime(
				"bank-rec-statement-import-progress",
				{
					"progress": round(progress / total_transactions * 100),
					"current": progress,
					"total": total_transactions,
				},
				doctype="Bank Statement Import Log",
				docname=self.name,
			)

		frappe.publish_realtime(
			"bank-rec-statement-import-progress",
			{
				"progress": 100,
				"current": total_transactions,
				"total": total_transactions,
			},
			doctype="Bank Statement Import Log",
			docname=self.name,
		)

		# the saved closing balance reads 0 when the statement has no balance, so take it from the rows
		_start_date, end_date, closing_balance = get_statement_period(final_rows, "%Y-%m-%d")
		if closing_balance is not None:
			_set_closing_balance_as_per_statement(self.bank_account, end_date, closing_balance)

		if skipped:
			frappe.msgprint(
				_(
					"{0} rows were not imported again: a submitted Bank Transaction with the same date, amount and reference already exists."
				).format(skipped),
				title=_("Rows Already Imported"),
			)

		from erpnext.accounts.doctype.bank_transaction_rule.bank_transaction_rule import run_rule_evaluation

		run_rule_evaluation()

		self.status = "Completed"
		self.save()


def get_statement_period(transactions: list, date_format: str):
	"""Start date, end date and closing balance of the statement rows.

	The closing balance is the balance of the chronologically last row: the first row of the
	last date when the statement lists the newest first. It is None when no row has a balance.
	"""
	dated = []
	for transaction in transactions:
		date = transaction.get("date")
		if not date:
			continue
		dated.append(
			(date if isinstance(date, datetime) else parse_statement_date(date, date_format), transaction)
		)

	if not dated:
		return None, None, None

	start_date = min(date for date, _transaction in dated)
	end_date = max(date for date, _transaction in dated)
	last_day = [transaction for date, transaction in dated if date == end_date]
	newest_first = dated[0][0] > dated[-1][0]
	if dated[0][0] == dated[-1][0]:
		# a statement of one day: the dates do not give the order, the running balance does
		newest_first = is_balance_newest_first(last_day)
	closing_row = last_day[0] if newest_first else last_day[-1]

	return getdate(start_date), getdate(end_date), get_float_amount(closing_row.get("balance"))


def is_balance_newest_first(transactions: list) -> bool:
	"""True when each row's balance is the next row's balance plus this row's amount."""

	def get_amount(row):
		return flt(get_float_amount(row.get("deposit"))) - flt(get_float_amount(row.get("withdrawal")))

	for row, next_row in pairwise(transactions):
		balance, next_balance = (
			get_float_amount(row.get("balance")),
			get_float_amount(next_row.get("balance")),
		)
		if balance is None or next_balance is None:
			continue

		oldest_first = flt(next_balance - balance - get_amount(next_row), 2) == 0
		newest_first = flt(balance - next_balance - get_amount(row), 2) == 0
		if oldest_first != newest_first:
			return newest_first

	return False


def parse_statement_date(date: str, date_format: str) -> datetime:
	try:
		return datetime.strptime(date, date_format)
	except ValueError:
		frappe.throw(
			_("The date {0} in the statement does not match the date format {1} of the other rows.").format(
				frappe.bold(date), frappe.bold(date_format)
			),
			title=_("Invalid Statement Date"),
		)


def get_transaction_key(transaction: dict) -> tuple | None:
	"""Rows are matched to imported transactions only by date, amount and reference."""
	reference = cstr(transaction.get("reference")).strip()
	if not reference:
		return None
	return (
		getdate(transaction.get("date")),
		reference,
		flt(transaction.get("deposit"), 2),
		flt(transaction.get("withdrawal"), 2),
	)


def get_imported_transactions(bank_account: str, transactions: list) -> set:
	keys = {get_transaction_key(transaction) for transaction in transactions} - {None}
	if not keys:
		return set()

	bank_transactions = frappe.get_all(
		"Bank Transaction",
		filters={
			"bank_account": bank_account,
			"docstatus": 1,
			"date": ["between", [min(key[0] for key in keys), max(key[0] for key in keys)]],
			"reference_number": ["in", list({key[1] for key in keys})],
		},
		fields=["date", "reference_number as reference", "deposit", "withdrawal"],
	)
	return {get_transaction_key(transaction) for transaction in bank_transactions} & keys


HEADER_KEYWORDS = [
	"date",
	"amount",
	"description",
	"reference",
	"transaction",
	"type",
	"cr",
	"dr",
	"deposit",
	"withdrawal",
	"balance",
]

STANDARD_VARIABLES = {
	"Date": ["date", "transaction date"],
	"Debit/Credit": [
		"transaction type",
		"cr/dr",
		"dr/cr",
		"debit/credit",
		"credit/debit",
		"debit / credit",
		"credit / debit",
	],
	"Withdrawal": ["withdrawal", "debit", "paid out", "money out"],
	"Deposit": ["deposit", "credit", "paid in", "money in"],
	"Amount": ["amount"],
	"Description": ["description", "particulars", "remarks", "narration", "detail", "reference"],
	"Reference": ["reference", "ref", "tran id", "transaction id", "cheque", "check", "id", "chq"],
	"Balance": ["balance"],
}

# Map of standard column variable -> transaction row field
FIELD_MAP = {
	"Date": "date",
	"Amount": "amount",
	"Withdrawal": "withdrawal",
	"Deposit": "deposit",
	"Balance": "balance",
	"Reference": "reference",
	"Description": "description",
	"Debit/Credit": "debit_credit",
	"Transaction Type": "transaction_type",
	"Included Fee": "included_fee",
	"Excluded Fee": "excluded_fee",
	"Party Name/Account Holder": "party_name",
	"Party Account No.": "party_account_number",
	"Party IBAN": "party_iban",
}


def detect_header_row(data: list[list]) -> tuple[int, int]:
	"""
	Return ``(row_index, score)`` of the most header-like row. ``score`` is the count of
	cells containing a banking keyword - callers can treat a low score as "no header".
	"""
	row_index = 0
	max_valid_columns = 0

	for idx, row in enumerate(data):
		valid_columns = 0
		for cell in row:
			if not cell or not isinstance(cell, str):
				continue
			if any(keyword in cell.lower() for keyword in HEADER_KEYWORDS):
				valid_columns += 1
		if valid_columns > max_valid_columns:
			max_valid_columns = valid_columns
			row_index = idx

	return row_index, max_valid_columns


def detect_column_mapping(header_row: list) -> list[dict]:
	"""
	Given a header row, map each column index to a standard variable, or "Do not import".
	A standard variable can be represented by multiple names; the first match wins.
	"""
	column_mapping: dict[str, int] = {}
	columns = []

	for idx, cell in enumerate(header_row):
		if not cell or not isinstance(cell, str):
			continue

		column = {
			"index": idx,
			"header_text": cell,
			"variable": cell.strip().lower().replace(" ", "_").replace("?", "").replace(".", ""),
			"maps_to": "Do not import",
		}

		header = normalize_header(cell)
		for standard_variable, names in STANDARD_VARIABLES.items():
			if any(header_has_name(header, name) for name in names):
				if column_mapping.get(standard_variable, None) is None:
					column["maps_to"] = standard_variable
					column_mapping[standard_variable] = idx
					break

		columns.append(column)

	return columns


def normalize_header(cell: str) -> str:
	"""Lower case, dots as spaces and no spaces around a slash, so "Dr / Cr" reads as "dr/cr"."""
	header = re.sub(r"\s+", " ", cell.lower().replace(".", " "))
	return re.sub(r"\s*/\s*", "/", header).strip()


def header_has_name(header: str, name: str) -> bool:
	# a short name must be a whole word: "id" is in "Paid In", "ref" is in "Transfer"
	if len(name) <= 3:
		return re.search(rf"(?<![a-z]){re.escape(name)}(?![a-z])", header) is not None
	return name in header


def is_meaningful_mapping(columns: list[dict]) -> bool:
	"""True if at least one column resolves to an actual field (not "Do not import")."""
	return any(col.get("maps_to") and col["maps_to"] != "Do not import" for col in columns)


def guess_column_mapping_by_content(rows: list[list]) -> list[dict]:
	"""
	Best-effort column mapping for tables without a usable header row (common in PDFs).
	Uses cell contents: a mostly-date column -> Date, the widest text column -> Description,
	and a lone numeric column -> Amount. Ambiguous numeric columns (e.g. separate
	withdrawal/deposit/balance) are left for the user to map.
	"""
	num_cols = max((len(row) for row in rows), default=0)
	column_stats = []

	for idx in range(num_cols):
		cells = [row[idx] for row in rows if idx < len(row) and str(row[idx]).strip() != ""]
		count = len(cells)
		if not count:
			column_stats.append({"index": idx, "date_ratio": 0, "num_ratio": 0, "avg_len": 0, "count": 0})
			continue
		date_hits = sum(1 for c in cells if isinstance(c, str) and frappe.utils.guess_date_format(c))
		num_hits = sum(1 for c in cells if get_float_amount(c) is not None)
		avg_len = sum(len(str(c)) for c in cells) / count
		column_stats.append(
			{
				"index": idx,
				"date_ratio": date_hits / count,
				"num_ratio": num_hits / count,
				"avg_len": avg_len,
				"count": count,
			}
		)

	mapping: dict[int, str] = {}
	numeric_cols = []
	date_assigned = False

	for stat in column_stats:
		if stat["count"] == 0:
			continue
		if not date_assigned and stat["date_ratio"] >= 0.6:
			mapping[stat["index"]] = "Date"
			date_assigned = True
		elif stat["num_ratio"] >= 0.6:
			numeric_cols.append(stat["index"])

	# Description: widest non-date, non-numeric text column
	text_cols = [
		s for s in column_stats if s["count"] and s["index"] not in mapping and s["index"] not in numeric_cols
	]
	if text_cols:
		mapping[max(text_cols, key=lambda s: s["avg_len"])["index"]] = "Description"

	# A single numeric column is unambiguously the amount; otherwise leave for the user.
	if len(numeric_cols) == 1:
		mapping[numeric_cols[0]] = "Amount"

	return [
		{
			"index": idx,
			"header_text": "",
			"variable": f"column_{idx}",
			"maps_to": mapping.get(idx, "Do not import"),
		}
		for idx in range(num_cols)
	]


def extract_transaction_rows(data: list[list], column_mapping: dict[str, int], header_index: int):
	"""
	Pure version of the transaction-row detector. ``header_index`` may be -1/None to mean
	"no header row - treat every row as data" (used for headerless PDF tables).

	For each row after the header, validate that the date column holds a date and that at
	least one of amount/withdrawal/deposit is a number. Returns
	``(transaction_rows, starting_index, ending_index)``.
	"""
	if header_index is None:
		header_index = -1

	def cell(row, key):
		idx = column_mapping.get(key)
		if idx is None or idx >= len(row):
			return None
		return row[idx]

	transaction_rows = []
	transaction_starting_index = None
	transaction_ending_index = None

	valid_rows = data[header_index + 1 :]

	for row_index, row in enumerate(valid_rows):
		date = cell(row, "Date")
		amount = cell(row, "Amount")
		withdrawal = cell(row, "Withdrawal")
		deposit = cell(row, "Deposit")

		if not date:
			continue

		if isinstance(date, datetime):
			date = date.strftime("%Y-%m-%d")

		if not isinstance(date, str):
			continue

		if not amount and not withdrawal and not deposit:
			continue

		row_date_format = frappe.utils.guess_date_format(date)
		if not row_date_format:
			continue

		amount = get_float_amount(amount)
		withdrawal = get_float_amount(withdrawal)
		deposit = get_float_amount(deposit)

		if not amount and not withdrawal and not deposit:
			continue

		if transaction_starting_index is None:
			transaction_starting_index = row_index
		transaction_ending_index = row_index

		transaction_row = {"date_format": row_date_format}
		for source_field, target_field in FIELD_MAP.items():
			if source_field in column_mapping:
				transaction_row[target_field] = cell(row, source_field)

		transaction_rows.append(transaction_row)

	base_index = header_index + 1
	if transaction_starting_index is not None:
		transaction_starting_index += base_index
	if transaction_ending_index is not None:
		transaction_ending_index += base_index

	return transaction_rows, transaction_starting_index, transaction_ending_index


def compute_final_transactions(transaction_rows: list, date_format: str, amount_format: str) -> list:
	"""Pure version of the final-transaction builder (date normalized, amount split)."""
	final_transactions = []

	# Which marker does this statement actually write? A statement that only ever says "Cr"
	# is marking the credits as its exceptions, so an unmarked row is a withdrawal; one that
	# only ever says "Dr" means the opposite. With both markers present an unmarked row is
	# genuinely undetermined, so it stays a withdrawal.
	unmarked_is_deposit = False
	if amount_format == 'Amount column has "CR"/"DR" values':
		markers = {get_amount_cr_dr_marker(row.get("amount")) for row in transaction_rows}
		unmarked_is_deposit = markers - {None} == {"dr"}

	def parse_amount(transaction_row: dict):
		if amount_format == "Separate columns for withdrawal and deposit":
			# the column gives the side; "(500)" or "-500" in the withdrawal column is a withdrawal of 500
			return abs(get_float_amount(transaction_row.get("withdrawal")) or 0), abs(
				get_float_amount(transaction_row.get("deposit")) or 0
			)

		if amount_format == 'Amount column has "CR"/"DR" values':
			amount = transaction_row.get("amount")
			marker = get_amount_cr_dr_marker(amount)
			# The marker carries the direction, so the amount's own sign is ignored.
			signed_amount = get_float_amount(amount) or 0

			if marker:
				return (0, abs(signed_amount)) if marker == "cr" else (abs(signed_amount), 0)

			# An unmarked row takes the opposite direction to the marker this statement
			# uses. A negative amount reverses that again (a refund).
			is_deposit = unmarked_is_deposit
			if signed_amount < 0:
				is_deposit = not is_deposit

			return (0, abs(signed_amount)) if is_deposit else (abs(signed_amount), 0)

		# `or 0` below: get_float_amount returns None for an unparseable cell, and a blank
		# transaction-type cell comes through as None. Both used to raise.
		if amount_format == "Amount column has positive/negative values":
			amount = get_float_amount(transaction_row.get("amount", "0")) or 0
			if amount > 0:
				return 0, abs(amount)
			else:
				return abs(amount), 0

		transaction_type = str(transaction_row.get("debit_credit") or "").strip().lower()
		amount = abs(get_float_amount(transaction_row.get("amount", "0")) or 0)

		if amount_format == 'Transaction type column has "CR"/"DR" values':
			# "credit" contains "cr". "debit" does not contain "dr", so it correctly falls
			# through to the withdrawal side.
			return (0, amount) if "cr" in transaction_type else (amount, 0)

		if amount_format == 'Transaction type column has "C"/"D" values':
			return (0, amount) if transaction_type == "c" else (amount, 0)

		if amount_format == 'Transaction type column has "Deposit"/"Withdrawal" values':
			return (0, amount) if "deposit" in transaction_type else (amount, 0)

		return 0, 0

	for transaction in transaction_rows:
		date = transaction.get("date")

		if isinstance(date, datetime):
			date = date.strftime("%Y-%m-%d")
		else:
			date = parse_statement_date(date, date_format).strftime("%Y-%m-%d")

		withdrawal, deposit = parse_amount(transaction)
		final_transactions.append(
			{
				**transaction,
				"date": date,
				"withdrawal": withdrawal,
				"deposit": deposit,
			}
		)

	return final_transactions


def build_table_transactions(table: dict):
	"""
	Run the per-table detection pipeline on a single PDF table dict and return
	``(final_transactions, date_format, amount_format)``. A table whose mapping has no Date
	column (e.g. an ad or summary block) naturally yields zero transactions.
	"""
	column_mapping: dict[str, int] = {}
	for column in table.get("column_mapping", []):
		if column.get("maps_to") and column["maps_to"] != "Do not import":
			column_mapping[column["maps_to"]] = column["index"]

	transaction_rows, _start, _end = extract_transaction_rows(
		table.get("rows", []), column_mapping, table.get("header_index")
	)
	date_format, amount_format = get_file_properties(transaction_rows)
	final_transactions = compute_final_transactions(transaction_rows, date_format, amount_format)
	return final_transactions, date_format, amount_format


def should_include_table(table: dict, final_transactions: list) -> bool:
	"""
	Whether a freshly extracted PDF table should START as included - only the default state
	of the checkbox, which the user can change afterwards.

	It must have yielded transactions, and it must have a Description column mapped. A
	transaction table always carries a narration; the summary boxes printed around it -
	payment due, credit limit, reward points - are dates and figures only. Otherwise the
	HDFC credit-card "Payment Due Date / Total Dues / Minimum Amount Due" box parses as one
	transaction and imports a phantom row.

	A description is NOT needed to import (it is not mandatory on Bank Transaction), so a
	bank that omits narration still works - its table just starts unticked.
	"""
	if not final_transactions:
		return False

	return any(column.get("maps_to") == "Description" for column in table.get("column_mapping", []))


def _clean_cell(cell) -> str:
	"""Normalize a pdfplumber cell: None -> '', collapse wrapped newlines, strip."""
	if cell is None:
		return ""
	return str(cell).replace("\n", " ").strip()


def extract_pdf_tables(content: bytes, password: str | None = None) -> list[dict]:
	"""
	Extract tables from a PDF, kept SEPARATE (never merged), each with its page, table index,
	bounding box and page dimensions. Raises a recognizable error for encrypted PDFs without
	a valid password, and for PDFs where no tables can be detected (e.g. scanned/image PDFs).
	"""
	try:
		import pdfplumber
	except ImportError:
		frappe.throw(
			_("PDF statement support requires the 'pdfplumber' library to be installed."),
			title=_("Missing Dependency"),
		)

	from pypdf import PdfReader

	reader = PdfReader(io.BytesIO(content))
	if reader.is_encrypted:
		# Try opening the PDF with a password - if no password is provided, try with a blank password
		if not password:
			password = ""
		if not reader.decrypt(password):
			frappe.throw(
				_(
					"This PDF is password protected. Please set the correct statement password on the"
					" Bank Account and try again."
				),
				title=_("Password Required"),
			)

	text_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}
	tables = []

	with pdfplumber.open(io.BytesIO(content), password=password or "") as pdf:
		for page_number, page in enumerate(pdf.pages, start=1):
			found_tables = page.find_tables()
			if not found_tables:
				found_tables = page.find_tables(table_settings=text_settings)

			for table_index, table in enumerate(found_tables):
				rows = [[_clean_cell(c) for c in row] for row in (table.extract() or [])]
				rows = [row for row in rows if any(cell != "" for cell in row)]
				if not rows:
					continue

				tables.append(
					{
						"page": page_number,
						"table_index": table_index,
						"bbox": [round(float(v), 2) for v in table.bbox],
						"page_width": round(float(page.width), 2),
						"page_height": round(float(page.height), 2),
						"rows": rows,
					}
				)

	if not tables:
		frappe.throw(
			_(
				"Could not detect any tables in this PDF. It may be a scanned or image-based"
				" statement, which is not supported (no OCR)."
			),
			title=_("No Tables Detected"),
		)

	return tables


def extract_table_in_bbox(
	content: bytes, password: str | None, page_number: int, bbox: list[float]
) -> list[list[str]]:
	"""
	Re-extract a single table from a user-adjusted region (PDF points, top-left origin) on a
	given 1-based page. The bbox is clamped to the page bounds before cropping.
	"""
	import pdfplumber

	text_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}

	with pdfplumber.open(io.BytesIO(content), password=password or "") as pdf:
		page = pdf.pages[page_number - 1]

		x0 = max(0, min(float(bbox[0]), page.width))
		top = max(0, min(float(bbox[1]), page.height))
		x1 = max(x0 + 1, min(float(bbox[2]), page.width))
		bottom = max(top + 1, min(float(bbox[3]), page.height))

		cropped = page.crop((x0, top, x1, bottom))
		table = cropped.extract_table() or cropped.extract_table(table_settings=text_settings)

	rows = [[_clean_cell(cell) for cell in row] for row in (table or [])]
	return [row for row in rows if any(cell != "" for cell in row)]


def render_pdf_pages(
	content: bytes, password: str | None, pages: set[int], resolution: int = 150
) -> dict[int, tuple[bytes, float]]:
	"""
	Rasterize the requested (1-based) pages to PNG bytes. Returns
	``{page_number: (png_bytes, render_scale)}`` where ``render_scale`` is pixels per PDF point.
	"""
	import pdfplumber

	images = {}
	with pdfplumber.open(io.BytesIO(content), password=password or "") as pdf:
		for page_number, page in enumerate(pdf.pages, start=1):
			if page_number not in pages:
				continue
			page_image = page.to_image(resolution=resolution)
			buffer = io.BytesIO()
			page_image.original.save(buffer, format="PNG")
			images[page_number] = (buffer.getvalue(), round(resolution / 72.0, 4))
	return images


# The number in an amount cell: a dot right after a letter belongs to "Rs." or "Cr.", not to the number.
AMOUNT_NUMBER_PATTERN = re.compile(r"(?<![a-zA-Z])\.?\d[\d,.'\s]*")
MINUS_SIGNS = ("-", "\u2212")


def get_float_amount(amount):
	if not amount:
		return None

	if isinstance(amount, str):
		return parse_amount_text(amount)
	elif isinstance(amount, int):
		amount = float(amount)
	else:
		try:
			amount = float(amount)
		except ValueError:
			return None

	return amount


def parse_amount_text(text: str) -> float | None:
	"""Read "Rs. 1,000.00 Cr", "(500.00)", "300.00-", "1.234,56" or "-1,000.34 INR" as a number.

	Parentheses and a leading or trailing minus make it negative. When a comma and a dot both
	appear, the last one is the decimal separator; a single comma followed by other than three
	digits is a decimal comma.
	"""
	match = AMOUNT_NUMBER_PATTERN.search(text)
	if not match:
		return None

	before, after = text[: match.start()], text[match.end() :].strip()
	negative = (
		any(sign in before for sign in MINUS_SIGNS)
		or after.startswith(MINUS_SIGNS)
		or ("(" in before and after.startswith(")"))
	)

	number = re.sub(r"[\s']", "", match.group()).rstrip(".,")
	if "," in number and "." in number:
		decimal, thousands = (",", ".") if number.rfind(",") > number.rfind(".") else (".", ",")
		number = number.replace(thousands, "").replace(decimal, ".")
	elif "," in number:
		whole, _sep, fraction = number.rpartition(",")
		is_decimal_comma = number.count(",") == 1 and len(fraction) != 3
		number = f"{whole}.{fraction}" if is_decimal_comma else number.replace(",", "")
	elif number.count(".") > 1:
		number = number.replace(".", "")

	try:
		amount = float(number)
	except ValueError:
		return None

	return -amount if negative else amount


# A "CR"/"DR" marker on the amount itself, at either end: "2,378.00Cr", "Cr 100",
# "INR 50.90 Cr.", "DR 1,234.50".
# `(?![a-zA-Z])` rather than `\b` on the leading form: there is no word boundary between
# the "r" of "Cr100" and the digit, but there IS one inside "CREDIT" and "DRAFT".
AMOUNT_CR_DR_PATTERN = re.compile(r"^\s*(cr|dr)(?![a-zA-Z])\.?|(?:^|[\s\d.)])(cr|dr)\b\.?\s*$", re.IGNORECASE)


def get_amount_cr_dr_marker(amount) -> str | None:
	"""
	Return "cr" or "dr" if the amount cell carries a direction marker of its own, else None.

	What is left after removing the marker has to look like an amount - it must hold a digit
	and at most a short currency token - so that text which merely starts or ends with the
	letters is not read as a marker. That guard is what separates "Cr 100" from a
	description that bled into the amount column, like "Dr Smith Clinic 500".
	"""
	if not isinstance(amount, str):
		return None

	match = AMOUNT_CR_DR_PATTERN.search(amount)
	if not match:
		return None

	# Only the marker itself is removed - the surrounding character the pattern needed to
	# anchor on (a digit, say) stays part of the remainder.
	group = 1 if match.group(1) else 2
	start, end = match.span(group)
	remainder = amount[:start] + amount[end:]

	if not any(char.isdigit() for char in remainder):
		return None
	if sum(char.isalpha() for char in remainder) > 3:
		return None

	return match.group(group).lower()


def get_file_properties(transactions: list):
	"""
	From the transaction rows, try to figure out the following:
	1. Most common date format
	2. Amount format - does it contain "CR/Dr" text or is it in a separate column (maybe transaction type?). Amount could also be positive and negative.
	"""

	date_format_frequency = {
		"%d/%m/%Y": 0,
	}

	amount_format_frequency = {
		"Separate columns for withdrawal and deposit": 0,
		'Amount column has "CR"/"DR" values': 0,
		"Amount column has positive/negative values": 0,
		'Transaction type column has "CR"/"DR" values': 0,
		'Transaction type column has "Deposit"/"Withdrawal" values': 0,
		'Transaction type column has "C"/"D" values': 0,
	}

	amount_column_has_cr_dr = False

	for transaction in transactions:
		date_format = transaction.get("date_format")

		if date_format:
			date_format_frequency[date_format] = date_format_frequency.get(date_format, 0) + 1

		# Check if there's an amount column
		# If there's a separate column for withdrawal and deposit, we can skip this
		if transaction.get("withdrawal", None) or transaction.get("deposit", None):
			amount_format_frequency["Separate columns for withdrawal and deposit"] += 1
			continue

		amount = transaction.get("amount", None)

		if not amount:
			continue

		debit_credit = str(transaction.get("debit_credit") or "").strip().lower()

		# One vote per row, most specific signal first. Order matters: "withdrawal" contains
		# "dr", so it must be matched before the loose cr/dr check or a Deposit/Withdrawal
		# column reads as CR/DR. "debit" needs listing because, unlike "credit", it does not
		# contain "dr". The final else means every row votes, even an unrecognised type.
		if get_amount_cr_dr_marker(amount):
			amount_column_has_cr_dr = True
			amount_format_frequency['Amount column has "CR"/"DR" values'] += 1
		elif "deposit" in debit_credit or "withdrawal" in debit_credit:
			amount_format_frequency['Transaction type column has "Deposit"/"Withdrawal" values'] += 1
		elif debit_credit in ("c", "d"):
			amount_format_frequency['Transaction type column has "C"/"D" values'] += 1
		elif any(token in debit_credit for token in ("cr", "dr", "debit")):
			amount_format_frequency['Transaction type column has "CR"/"DR" values'] += 1
		else:
			# Nothing said which direction this is, so assume the amount carries the sign.
			amount_format_frequency["Amount column has positive/negative values"] += 1

	most_common_date_format = pick_date_format(transactions, date_format_frequency)
	most_common_amount_format = max(amount_format_frequency, key=amount_format_frequency.get)

	# With no votes at all (no rows, or every amount blank) max() would return whichever key
	# happens to be first in the dict. Say what we mean instead.
	if not amount_format_frequency[most_common_amount_format]:
		most_common_amount_format = "Amount column has positive/negative values"

	# A CR/DR amount column is proved by a single marker, not by a majority: both formats
	# describe the same column, and an unmarked row is only the default direction, not
	# evidence against the notation. Statements mark just the exceptions - one HDFC
	# credit-card page has 18 rows and a single "50.90Cr".
	if amount_column_has_cr_dr and most_common_amount_format == "Amount column has positive/negative values":
		most_common_amount_format = 'Amount column has "CR"/"DR" values'

	return most_common_date_format, most_common_amount_format


def pick_date_format(transactions: list, date_format_frequency: dict) -> str:
	"""The most common date format that reads every row.

	Each row votes for the first format that reads it, and that is day-first for a date like
	03/05/2026. A statement with a day after the 12th shows its order; when every row can be read
	both ways, the system date format decides.
	"""
	candidates = sorted(date_format_frequency, key=date_format_frequency.get, reverse=True)
	candidates += [swap_day_month(date_format) for date_format in candidates]
	candidates = list(dict.fromkeys(candidates))

	dates = [
		transaction.get("date") for transaction in transactions if isinstance(transaction.get("date"), str)
	]
	readable = [
		date_format for date_format in candidates if all(reads_date(date, date_format) for date in dates)
	]
	if not readable:
		return candidates[0]

	date_format = readable[0]
	swapped = swap_day_month(date_format)
	if swapped in readable and is_month_first(date_format) != system_is_month_first():
		return swapped
	return date_format


def swap_day_month(date_format: str) -> str:
	"""%d/%m/%Y <-> %m/%d/%Y. A format that starts with the year is never read the other way."""
	day, month = date_format.find("%d"), date_format.find("%m")
	year = max(date_format.find("%Y"), date_format.find("%y"))
	if day < 0 or month < 0 or year < max(day, month):
		return date_format
	return date_format.replace("%d", "%_").replace("%m", "%d").replace("%_", "%m")


def is_month_first(date_format: str) -> bool:
	return date_format.find("%m") < date_format.find("%d")


def system_is_month_first() -> bool:
	return cstr(frappe.get_system_settings("date_format")).startswith("mm")


def reads_date(date: str, date_format: str) -> bool:
	try:
		datetime.strptime(date, date_format)
	except ValueError:
		return False
	return True


@frappe.whitelist(methods=["GET"])
def get_statement_details(statement_import_id: str):
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)

	doc.check_permission()

	# Get the final transactions and check for conflicts

	char_map = {
		"%d": "DD",
		"%m": "MM",
		"%Y": "YYYY",
		"%y": "YY",
		"%b": "MMM",
		"%B": "MMMM",
		"%H": "HH",
		"%M": "mm",
		"%S": "ss",
	}
	formatted_date_format = doc.detected_date_format

	for char, replacement in char_map.items():
		formatted_date_format = formatted_date_format.replace(char, replacement)

	conflicting_transactions = check_for_conflicts(doc.bank_account, doc.start_date, doc.end_date)

	if doc.is_pdf():
		# PDF: the per-table data lives in `pdf_tables`; transactions are the union of
		# all included tables. `raw_data` is unused by the PDF frontend.
		pdf_tables = doc.get_pdf_tables()
		final_transactions = doc.get_pdf_final_transactions()
		return {
			"doc": doc,
			"date_format": formatted_date_format,
			"conflicting_transactions": conflicting_transactions,
			"final_transactions": final_transactions,
			"raw_data": [],
			"pdf_tables": pdf_tables,
		}

	raw_data = doc.get_data()

	transaction_rows, _starting_index, _ending_index = doc.get_transaction_rows(raw_data)

	final_transactions = doc.get_final_transactions(transaction_rows=transaction_rows)

	return {
		"doc": doc,
		"date_format": formatted_date_format,
		"conflicting_transactions": conflicting_transactions,
		"final_transactions": final_transactions,
		"raw_data": raw_data,
	}


@frappe.whitelist(methods=["POST"])
def update_pdf_tables(statement_import_id: str, tables: list | str):
	"""
	Persist the user's per-table edits (column mapping, include/exclude flags) for a PDF
	statement and return the refreshed statement details (so the preview stays in sync).
	"""
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)
	doc.check_permission("write")

	if doc.status == "Completed":
		frappe.throw(_("This statement has already been imported."), title=_("Already Imported"))

	tables = frappe.parse_json(tables)

	doc.apply_pdf_tables(tables)

	return get_statement_details(statement_import_id)


@frappe.whitelist(methods=["POST"])
def reextract_pdf_table(statement_import_id: str, page: int, table_index: int, bbox: list | str):
	"""
	Re-extract one PDF table's rows from a user-adjusted bounding box and refresh the preview.
	The user's column mapping is preserved when the column count is unchanged; otherwise the
	table is re-mapped automatically.
	"""
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)
	doc.check_permission("write")

	if doc.status == "Completed":
		frappe.throw(_("This statement has already been imported."), title=_("Already Imported"))

	bbox = frappe.parse_json(bbox)

	page = int(page)
	table_index = int(table_index)

	content = doc.get_file_doc().get_content()
	password = doc.get_statement_password()
	rows = extract_table_in_bbox(content, password, page, [float(v) for v in bbox])

	tables = doc.get_pdf_tables()
	for table in tables:
		if table["page"] == page and table["table_index"] == table_index:
			old_columns = max((len(row) for row in table.get("rows", [])), default=0)
			new_columns = max((len(row) for row in rows), default=0)

			table["rows"] = rows
			table["bbox"] = [round(float(v), 2) for v in bbox]

			# Keep the user's mapping if the shape is unchanged; otherwise re-detect.
			if new_columns != old_columns or not table.get("column_mapping"):
				header_index, score = detect_header_row(rows)
				if score >= 2:
					table["header_index"] = header_index
					table["column_mapping"] = detect_column_mapping(rows[header_index])
				else:
					table["header_index"] = None
					table["column_mapping"] = guess_column_mapping_by_content(rows)

			_finals, table["date_format"], table["amount_format"] = build_table_transactions(table)
			break

	doc.apply_pdf_tables(tables)

	return get_statement_details(statement_import_id)


@frappe.whitelist(methods=["POST"])
def set_pdf_table_header(statement_import_id: str, page: int, table_index: int, header_index: int):
	"""
	Set (or clear) the header row of a PDF table and re-derive its column mapping.

	A ``header_index`` of -1 means the table has NO header row: every row is treated as data
	and the mapping is guessed from the column contents. Otherwise the given row is the header
	and the mapping is derived from its labels.
	"""
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)
	doc.check_permission("write")

	if doc.status == "Completed":
		frappe.throw(_("This statement has already been imported."), title=_("Already Imported"))

	page = int(page)
	table_index = int(table_index)
	header_index = int(header_index)

	tables = doc.get_pdf_tables()
	for table in tables:
		if table["page"] == page and table["table_index"] == table_index:
			rows = table.get("rows", [])
			# Preserve the existing mapping; only re-derive when the chosen header row
			# resolves to a meaningful mapping. Clearing the header keeps the mapping.
			if 0 <= header_index < len(rows):
				table["header_index"] = header_index
				candidate = detect_column_mapping(rows[header_index])
				if is_meaningful_mapping(candidate):
					table["column_mapping"] = candidate
			else:
				table["header_index"] = None

			_finals, table["date_format"], table["amount_format"] = build_table_transactions(table)
			break

	doc.apply_pdf_tables(tables)

	return get_statement_details(statement_import_id)


@frappe.whitelist(methods=["POST"])
def update_column_mapping(statement_import_id: str, column_mapping: list | str):
	"""Persist a user-overridden column mapping for a tabular (CSV/XLSX) statement."""
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)

	if doc.status == "Completed":
		frappe.throw(_("This statement has already been imported."), title=_("Already Imported"))

	column_mapping = frappe.parse_json(column_mapping)

	doc.apply_column_mapping(column_mapping)
	doc.save()

	return get_statement_details(statement_import_id)


@frappe.whitelist(methods=["POST"])
def set_header_index(statement_import_id: str, header_index: int):
	"""
	Set (or clear, with -1) the header row of a tabular statement and re-derive its mapping.
	"""
	doc = frappe.get_doc("Bank Statement Import Log", statement_import_id)

	if doc.status == "Completed":
		frappe.throw(_("This statement has already been imported."), title=_("Already Imported"))

	doc.apply_header_index(int(header_index))
	doc.save()

	return get_statement_details(statement_import_id)


def check_for_conflicts(bank_account: str, start_date: str, end_date: str):
	"""
	Given a bank account, start date and end date, check if there are any conflicts with existing bank transactions
	"""
	if not start_date or not end_date:
		return []

	conflicts = frappe.get_all(
		"Bank Transaction",
		filters={
			"bank_account": bank_account,
			"date": ["between", [start_date, end_date]],
			"docstatus": 1,
		},
		fields=["name", "date", "withdrawal", "deposit", "description", "reference_number", "currency"],
		order_by="date",
	)

	return conflicts
