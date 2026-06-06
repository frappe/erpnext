# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import io
import json
import re
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils.csvutils import read_csv_content
from frappe.utils.xlsxutils import (
	read_xls_file_from_attached_file,
	read_xlsx_file_from_attached_file,
)

from erpnext.accounts.doctype.bank_account.bank_account import set_closing_balance_as_per_statement


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

		statement_start_date = None
		statement_end_date = None
		closing_balance = None

		date_format = self.detected_date_format

		for transaction in transactions:
			date = transaction.get("date")
			if not date:
				continue

			if isinstance(date, datetime):
				tx_date = date
			else:
				tx_date = datetime.strptime(date, date_format)

			if statement_start_date is None or tx_date < statement_start_date:
				statement_start_date = tx_date

			if statement_end_date is None or tx_date >= statement_end_date:
				statement_end_date = tx_date

				closing_balance = transaction.get("balance")

		self.start_date = getdate(statement_start_date)
		self.end_date = getdate(statement_end_date)
		self.closing_balance = get_float_amount(closing_balance)

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
			# Tables with no detectable transactions (ads, summaries, headers) start excluded.
			table["included"] = bool(final_transactions)

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
		start_date = end_date = None
		closing_balance = None

		for transaction in final_transactions:
			withdrawal = transaction.get("withdrawal", 0) or 0
			deposit = transaction.get("deposit", 0) or 0
			if withdrawal > 0:
				total_debits += withdrawal
				debit_transactions += 1
			if deposit > 0:
				total_credits += deposit
				credit_transactions += 1

			date = transaction.get("date")
			if not date:
				continue
			tx_date = getdate(date)
			if start_date is None or tx_date < start_date:
				start_date = tx_date
			if end_date is None or tx_date >= end_date:
				end_date = tx_date
				closing_balance = transaction.get("balance")

		self.total_debits = total_debits
		self.total_credits = total_credits
		self.total_debit_transactions = debit_transactions
		self.total_credit_transactions = credit_transactions
		self.start_date = getdate(start_date) if start_date else None
		self.end_date = getdate(end_date) if end_date else None
		self.closing_balance = get_float_amount(closing_balance)

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
				},
				doctype="Bank Statement Import Log",
				docname=self.name,
			)

		frappe.publish_realtime(
			"bank-rec-statement-import-progress",
			{
				"progress": 100,
				"total": total_transactions,
			},
			doctype="Bank Statement Import Log",
			docname=self.name,
		)

		if self.closing_balance and self.closing_balance > 0 and self.end_date:
			set_closing_balance_as_per_statement(
				self.bank_account, frappe.utils.getdate(self.end_date), self.closing_balance
			)

		from erpnext.accounts.doctype.bank_transaction_rule.bank_transaction_rule import run_rule_evaluation

		run_rule_evaluation()

		self.status = "Completed"
		self.save()


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
	"Withdrawal": ["withdrawal", "debit"],
	"Deposit": ["deposit", "credit"],
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

		for standard_variable, names in STANDARD_VARIABLES.items():
			if any(name in cell.lower().replace(".", "") for name in names):
				if column_mapping.get(standard_variable, None) is None:
					column["maps_to"] = standard_variable
					column_mapping[standard_variable] = idx
					break

		columns.append(column)

	return columns


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

	def parse_amount(transaction_row: dict):
		if amount_format == "Separate columns for withdrawal and deposit":
			return get_float_amount(transaction_row.get("withdrawal")), get_float_amount(
				transaction_row.get("deposit")
			)

		if amount_format == 'Amount column has "CR"/"DR" values':
			amount = transaction_row.get("amount")
			float_amount = get_float_amount(amount)
			if "cr" in amount.lower():
				return 0, float_amount
			else:
				return float_amount, 0

		if amount_format == "Amount column has positive/negative values":
			amount = get_float_amount(transaction_row.get("amount", "0"))
			if amount > 0:
				return 0, abs(amount)
			else:
				return abs(amount), 0

		if amount_format == 'Transaction type column has "CR"/"DR" values':
			transaction_type = transaction_row.get("debit_credit")
			amount = get_float_amount(transaction_row.get("amount", "0"))
			if "cr" in transaction_type.lower():
				return 0, abs(amount)
			else:
				return abs(amount), 0

		if amount_format == 'Transaction type column has "C"/"D" values':
			transaction_type = transaction_row.get("debit_credit")
			amount = get_float_amount(transaction_row.get("amount", "0"))
			if transaction_type.lower().strip() == "c":
				return 0, abs(amount)
			else:
				return abs(amount), 0

		if amount_format == 'Transaction type column has "Deposit"/"Withdrawal" values':
			transaction_type = transaction_row.get("debit_credit")
			amount = get_float_amount(transaction_row.get("amount", "0"))
			if "deposit" in transaction_type.lower():
				return 0, abs(amount)
			else:
				return abs(amount), 0

		return 0, 0

	for transaction in transaction_rows:
		date = transaction.get("date")

		if isinstance(date, datetime):
			date = date.strftime("%Y-%m-%d")
		else:
			date = datetime.strptime(date, date_format).strftime("%Y-%m-%d")

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
	if reader.is_encrypted and (not password or not reader.decrypt(password)):
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


def get_float_amount(amount):
	if not amount:
		return None

	if isinstance(amount, str):
		amount = amount.lower().replace(",", "").replace(" ", "").replace("cr", "").replace("dr", "")
		# Remove any other alphabets and currency symbols - do not remove the minus or decimal sign
		amount = re.sub(r"[^\d.-]", "", amount)
		try:
			amount = float(amount)
		except ValueError:
			return None
	elif isinstance(amount, int):
		amount = float(amount)
	else:
		try:
			amount = float(amount)
		except ValueError:
			return None

	return amount


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

		if isinstance(amount, str) and ("cr" in amount.lower() or "dr" in amount.lower()):
			amount_format_frequency['Amount column has "CR"/"DR" values'] += 1

		# Check if there's a debit_credit column containing "cr"/"dr"
		if transaction.get("debit_credit", None):
			if (
				"cr" in transaction.get("debit_credit", "").lower()
				or "dr" in transaction.get("debit_credit", "").lower()
			):
				amount_format_frequency['Transaction type column has "CR"/"DR" values'] += 1
			elif (
				"deposit" in transaction.get("debit_credit", "").lower()
				or "withdrawal" in transaction.get("debit_credit", "").lower()
			):
				amount_format_frequency['Transaction type column has "Deposit"/"Withdrawal" values'] += 1
			elif (transaction.get("debit_credit", "").lower().strip() == "c") or (
				transaction.get("debit_credit", "").lower().strip() == "d"
			):
				amount_format_frequency['Transaction type column has "C"/"D" values'] += 1

		# Else assume that the amount is expressed as positive/negative value
		else:
			amount_format_frequency["Amount column has positive/negative values"] += 1

	most_common_date_format = max(date_format_frequency, key=date_format_frequency.get)
	most_common_amount_format = max(amount_format_frequency, key=amount_format_frequency.get)

	return most_common_date_format, most_common_amount_format


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

	if isinstance(tables, str):
		tables = json.loads(tables)

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

	if isinstance(bbox, str):
		bbox = json.loads(bbox)

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

	if isinstance(column_mapping, str):
		column_mapping = json.loads(column_mapping)

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
