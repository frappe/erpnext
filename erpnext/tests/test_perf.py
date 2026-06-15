import frappe

from erpnext.tests.utils import ERPNextTestSuite

INDEXED_FIELDS = {
	"Bin": ["item_code"],
	"GL Entry": ["voucher_no", "posting_date", "company", "party"],
	"Purchase Order Item": ["item_code"],
}


def has_leading_column_index(table_name: str, fieldname: str) -> bool:
	"""Return True if ``fieldname`` is the leading column of any index on ``table_name``.

	These fields are not explicitly indexed on their own -- they're the prefix (leading
	column) of some, often composite, index (e.g. Bin's unique ``(item_code, warehouse)``).
	``frappe.db.get_column_index`` only matches single-column indexes, so it can't be used
	here. This mirrors the original MariaDB ``SHOW INDEX ... AND Seq_in_index = 1`` check
	while staying portable to postgres.
	"""
	if frappe.db.db_type == "postgres":
		return bool(
			frappe.db.sql(
				"""
				SELECT 1
				FROM pg_index i
				JOIN pg_class tc ON tc.oid = i.indrelid
				JOIN pg_namespace n ON n.oid = tc.relnamespace
				JOIN pg_attribute a ON a.attrelid = tc.oid AND a.attnum = i.indkey[0]
				WHERE tc.relname = %(table_name)s
					AND n.nspname = current_schema()
					AND a.attname = %(fieldname)s
				LIMIT 1
				""",
				{"table_name": table_name, "fieldname": fieldname},
			)
		)

	return bool(
		frappe.db.sql(
			f"""SHOW INDEX FROM `{table_name}`
				WHERE Column_name = %s AND Seq_in_index = 1""",
			fieldname,
		)
	)


class TestPerformance(ERPNextTestSuite):
	def test_ensure_indexes(self):
		# These fields are not explicitly indexed BUT they are prefix in some
		# other composite index. If those are removed this test should be
		# updated accordingly.
		for doctype, fields in INDEXED_FIELDS.items():
			for field in fields:
				self.assertTrue(
					has_leading_column_index(f"tab{doctype}", field),
					msg=f"Expected an index with {field} as the leading column on {doctype}",
				)
