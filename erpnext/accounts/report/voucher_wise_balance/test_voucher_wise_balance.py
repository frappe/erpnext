# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.voucher_wise_balance.voucher_wise_balance import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestVoucherWiseBalance(ERPNextTestSuite):
	def run_report(self, **extra):
		filters = frappe._dict(
			{
				"company": "_Test Company",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
			}
		)
		filters.update(extra)
		return execute(filters)[1]

	def test_company_is_mandatory(self):
		self.assertRaises(frappe.ValidationError, execute, frappe._dict(from_date="2026-01-01"))

	def test_same_named_vouchers_of_different_types_reported_separately(self):
		jv = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		other = make_journal_entry(
			"Sales - _TC", "_Test Bank - _TC", 1000, submit=True, posting_date="2026-06-01"
		)
		gle = frappe.qb.DocType("GL Entry")
		frappe.qb.update(gle).set(gle.voucher_type, "Sales Invoice").set(gle.voucher_no, jv.name).where(
			gle.voucher_no == other.name
		).run()
		frappe.db.set_value(
			"GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name, "debit": [">", 0]},
			"debit",
			1500,
		)
		frappe.db.set_value(
			"GL Entry",
			{"voucher_type": "Sales Invoice", "voucher_no": jv.name, "credit": [">", 0]},
			"credit",
			1500,
		)

		rows = {
			(row.voucher_type, row.debit, row.credit)
			for row in self.run_report()
			if row.voucher_no == jv.name
		}
		self.assertEqual(rows, {("Journal Entry", 1500, 1000), ("Sales Invoice", 1000, 1500)})
