# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
import json
from collections import deque
from math import floor

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils.data import DATETIME_FORMAT, guess_date_format


class Node(object):
	def __init__(
		self,
		parent: int = None,
		period: (datetime, datetime) = None,
		left: int = None,
		right: int = None,
	):
		self.parent = parent
		self.left_child = left
		self.right_child = right

		self.period = period
		self.difference = 0.0
		self.profit_and_loss_summary = 0.0
		self.balance_sheet_summary = 0.0

	def as_dict(self):
		return dict(
			parent=self.parent,
			left_child=self.left_child,
			right_child=self.right_child,
			period=(self.period[0].strftime(DATETIME_FORMAT), self.period[1].strftime(DATETIME_FORMAT)),
			difference=self.difference,
			profit_and_loss_summary=self.profit_and_loss_summary,
			balance_sheet_summary=self.balance_sheet_summary,
		)

	def __repr__(self):
		return f"Node (parent: {self.parent}, left_child: {self.left_child}, right_child: {self.right_child}, period: {self.period})"


class BTree(object):
	def __init__(self):
		self.btree = []
		self.current_node = None

	def as_list(self):
		lst = []
		for x in self.btree:
			lst.append(x.as_dict())
		return lst

	def bfs(self, from_date: datetime, to_date: datetime):
		node = frappe.new_doc("Nodes")
		node.period_from_date = from_date
		node.period_to_date = to_date
		node.root = None
		node.insert()

		period_list = deque([node])

		while period_list:
			cur_node = period_list.popleft()

			print(cur_node.as_dict())
			delta = cur_node.period_to_date - cur_node.period_from_date
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				left = (
					cur_node.period_from_date,
					(cur_node.period_from_date + relativedelta(days=+cur_floor)),
				)
				left_node = frappe.get_doc(
					{
						"doctype": "Nodes",
						"period_from_date": cur_node.period_from_date,
						"period_to_date": left,
						"root": cur_node.name,
					}
				).insert()
				cur_node.left_child = left_node.name
				period_list.append(left_node)

				right = (
					(cur_node.period_from_date + relativedelta(days=+(cur_floor + 1))),
					cur_node.period_to_date,
				)
				right_node = frappe.get_doc(
					{
						"doctype": "Nodes",
						"period_from_date": right,
						"period_to_date": cur_node.period_to_date,
						"root": cur_node.name,
					}
				).insert()
				cur_node.right_child = right_node
				period_list.append(right_node)

	def dfs(self, from_date: datetime, to_date: datetime):
		root_node = Node(parent=None, period=(getdate(from_date), getdate(to_date)))
		root_node.parent = None

		# add root node to tree
		self.btree.append(root_node)
		cur_node = root_node
		period_list = [root_node]

		while period_list:
			cur_node = period_list.pop()
			cur_node_index = len(self.btree) - 1

			delta = cur_node.period[1] - cur_node.period[0]
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				left = (cur_node.period[0], (cur_node.period[0] + relativedelta(days=+cur_floor)))
				left_node = Node(parent=cur_node_index, period=left)
				self.btree.append(left_node)
				cur_node.left_child = len(self.btree) - 1
				period_list.append(left_node)

				right = ((cur_node.period[0] + relativedelta(days=+(cur_floor + 1))), cur_node.period[1])
				right_node = Node(parent=cur_node_index, period=right)
				self.btree.append(right_node)
				cur_node.right_child = len(self.btree) - 1
				period_list.append(right_node)

	def load_tree(self, tree: list, current_node: dict):
		self.btree = []
		tree = json.loads(tree)
		for x in tree:
			x = frappe._dict(x)
			n = Node(x.parent, None, x.left_child, x.right_child)
			date_format = guess_date_format(x.period[0])
			n.period = (
				datetime.datetime.strptime(x.period[0], date_format),
				datetime.datetime.strptime(x.period[1], date_format),
			)
			n.difference = x.difference
			x.profit_and_loss_summary = x.profit_and_loss_summary
			x.balance_sheet_summary = x.balance_sheet_summary
			self.btree.append(n)

		current_node = frappe._dict(json.loads(current_node))
		n = Node(
			current_node.parent, current_node.period, current_node.left_child, current_node.right_child
		)
		n.period = current_node.period
		n.difference = current_node.difference
		n.profit_and_loss_summary = current_node.profit_and_loss_summary
		n.balance_sheet_summary = current_node.balance_sheet_summary
		self.current_node = n

	def build_tree(self, from_date: datetime, to_date: datetime, alogrithm: str):
		frappe.db.delete("Nodes")
		if alogrithm == "BFS":
			self.bfs(from_date, to_date)

		if alogrithm == "DFS":
			self.dfs(from_date, to_date)

		# set root as current node
		self.current_node = self.btree[0]

	def bisec_left(self):
		pass

	def bisect_right(self):
		pass

	def move_up(self):
		pass


class BisectAccountingStatements(Document):
	def __init__(self, *args, **kwargs):
		super(BisectAccountingStatements, self).__init__(*args, **kwargs)
		if self.tree and self.current_node:
			self.tree_instance = BTree()
			self.tree_instance.load_tree(self.tree, self.current_node)

	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(
				_("From Date: {0} cannot be greater than To date: {1}").format(
					frappe.bold(self.from_date), frappe.bold(self.to_date)
				)
			)

	@frappe.whitelist()
	def build_tree(self):
		self.tree_instance = BTree()
		self.tree_instance.build_tree(self.from_date, self.to_date, self.algorithm)
		print("printing tree")
		for x in self.tree_instance.btree:
			print(x)

		print("Root", self.tree_instance.current_node)

		self.tree = json.dumps(self.tree_instance.as_list())
		self.current_node = json.dumps(self.tree_instance.btree[0].as_dict())

	@frappe.whitelist()
	def bisect_left(self):
		if self.tree_instance.current_node is not None:
			if self.tree_instance.current_node.left_child is not None:
				self.current_node = self.tree_instance.btree[self.tree_instance.current_node.left_child]
				self.current_node = json.dumps(self.current_node.as_dict())
				self.save()
			else:
				frappe.msgprint("No more children on Left")

	@frappe.whitelist()
	def bisect_right(self):
		if self.tree_instance.current_node is not None:
			if self.tree_instance.current_node.right_child is not None:
				self.current_node = self.tree_instance.btree[self.tree_instance.current_node.right_child]
				self.current_node = json.dumps(self.current_node.as_dict())
				self.save()
			else:
				frappe.msgprint("No more children on Right")

	@frappe.whitelist()
	def move_up(self):
		if self.tree_instance.current_node is not None:
			if self.tree_instance.current_node.parent is not None:
				self.current_node = self.tree_instance.btree[self.tree_instance.current_node.parent]
				self.current_node = json.dumps(self.current_node.as_dict())
				self.save()
			else:
				frappe.msgprint("Reached Root")
