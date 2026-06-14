import frappe

from erpnext.tests.utils import ERPNextTestSuite

INDEXED_FIELDS = {
	"Bin": ["item_code"],
	"GL Entry": ["voucher_no", "posting_date", "company", "party"],
	"Purchase Order Item": ["item_code"],
}


class TestPerformance(ERPNextTestSuite):
	def test_ensure_indexes(self):
		# Each of these fields has its own single-column index (search_index / Link).
		# If those are removed this test should be updated accordingly.
		for doctype, fields in INDEXED_FIELDS.items():
			for field in fields:
				self.assertTrue(
					frappe.db.get_column_index(f"tab{doctype}", field, unique=False),
					msg=f"Expected an index with {field} as the leading column on {doctype}",
				)
