# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

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
		data = self.get_data()

		self.set_file_properties(data)

	def set_file_properties(self, raw_data: list[list]):
		self.set_header_row_index(raw_data)

		self.set_column_mapping(raw_data)

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

	def get_data(self):
		"""
		Extract the data from the attached file
		"""

		file_doc = frappe.get_doc("File", {"file_url": self.file})

		parts = file_doc.get_extension()
		extension = parts[1]
		content = file_doc.get_content()

		if extension.lower() not in (".csv", ".xlsx", ".xls"):
			frappe.throw(
				_("Import template should be of type .csv, .xlsx or .xls"), title=_("Invalid File Type")
			)

		if extension.lower() == ".csv":
			data = read_csv_content(content)
		elif extension.lower() == ".xlsx":
			data = read_xlsx_file_from_attached_file(fcontent=content)
		elif extension.lower() == ".xls":
			data = read_xls_file_from_attached_file(content)

		return data

	def set_header_row_index(self, data: list[list[str]]):
		"""
		Given the data, try to get the row index of the header row.
		"""

		row_index = 0
		max_valid_columns = 0

		# Loop over rows and find the first row that has the most number of "valid" column headers
		# Valid columns is based on keywords present in each cell

		for idx, row in enumerate(data):
			valid_columns = 0
			for cell in row:
				if not cell:
					continue

				# If cell is a string, then we need to check if it contains any of the keywords
				if not isinstance(cell, str):
					continue

				if any(
					keyword in cell.lower()
					for keyword in [
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
				):
					valid_columns += 1
			if valid_columns > max_valid_columns:
				max_valid_columns = valid_columns
				row_index = idx

		self.detected_header_index = row_index

	def set_column_mapping(self, data: list[list[str]]):
		"""
		Given the header row, try to map each column index to a standard variable, or set it to "Do not import"
		"""

		header_row = data[self.detected_header_index]

		standard_variables = {
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

		# A standard variable can be represented by multiple names

		column_mapping = {}

		# Loop over all columns and check if they contain any of the standard variable names
		# If not, we do not import it
		# If they do, we map the column index to the standard variable

		columns = []

		for idx, cell in enumerate(header_row):
			if not cell:
				continue

			if not isinstance(cell, str):
				continue

			column = {
				"index": idx,
				"header_text": cell,
				"variable": cell.strip().lower().replace(" ", "_").replace("?", "").replace(".", ""),
				"maps_to": "Do not import",
			}

			for standard_variable, names in standard_variables.items():
				if any(name in cell.lower().replace(".", "") for name in names):
					if column_mapping.get(standard_variable, None) is None:
						column["maps_to"] = standard_variable

						column_mapping[standard_variable] = idx

						break

			columns.append(column)

		self.column_mapping = []

		for col in columns:
			self.append(
				"column_mapping",
				{
					"header_text": col["header_text"],
					"variable": col["variable"],
					"maps_to": col["maps_to"],
					"index": col["index"],
				},
			)

	def get_transaction_rows(self, data: list[list[str]]):
		"""
		Given the data, header index and column mapping, try to get the transaction rows

		For each row after the header row, check if the data makes sense - date column should have a date,
		amount column should be a number after removing any special charatcers, spaces and "CR/DR" text.
		Balance column should be a number after removing any special charatcers, spaces and "CR/DR" text.
		"""

		column_mapping: dict[str, int] = {}
		for column in self.column_mapping:
			if column.maps_to != "Do not import":
				column_mapping[column.maps_to] = column.index

		transaction_rows = []

		transaction_starting_index = None
		transaction_ending_index = None

		valid_rows = data[self.detected_header_index + 1 :]

		column_map_keys = column_mapping.keys()

		for row_index, row in enumerate(valid_rows):
			date = row[column_mapping["Date"]] if "Date" in column_map_keys else None
			amount = row[column_mapping["Amount"]] if "Amount" in column_map_keys else None
			withdrawal = row[column_mapping["Withdrawal"]] if "Withdrawal" in column_map_keys else None
			deposit = row[column_mapping["Deposit"]] if "Deposit" in column_map_keys else None
			balance = row[column_mapping["Balance"]] if "Balance" in column_map_keys else None

			if not date:
				continue

			if isinstance(date, datetime):
				date = date.strftime("%Y-%m-%d")

			if not isinstance(date, str):
				continue

			if not amount and not withdrawal and not deposit:
				continue

			# Check if date column is a valid date
			row_date_format = frappe.utils.guess_date_format(date)

			if not row_date_format:
				continue

			# Check if either the amount, withdrawal or deposit column is a valid number
			amount = get_float_amount(amount)
			withdrawal = get_float_amount(withdrawal)
			deposit = get_float_amount(deposit)
			balance = get_float_amount(balance)

			if not amount and not withdrawal and not deposit:
				continue

			if transaction_starting_index is None:
				transaction_starting_index = row_index

			transaction_ending_index = row_index

			transaction_row = {
				"date_format": row_date_format,
			}

			# Populate the raw transaction row as is - without any formatting

			field_map = {
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

			for source_field, target_field in field_map.items():
				if source_field in column_map_keys:
					transaction_row[target_field] = row[column_mapping[source_field]]

			transaction_rows.append(transaction_row)

		base_index = self.detected_header_index + 1

		if transaction_starting_index is not None:
			transaction_starting_index += base_index

		if transaction_ending_index is not None:
			transaction_ending_index += base_index

		return transaction_rows, transaction_starting_index, transaction_ending_index

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

		date_format = self.detected_date_format
		amount_format = self.detected_amount_format

		final_transactions = []

		def parse_amount(transaction_row: dict):
			"""
			Given a transaction row, try to parse the amount - returns tuple of (withdrawal, deposit)
			"""

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

		raw_data = self.get_data()
		transaction_rows, transaction_starting_index, transaction_ending_index = self.get_transaction_rows(
			raw_data
		)

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

	raw_data = doc.get_data()

	transaction_rows, transaction_starting_index, transaction_ending_index = doc.get_transaction_rows(
		raw_data
	)

	final_transactions = doc.get_final_transactions(transaction_rows=transaction_rows)

	return {
		"doc": doc,
		"date_format": formatted_date_format,
		"conflicting_transactions": conflicting_transactions,
		"final_transactions": final_transactions,
		"raw_data": raw_data,
	}


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
