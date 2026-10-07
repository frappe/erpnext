import frappe

from erpnext.stock.doctype.item.test_item import make_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry
from erpnext.stock.report.batch_split_tree.batch_split_tree import execute
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
