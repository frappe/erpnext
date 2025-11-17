import frappe
import unittest
from frappe.utils import today, add_days
import erpnext.accounts.report.bank_clearance_summary.bank_clearance_summary as bcs

class TestBankClearanceSummary(unittest.TestCase):
	def setUp(self):
		self.company = frappe.get_all("Company", limit=1)[0].name if frappe.get_all("Company") else None
		self.account = frappe.get_all("Account", filters={"company": self.company, "is_group": 0}, limit=1)[0].name if self.company else None

	def tearDown(self):
		frappe.db.rollback()

	def test_execute_with_filters_TC_ACC_500(self):
		filters = {
			"account": self.account,
			"from_date": today(),
			"to_date": today(),
		}
		columns, data = bcs.execute(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)

	def test_get_columns_TC_ACC_501(self):
		columns = bcs.get_columns()
		self.assertTrue(any(col.get("fieldname") == "payment_document_type" for col in columns))
		self.assertTrue(any(col.get("fieldname") == "amount" for col in columns))

	def test_get_conditions_TC_ACC_502(self):
		filters = {"from_date": "2024-01-01", "to_date": "2024-01-31"}
		conditions = bcs.get_conditions(filters)
		self.assertIn("posting_date>=", conditions)
		self.assertIn("posting_date<=", conditions)

	def test_get_entries_TC_ACC_503(self):
		filters = {"account": self.account}
		entries = bcs.get_entries(filters)
		self.assertIsInstance(entries, list)

	def test_get_entries_for_bank_clearance_summary_TC_ACC_504(self):
		# Ensure 'account' is not None before running the test
		if not self.account:
			self.skipTest("No account found for the company; skipping test.")
		filters = {"account": self.account, "from_date": today(), "to_date": add_days(today(), 1)}
		entries = bcs.get_entries_for_bank_clearance_summary(filters)
		self.assertIsInstance(entries, list)

if __name__ == "__main__":
	unittest.main()
