# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest
import webnotes
from webnotes.utils.nestedset import NestedSetRecursionError, NestedSetMultipleRootsError, \
	rebuild_tree, get_ancestors_of

test_records = [
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group",
		"parent_item_group": "All Item Groups",
		"is_group": "No"
	}],
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group Desktops",
		"parent_item_group": "All Item Groups",
		"is_group": "No"
	}],
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group A",
		"parent_item_group": "All Item Groups",
		"is_group": "Yes"
	}],
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group B",
		"parent_item_group": "All Item Groups",
		"is_group": "Yes"
	}],
		[{
			"doctype": "Item Group",
			"item_group_name": "_Test Item Group B - 1",
			"parent_item_group": "_Test Item Group B",
			"is_group": "Yes"
		}],
		[{
			"doctype": "Item Group",
			"item_group_name": "_Test Item Group B - 2",
			"parent_item_group": "_Test Item Group B",
			"is_group": "Yes"
		}],
		[{
			"doctype": "Item Group",
			"item_group_name": "_Test Item Group B - 3",
			"parent_item_group": "_Test Item Group B",
			"is_group": "No"
		}],
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group C",
		"parent_item_group": "All Item Groups",
		"is_group": "Yes"
	}],
		[{
			"doctype": "Item Group",
			"item_group_name": "_Test Item Group C - 1",
			"parent_item_group": "_Test Item Group C",
			"is_group": "Yes"
		}],
		[{
			"doctype": "Item Group",
			"item_group_name": "_Test Item Group C - 2",
			"parent_item_group": "_Test Item Group C",
			"is_group": "Yes"
		}],
	[{
		"doctype": "Item Group",
		"item_group_name": "_Test Item Group D",
		"parent_item_group": "All Item Groups",
		"is_group": "Yes"
	}],
]

class TestItem(unittest.TestCase):
	def test_basic_tree(self, records=None):
		min_lft = 1
		max_rgt = webnotes.conn.sql("select max(rgt) from `tabItem Group`")[0][0]
		
		if not records:
			records = test_records[2:]
		
		for item_group in records:
			item_group = item_group[0]
			lft, rgt, parent_item_group = webnotes.conn.get_value("Item Group", item_group["item_group_name"], 
				["lft", "rgt", "parent_item_group"])
			
			if parent_item_group:
				parent_lft, parent_rgt = webnotes.conn.get_value("Item Group", parent_item_group,
					["lft", "rgt"])
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
			
			children = webnotes.conn.sql("""select count(name) from `tabItem Group`
				where lft>%s and rgt<%s""", (lft, rgt))[0][0]
			self.assertTrue(rgt == (lft + 1 + (2 * children)))
			
	def test_recursion(self):
		group_b = webnotes.bean("Item Group", "_Test Item Group B")
		group_b.doc.parent_item_group = "_Test Item Group B - 3"
		self.assertRaises(NestedSetRecursionError, group_b.save)
	
	def test_rebuild_tree(self):
		rebuild_tree("Item Group", "parent_item_group")
		self.test_basic_tree()
		
	def move_it_back(self):
		group_b = webnotes.bean("Item Group", "_Test Item Group B")
		group_b.doc.parent_item_group = "All Item Groups"
		group_b.save()
		self.test_basic_tree()
		
	def test_move_group_into_another(self):
		previous_lft_rgt = self.get_lft_rgt(get_ancestors_of("Item Group", "_Test Item Group B"))
		
		# put B under C
		group_b = webnotes.bean("Item Group", "_Test Item Group B")
		group_b.doc.parent_item_group = "_Test Item Group C"
		group_b.save()
		self.test_basic_tree()
		
		# TODO check rgt of old parent and new parent
		# check_ancestors_rgt(previous_lft_rgt, "_Test Item Group C", pass)
		
		self.move_it_back()
		
	def check_ancestors_rgt(self, previous_lft_rgt, new_parent, increment):
		if new_parent in previous_lft_rgt:
			pass
		else:
			pass
		
	def get_lft_rgt(self, item_groups):
		item_groups = webnotes.conn.sql("""select name, lft, rgt from `tabItem Group`
			where name in ({})""".format(", ".join(["%s"*len(item_groups)])), tuple(item_groups), as_dict=True)
		
		out = {}
		for item_group in item_groups:
			out[item_group.name] = item_group
		
		return out
		
	def test_move_group_into_root(self):
		group_b = webnotes.bean("Item Group", "_Test Item Group B")
		group_b.doc.parent_item_group = ""
		self.assertRaises(NestedSetMultipleRootsError, group_b.save)

		# trick! works because it hasn't been rolled back :D
		self.test_basic_tree()
		
		# TODO check rgt of old parent and new parent
		
		self.move_it_back()
		
	def test_move_leaf_into_another_group(self):
		group_b_3 = webnotes.bean("Item Group", "_Test Item Group B - 3")
		group_b_3.doc.parent_item_group = "_Test Item Group C"
		group_b_3.save()
		self.test_basic_tree()
		
		# TODO check rgt of old parent and new parent
		
		# move it back
		group_b_3 = webnotes.bean("Item Group", "_Test Item Group B - 3")
		group_b_3.doc.parent_item_group = "_Test Item Group B"
		group_b_3.save()
		self.test_basic_tree()
		
	def test_delete_leaf(self):
		# for checking later
		parent_item_group = webnotes.conn.get_value("Item Group", "_Test Item Group B - 3", "parent_item_group")
		rgt = webnotes.conn.get_value("Item Group", parent_item_group, "rgt")
		
		webnotes.delete_doc("Item Group", "_Test Item Group B - 3")
		records_to_test = test_records[2:]
		del records_to_test[4]
		self.test_basic_tree(records=records_to_test)
		
		# TODO rgt of all ancestors should reduce by 2
		new_rgt = webnotes.conn.get_value("Item Group", parent_item_group, "rgt")
		self.assertEquals(new_rgt, rgt - 2)
		
		# insert it back
		webnotes.bean(copy=test_records[6]).insert()
		self.test_basic_tree()
		
	def test_delete_group(self):
		# TODO cannot delete group with child, but can delete leaf
		pass
		
	def test_merge_groups(self):
		pass
		
	def test_merge_leaves(self):
		pass
		
	def test_merge_leaf_into_group(self):
		# should raise exception
		pass
		
	def test_merge_group_into_leaf(self):
		# should raise exception
		pass