# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import duckdb
import frappe
import pyarrow as pa
from frappe.database.duckdb.database import DuckDBConnection
from frappe.database.duckdb.schema import DuckDBTable
from frappe.utils import today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.general_ledger.general_ledger import _execute_with_duckdb_conn, execute
from erpnext.tests.utils import ERPNextTestSuite

ALLOWED_ACCOUNT = "_Test Bank - _TC"
RESTRICTED_ACCOUNT = "_Test Account Cost for Goods Sold - _TC"
TEST_USER = "test_account_category_permission@example.com"


class TestAccountCategory(ERPNextTestSuite):
	def setUp(self):
		for category, account in (
			("_Test Allowed Category", ALLOWED_ACCOUNT),
			("_Test Restricted Category", RESTRICTED_ACCOUNT),
		):
			if not frappe.db.exists("Account Category", category):
				frappe.get_doc({"doctype": "Account Category", "account_category_name": category}).insert()
			frappe.db.set_value("Account", account, "account_category", category)

		if not frappe.db.exists("User", TEST_USER):
			user = frappe.new_doc("User")
			user.email = TEST_USER
			user.first_name = "Account Category Perm"
			user.append("roles", {"role": "Accounts User"})
			user.save()

		frappe.permissions.add_user_permission("Account Category", "_Test Allowed Category", TEST_USER)
		self.journal_entry = make_journal_entry(RESTRICTED_ACCOUNT, ALLOWED_ACCOUNT, 100, submit=True)

	def test_general_ledger_honours_account_category_user_permission(self):
		filters = self.get_general_ledger_filters()

		self.assertEqual(self.get_general_ledger_accounts(filters), {ALLOWED_ACCOUNT, RESTRICTED_ACCOUNT})

		with self.set_user(TEST_USER):
			self.assertEqual(self.get_general_ledger_accounts(filters), {ALLOWED_ACCOUNT})

	def test_general_ledger_snapshot_honours_account_category_user_permission(self):
		filters = self.get_general_ledger_filters()
		conn = self.get_gl_entry_snapshot()

		self.assertEqual(
			self.get_general_ledger_accounts(filters, conn), {ALLOWED_ACCOUNT, RESTRICTED_ACCOUNT}
		)

		with self.set_user(TEST_USER):
			self.assertEqual(self.get_general_ledger_accounts(filters, conn), {ALLOWED_ACCOUNT})

	def test_gl_entry_list_honours_account_category_user_permission(self):
		with self.set_user(TEST_USER):
			accounts = frappe.get_list(
				"GL Entry", filters={"voucher_no": self.journal_entry.name}, pluck="account"
			)
		self.assertEqual(accounts, [ALLOWED_ACCOUNT])

	def test_gl_entry_document_honours_account_category_user_permission(self):
		gl_entries = {
			entry.account: entry.name
			for entry in frappe.get_all(
				"GL Entry", filters={"voucher_no": self.journal_entry.name}, fields=["name", "account"]
			)
		}

		with self.set_user(TEST_USER):
			self.assertTrue(frappe.has_permission("GL Entry", "read", gl_entries[ALLOWED_ACCOUNT]))
			self.assertFalse(frappe.has_permission("GL Entry", "read", gl_entries[RESTRICTED_ACCOUNT]))

	def test_uncategorised_account_follows_strict_user_permissions(self):
		frappe.db.set_value("Account", RESTRICTED_ACCOUNT, "account_category", None)
		filters = {"voucher_no": self.journal_entry.name}

		frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 0)
		with self.set_user(TEST_USER):
			self.assertEqual(len(frappe.get_list("GL Entry", filters=filters)), 2)

		frappe.db.set_single_value("System Settings", "apply_strict_user_permissions", 1)
		with self.set_user(TEST_USER):
			self.assertEqual(len(frappe.get_list("GL Entry", filters=filters)), 1)

	def get_general_ledger_filters(self):
		return frappe._dict(
			company="_Test Company",
			from_date=today(),
			to_date=today(),
			voucher_no=self.journal_entry.name,
			categorize_by="Categorize by Voucher (Consolidated)",
		)

	def get_gl_entry_snapshot(self):
		table = DuckDBTable("GL Entry")
		rows = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": self.journal_entry.name},
			fields=frappe.get_meta("GL Entry").get_valid_columns(),
		)

		conn = duckdb.connect(":memory:")
		table.sync(conn)
		conn.register("captured", pa.Table.from_pylist(rows, schema=table.get_arrow_schema()))
		conn.execute('INSERT INTO "tabGL Entry" BY NAME SELECT * FROM captured')
		conn.unregister("captured")
		return DuckDBConnection(conn)

	def get_general_ledger_accounts(self, filters, conn=None):
		result = _execute_with_duckdb_conn(filters.copy(), conn) if conn else execute(filters.copy())
		return {row.get("account") for row in result[1] if row.get("gl_entry")}
