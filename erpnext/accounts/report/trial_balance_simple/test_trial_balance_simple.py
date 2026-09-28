import frappe
from frappe.desk.query_report import run

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.tests.utils import ERPNextTestSuite


class TestTrialBalanceSimple(ERPNextTestSuite):
	def test_rows_are_split_by_finance_book(self):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "_Test Trial Balance Simple Expense",
				"parent_account": "Indirect Expenses - _TC",
				"company": "_Test Company",
			}
		).insert()
		book_a, book_b = (
			frappe.get_doc({"doctype": "Finance Book", "finance_book_name": name}).insert().name
			for name in ("_Test TB Simple Book A", "_Test TB Simple Book B")
		)

		for finance_book, amount in ((None, 100), (book_a, 30), (book_b, 40)):
			journal_entry = make_journal_entry(account.name, "_Test Bank - _TC", amount, save=False)
			journal_entry.finance_book = finance_book
			journal_entry.insert()
			journal_entry.submit()

		result = run("Trial Balance (Simple)", filters={"company": "_Test Company"})["result"]
		rows = [
			(row["finance_book"], row["debit"])
			for row in result
			if isinstance(row, dict) and row.get("account") == account.name
		]

		self.assertEqual(rows, [("", 100), (book_a, 30), (book_b, 40)])
