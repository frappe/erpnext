import frappe

from erpnext.tests.utils import ERPNextTestSuite

INDEXED_FIELDS = {
	"Bin": ["item_code"],
	"GL Entry": ["voucher_no", "posting_date", "company", "party"],
	"Purchase Order Item": ["item_code"],
}


def _is_leading_index_column(doctype: str, field: str) -> bool:
	"""Whether `field` is the first column of some index on the doctype's table.

	`SHOW INDEX` is MySQL-only; on Postgres read the leading key column (indkey[0])
	from the pg_index catalog. Both check the same thing across engines.
	"""
	table = f"tab{doctype}"
	if frappe.db.db_type == "postgres":
		return bool(
			frappe.db.sql(
				"""
				SELECT 1
				FROM pg_index i
				JOIN pg_class t ON t.oid = i.indrelid
				JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]
				WHERE t.relname = %s AND a.attname = %s
				LIMIT 1
				""",
				(table, field),
			)
		)
	# `table` is a trusted constant (from INDEXED_FIELDS); a table identifier can't be a %s
	# placeholder in SHOW INDEX, so the f-string is unavoidable and safe here.
	return bool(
		frappe.db.sql(  # pg-ok: MariaDB-only branch; Postgres is handled above via pg_index
			f"""SHOW INDEX FROM `{table}` WHERE Column_name = %s AND Seq_in_index = 1""",
			(field,),
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
					_is_leading_index_column(doctype, field),
					msg=f"{field} is not the leading column of any index on tab{doctype}",
				)
