# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils.nestedset import (
	NestedSetChildExistsError,
	NestedSetInvalidMergeError,
	NestedSetMultipleRootsError,
	NestedSetRecursionError,
	get_ancestors_of,
	rebuild_tree,
)

test_records = frappe.get_test_records("Item Group")


class TestItem(unittest.TestCase):
	def test_basic_tree(self, records=None):
		min_lft = 1
		max_rgt = frappe.db.sql("select max(rgt) from `tabItem Group`")[0][0]

		if not records:
			records = test_records[2:]

		for item_group in records:
			lft, rgt, parent_item_group = frappe.db.get_value(
				"Item Group", item_group["item_group_name"], ["lft", "rgt", "parent_item_group"]
			)

			if parent_item_group:
				parent_lft, parent_rgt = frappe.db.get_value("Item Group", parent_item_group, ["lft", "rgt"])
			else:
				# root
				parent_lft = min_lft - 1
				parent_rgt = max_rgt + 1

			self.assertTrue(lft)
			self.assertTrue(rgt)
			self.assertTrue(lft < rgt)
			self.assertTrue(parent_lft < parent_rgt)
			self.assertTrue(lft > parent_lft)
			self.assertTrue(rgt < parent_rgt)
			self.assertTrue(lft >= min_lft)
			self.assertTrue(rgt <= max_rgt)

			no_of_children = self.get_no_of_children(item_group["item_group_name"])
			self.assertTrue(rgt == (lft + 1 + (2 * no_of_children)))

			no_of_children = self.get_no_of_children(parent_item_group)
			self.assertTrue(parent_rgt == (parent_lft + 1 + (2 * no_of_children)))

	def get_no_of_children(self, item_group):
		def get_no_of_children(item_groups, no_of_children):
			children = []
			for ig in item_groups:
				children += frappe.db.sql_list(
					"""select name from `tabItem Group`
				where ifnull(parent_item_group, '')=%s""",
					ig or "",
				)

			if len(children):
				return get_no_of_children(children, no_of_children + len(children))
			else:
				return no_of_children

		return get_no_of_children([item_group], 0)

	def test_recursion(self):
		group_b = frappe.get_doc("Item Group", "_Test Item Group B")
		group_b.parent_item_group = "_Test Item Group B - 3"
		self.assertRaises(NestedSetRecursionError, group_b.save)

		# cleanup
		group_b.parent_item_group = "All Item Groups"
		group_b.save()

	def test_rebuild_tree(self):
		rebuild_tree("Item Group", "parent_item_group")
		self.test_basic_tree()

	def move_it_back(self):
		group_b = frappe.get_doc("Item Group", "_Test Item Group B")
		group_b.parent_item_group = "All Item Groups"
		group_b.save()
		self.test_basic_tree()

	def test_move_group_into_another(self):
		# before move
		old_lft, old_rgt = frappe.db.get_value("Item Group", "_Test Item Group C", ["lft", "rgt"])

		# put B under C
		group_b = frappe.get_doc("Item Group", "_Test Item Group B")
		lft, rgt = group_b.lft, group_b.rgt

		group_b.parent_item_group = "_Test Item Group C"
		group_b.save()
		self.test_basic_tree()

		# after move
		new_lft, new_rgt = frappe.db.get_value("Item Group", "_Test Item Group C", ["lft", "rgt"])

		# lft should reduce
		self.assertEqual(old_lft - new_lft, rgt - lft + 1)

		# adjacent siblings, hence rgt diff will be 0
		self.assertEqual(new_rgt - old_rgt, 0)

		self.move_it_back()

	def test_move_group_into_root(self):
		group_b = frappe.get_doc("Item Group", "_Test Item Group B")
		group_b.parent_item_group = ""
		self.assertRaises(NestedSetMultipleRootsError, group_b.save)

		# trick! works because it hasn't been rolled back :D
		self.test_basic_tree()

		self.move_it_back()

	def print_tree(self):
		import json

		print(json.dumps(frappe.db.sql("select name, lft, rgt from `tabItem Group` order by lft"), indent=1))

	def test_move_leaf_into_another_group(self):
		# before move
		old_lft, old_rgt = frappe.db.get_value("Item Group", "_Test Item Group C", ["lft", "rgt"])

		group_b_3 = frappe.get_doc("Item Group", "_Test Item Group B - 3")
		lft, rgt = group_b_3.lft, group_b_3.rgt

		# child of right sibling is moved into it
		group_b_3.parent_item_group = "_Test Item Group C"
		group_b_3.save()
		self.test_basic_tree()

		new_lft, new_rgt = frappe.db.get_value("Item Group", "_Test Item Group C", ["lft", "rgt"])

		# lft should remain the same
		self.assertEqual(old_lft - new_lft, 0)

		# rgt should increase
		self.assertEqual(new_rgt - old_rgt, rgt - lft + 1)

		# move it back
		group_b_3 = frappe.get_doc("Item Group", "_Test Item Group B - 3")
		group_b_3.parent_item_group = "_Test Item Group B"
		group_b_3.save()
		self.test_basic_tree()

	def test_delete_leaf(self):
		# for checking later
		parent_item_group = frappe.db.get_value("Item Group", "_Test Item Group B - 3", "parent_item_group")
		frappe.db.get_value("Item Group", parent_item_group, "rgt")

		ancestors = get_ancestors_of("Item Group", "_Test Item Group B - 3")
		ancestors = frappe.db.sql(
			"""select name, rgt from `tabItem Group`
			where name in ({})""".format(", ".join(["%s"] * len(ancestors))),
			tuple(ancestors),
			as_dict=True,
		)

		frappe.delete_doc("Item Group", "_Test Item Group B - 3")
		records_to_test = test_records[2:]
		del records_to_test[4]
		self.test_basic_tree(records=records_to_test)

		# rgt of each ancestor would reduce by 2
		for item_group in ancestors:
			new_lft, new_rgt = frappe.db.get_value("Item Group", item_group.name, ["lft", "rgt"])
			self.assertEqual(new_rgt, item_group.rgt - 2)

		# insert it back
		frappe.copy_doc(test_records[6]).insert()

		self.test_basic_tree()

	def test_delete_group(self):
		# cannot delete group with child, but can delete leaf
		self.assertRaises(NestedSetChildExistsError, frappe.delete_doc, "Item Group", "_Test Item Group B")

	def test_merge_groups(self):
		frappe.rename_doc("Item Group", "_Test Item Group B", "_Test Item Group C", merge=True)
		records_to_test = test_records[2:]
		del records_to_test[1]
		self.test_basic_tree(records=records_to_test)

		# insert Group B back
		frappe.copy_doc(test_records[3]).insert()
		self.test_basic_tree()

		# move its children back
		for name in frappe.db.sql_list(
			"""select name from `tabItem Group`
			where parent_item_group='_Test Item Group C'"""
		):
			doc = frappe.get_doc("Item Group", name)
			doc.parent_item_group = "_Test Item Group B"
			doc.save()

		self.test_basic_tree()

	def test_merge_leaves(self):
		frappe.rename_doc("Item Group", "_Test Item Group B - 2", "_Test Item Group B - 1", merge=True)
		records_to_test = test_records[2:]
		del records_to_test[3]
		self.test_basic_tree(records=records_to_test)

		# insert Group B - 2back
		frappe.copy_doc(test_records[5]).insert()
		self.test_basic_tree()

	def test_merge_leaf_into_group(self):
		self.assertRaises(
			NestedSetInvalidMergeError,
			frappe.rename_doc,
			"Item Group",
			"_Test Item Group B - 3",
			"_Test Item Group B",
			merge=True,
		)

	def test_merge_group_into_leaf(self):
		self.assertRaises(
			NestedSetInvalidMergeError,
			frappe.rename_doc,
			"Item Group",
			"_Test Item Group B",
			"_Test Item Group B - 3",
			merge=True,
		)
