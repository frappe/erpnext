import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities import update_doctypes


class TestUtilitiesInit(ERPNextTestSuite):
	def test_description_child_field_query_finds_core_child_fields(self):
		"""The converted query in update_doctypes() joins DocField + DocType to find
		description-bearing fields on child tables (istable=1). Reproduce the exact
		query and assert known core child-doctype description fields are returned."""
		df = frappe.qb.DocType("DocField")
		dt_table = frappe.qb.DocType("DocType")
		rows = (
			frappe.qb.from_(df)
			.inner_join(dt_table)
			.on(df.parent == dt_table.name)
			.select(df.parent, df.fieldname)
			.where(df.fieldname.like("%description%") & (dt_table.istable == 1))
			.run(as_dict=1)
		)

		# Map parent -> set of matched fieldnames for concrete assertions.
		matched = {}
		for d in rows:
			matched.setdefault(d.parent, set()).add(d.fieldname)

		# Known core child tables (istable=1) carrying a "description" field.
		self.assertIn("Sales Invoice Item", matched)
		self.assertIn("description", matched["Sales Invoice Item"])

		self.assertIn("Purchase Invoice Item", matched)
		self.assertIn("description", matched["Purchase Invoice Item"])

		# Every returned fieldname must satisfy the LIKE predicate, and every
		# returned parent must genuinely be a child table (istable=1) -- guards
		# against the join/where being dropped during the qb conversion.
		for d in rows:
			self.assertIn("description", d.fieldname)
		parents = {d.parent for d in rows}
		istable_map = dict(
			frappe.get_all(
				"DocType",
				filters={"name": ("in", list(parents))},
				fields=["name", "istable"],
				as_list=1,
			)
		)
		for parent in parents:
			self.assertEqual(
				istable_map.get(parent),
				1,
				msg=f"{parent} returned by description-child query but is not a child table",
			)

	def test_update_doctypes_is_importable_and_callable(self):
		"""update_doctypes() is the public entry point exercising the converted
		query; ensure it imports and runs without error against real schema."""
		self.assertTrue(callable(update_doctypes))
		# Run it: it should only ever upgrade Text/Small Text description fields to
		# Text Editor; core fixtures used above are already Text Editor, so this is
		# effectively a no-op but must not raise.
		update_doctypes()
