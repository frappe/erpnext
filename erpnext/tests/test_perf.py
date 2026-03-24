import frappe

from erpnext.tests.utils import ERPNextTestSuite

INDEXED_FIELDS = {
	"Bin": {"item_code": "unique_item_warehouse"},
	"GL Entry": {
		"voucher_no": "voucher_no",
		"posting_date": "posting_date",
		"company": "company",
		"party": "party",
	},
	"Purchase Order Item": {"item_code": "item_code_warehouse_index"},
}


class TestPerformance(ERPNextTestSuite):
	def test_ensure_indexes(self):
		# These fields are not explicitly indexed BUT they are prefix in some
		# other composite index. If those are removed this test should be
		# updated accordingly.
		for doctype, fields in INDEXED_FIELDS.items():
			for field, index_name in fields.items():
				self.assertTrue(
					frappe.db.has_index(f"tab{doctype}", index_name),
					msg=f"Expected index for {doctype}.{field}",
				)
