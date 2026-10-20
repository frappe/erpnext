import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_split_tree.batch_split_tree import execute
from erpnext.tests.permission_test_utils import as_user, make_company_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestBatchSplitTree(ERPNextTestSuite):
	def test_shared_labels_keep_separate_trees(self):
		roots = []
		children = []
		for _ in range(2):
			item = make_item(properties={"has_batch_no": 1})
			root = frappe.get_doc(doctype="Batch", item=item.name, batch_id="Split-Root").insert()
			receipt = make_stock_entry(
				item_code=item.name, to_warehouse="Stores - _TC", qty=2, rate=10, batch_no=root.name
			)
			child = frappe.get_doc(
				doctype="Batch",
				item=item.name,
				batch_id="Split-Child",
				parent_batch=root.name,
				reference_doctype="Stock Entry",
				reference_name=receipt.name,
			).insert()
			roots.append(root)
			children.append(child)

		for root, child in zip(roots, children, strict=True):
			columns, rows = execute(frappe._dict(batch=root.name))
			self.assertEqual([row.batch_no for row in rows], [root.name, child.name])
			self.assertEqual([row.batch_no_number for row in rows], ["Split-Root", "Split-Child"])
			self.assertEqual([row.indent for row in rows], [0, 1])
			self.assertTrue(all(row.item == root.item for row in rows))
			self.assertTrue(next(column for column in columns if column["fieldname"] == "batch_no")["hidden"])

	def test_item_filter_matches_descendants(self):
		items = [make_item(properties={"has_batch_no": 1}) for index in range(3)]
		root = frappe.get_doc(doctype="Batch", item=items[0].name, batch_id="Raw-Material").insert()
		receipt = make_stock_entry(
			item_code=items[0].name, to_warehouse="Stores - _TC", qty=2, rate=10, batch_no=root.name
		)
		batches = [root]
		for item in items[1:]:
			batches.append(
				frappe.get_doc(
					doctype="Batch",
					item=item.name,
					batch_id="Split-Material",
					parent_batch=batches[-1].name,
					reference_doctype="Stock Entry",
					reference_name=receipt.name,
				).insert()
			)

		for item in items:
			with self.subTest(item=item.name):
				rows = execute({"item_code": item.name})[1]
				self.assertEqual([row.batch_no for row in rows], [batch.name for batch in batches])
				self.assertEqual([row.indent for row in rows], [0, 1, 2])

		user = make_company_fenced_user("batch-tree-reader@example.com", ["Stock User"], "_Test Company")
		with as_user(user):
			self.assertEqual(len(execute({"item_code": items[2].name})[1]), 3)

		items[1].restrict_to_companies = 1
		items[1].append("allowed_companies", {"company": "_Test Company 1"})
		items[1].save()
		with as_user(user):
			self.assertEqual(execute({"item_code": items[1].name})[1], [])
			self.assertEqual(execute({"item_code": items[2].name})[1], [])

		# A cancelled split breaks the path to the root, even if a descendant still matches.
		frappe.db.set_value("Batch", batches[1].name, "reference_name", None)
		self.assertEqual(execute({"item_code": items[2].name})[1], [])
