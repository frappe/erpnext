import json
import types
import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.bank_transaction import bank_transaction_upload as mod


class TestBankTransactionUpload(FrappeTestCase):
	def setUp(self):
		# ensure we don't leak global upload state between tests
		for attr in ("uploaded_file",):
			if hasattr(frappe, attr):
				delattr(frappe, attr)
		frappe.local.uploaded_file = None
		frappe.local.uploaded_filename = None

	def test_upload_bank_statement_csv_and_xlsx_TC_ACC_371(self):
		"""
		Covers:
		  - CSV branch (read_csv_content)
		  - XLSX branch (read_xlsx_file_from_attached_file)
		Uses the safe 'else' path (frappe.local.*) to avoid the fname bug.
		"""
		# --- CSV branch ---
		# monkeypatch csv reader
		import frappe.utils.csvutils as csvutils
		orig_read_csv = getattr(csvutils, "read_csv_content", None)
		csvutils.read_csv_content = lambda content, *a, **k: [
			["Date", "Amount"],  # header
			["2025-08-26", "1000"],
		]

		try:
			frappe.local.uploaded_file = b"dummy-bytes"
			frappe.local.uploaded_filename = "statement.csv"
			res = mod.upload_bank_statement()
			self.assertEqual(res["columns"], ["Date", "Amount"])
			self.assertEqual(res["data"], [["2025-08-26", "1000"]])
		finally:
			if orig_read_csv:
				csvutils.read_csv_content = orig_read_csv

		# --- XLSX branch ---
		import frappe.utils.xlsxutils as xlsxutils
		orig_read_xlsx = getattr(xlsxutils, "read_xlsx_file_from_attached_file", None)
		xlsxutils.read_xlsx_file_from_attached_file = lambda fcontent=None, **k: [
			["Txn No", "Desc"],  # header
			["T1", "Hello"],
		]

		try:
			frappe.local.uploaded_file = b"dummy-xlsx-bytes"
			frappe.local.uploaded_filename = "statement.xlsx"
			res = mod.upload_bank_statement()
			self.assertEqual(res["columns"], ["Txn No", "Desc"])
			self.assertEqual(res["data"], [["T1", "Hello"]])
		finally:
			if orig_read_xlsx:
				xlsxutils.read_xlsx_file_from_attached_file = orig_read_xlsx

	def test_get_header_mapping_and_create_bank_entries_success_and_error_TC_ACC_372(self):
		"""
		Covers:
		  - get_header_mapping() (with custom get_bank_mapping())
		  - create_bank_entries(): both success and error paths
			* success row parses date & submits
			* error row triggers exception during date parse -> log_error + errors++
		"""
		# columns passed by UI: colIndex is 1-based in the code
		columns = json.dumps([
			{"content": "Date", "colIndex": 1},
			{"content": "Deposit", "colIndex": 2},
			{"content": "Withdrawal", "colIndex": 3},
			{"content": "Description", "colIndex": 4},
		])
		# data: one good row, one bad date to raise in parse_date/getdate
		data = json.dumps([
			["2025-08-26", "1000", None, "Salary"],   # success
			["not-a-date", "0", "100", "ErrorCase"],  # error
		])

		# monkeypatch get_bank_mapping -> avoid DB
		orig_get_bank_mapping = mod.get_bank_mapping
		mod.get_bank_mapping = lambda bank_account: {
			"Date": "date",
			"Deposit": "deposit",
			"Withdrawal": "withdrawal",
			"Description": "description",
		}

		# Verify header mapping itself
		header_map = mod.get_header_mapping(columns, "BA-TEST")
		self.assertEqual(header_map, {"date": 1, "deposit": 2, "withdrawal": 3, "description": 4})

		# monkeypatch frappe.get_doc to return a dummy document that behaves like a Bank Transaction
		created_docs = []

		class DummyBT:
			def __init__(self):
				# fields will be set via .update
				self.date = None
				self.deposit = None
				self.withdrawal = None
				self.description = None
				self.bank_account = None
				self._log_error_called = False

			def update(self, fields: dict):
				for k, v in fields.items():
					setattr(self, k, v)

			def insert(self):
				# simulate insert OK
				created_docs.append(("insert", dict(
					date=self.date, deposit=self.deposit, withdrawal=self.withdrawal, description=self.description
				)))

			def submit(self):
				# simulate submit OK
				created_docs.append(("submit", dict(
					date=self.date, deposit=self.deposit, withdrawal=self.withdrawal, description=self.description
				)))

			def log_error(self, msg):
				# just record it was called
				self._log_error_called = True
				created_docs.append(("log_error", msg))

		orig_get_doc = frappe.get_doc
		frappe.get_doc = lambda *a, **k: DummyBT()

		try:
			out = mod.create_bank_entries(columns, data, bank_account="BA-TEST")
			# 1 success (valid date), 1 error (invalid date parsing)
			self.assertEqual(out["success"], 1)
			self.assertEqual(out["errors"], 1)

			# Ensure our dummy saw both insert/submit AND a log_error
			kinds = [x[0] for x in created_docs]
			self.assertIn("insert", kinds)
			self.assertIn("submit", kinds)
			self.assertIn("log_error", kinds)
		finally:
			mod.get_bank_mapping = orig_get_bank_mapping
			frappe.get_doc = orig_get_doc

	def test_get_bank_mapping_uses_cached_value_and_doc_TC_ACC_373(self):
		"""
		Covers get_bank_mapping() by stubbing:
		  - frappe.get_cached_value("Bank Account", bank_account, "bank")
		  - frappe.get_doc("Bank", bank_name).bank_transaction_mapping rows
		"""
		# monkeypatch get_cached_value
		orig_get_cached_value = frappe.get_cached_value
		frappe.get_cached_value = lambda doctype, name, field: (
			"Test Bank Name" if (doctype == "Bank Account" and field == "bank") else None
		)

		# stub Bank doc with bank_transaction_mapping child rows
		class Row:
			def __init__(self, file_field, bank_transaction_field):
				self.file_field = file_field
				self.bank_transaction_field = bank_transaction_field

		class DummyBankDoc:
			def __init__(self):
				self.bank_transaction_mapping = [
					Row("Date", "date"),
					Row("Amount In", "deposit"),
					Row("Amount Out", "withdrawal"),
				]

		orig_get_doc = frappe.get_doc
		frappe.get_doc = lambda doctype, name: DummyBankDoc()

		try:
			mapping = mod.get_bank_mapping("BA-123")
			self.assertEqual(mapping, {
				"Date": "date",
				"Amount In": "deposit",
				"Amount Out": "withdrawal",
			})
		finally:
			frappe.get_cached_value = orig_get_cached_value
			frappe.get_doc = orig_get_doc
