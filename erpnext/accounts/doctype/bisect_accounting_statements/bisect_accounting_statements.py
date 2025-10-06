# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import datetime
from collections import deque
from math import floor

import frappe
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from frappe.utils.data import guess_date_format


class BisectAccountingStatements(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		algorithm: DF.Literal["BFS", "DFS"]
		b_s_summary: DF.Float
		company: DF.Link | None
		current_from_date: DF.Datetime | None
		current_node: DF.Link | None
		current_to_date: DF.Datetime | None
		difference: DF.Float
		from_date: DF.Datetime | None
		p_l_summary: DF.Float
		to_date: DF.Datetime | None
	# end: auto-generated types

	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(
				_("From Date: {0} cannot be greater than To date: {1}").format(
					frappe.bold(self.from_date), frappe.bold(self.to_date)
				)
			)

	def bfs(self, from_date: datetime, to_date: datetime):
		# Make Root node
		node = frappe.new_doc("Bisect Nodes")
		node.root = None
		node.period_from_date = from_date
		node.period_to_date = to_date
		node.insert()

		period_queue = deque([node])
		while period_queue:
			cur_node = period_queue.popleft()
			delta = cur_node.period_to_date - cur_node.period_from_date
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				next_to_date = cur_node.period_from_date + relativedelta(days=+cur_floor)
				left_node = frappe.new_doc("Bisect Nodes")
				left_node.period_from_date = cur_node.period_from_date
				left_node.period_to_date = next_to_date
				left_node.root = cur_node.name
				left_node.generated = False
				left_node.insert()
				cur_node.left_child = left_node.name
				period_queue.append(left_node)

				next_from_date = cur_node.period_from_date + relativedelta(days=+(cur_floor + 1))
				right_node = frappe.new_doc("Bisect Nodes")
				right_node.period_from_date = next_from_date
				right_node.period_to_date = cur_node.period_to_date
				right_node.root = cur_node.name
				right_node.generated = False
				right_node.insert()
				cur_node.right_child = right_node.name
				period_queue.append(right_node)

				cur_node.save()

	def dfs(self, from_date: datetime, to_date: datetime):
		# Make Root node
		node = frappe.new_doc("Bisect Nodes")
		node.root = None
		node.period_from_date = from_date
		node.period_to_date = to_date
		node.insert()

		period_stack = [node]
		while period_stack:
			cur_node = period_stack.pop()
			delta = cur_node.period_to_date - cur_node.period_from_date
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				next_to_date = cur_node.period_from_date + relativedelta(days=+cur_floor)
				left_node = frappe.new_doc("Bisect Nodes")
				left_node.period_from_date = cur_node.period_from_date
				left_node.period_to_date = next_to_date
				left_node.root = cur_node.name
				left_node.generated = False
				left_node.insert()
				cur_node.left_child = left_node.name
				period_stack.append(left_node)

				next_from_date = cur_node.period_from_date + relativedelta(days=+(cur_floor + 1))
				right_node = frappe.new_doc("Bisect Nodes")
				right_node.period_from_date = next_from_date
				right_node.period_to_date = cur_node.period_to_date
				right_node.root = cur_node.name
				right_node.generated = False
				right_node.insert()
				cur_node.right_child = right_node.name
				period_stack.append(right_node)

				cur_node.save()

	@frappe.whitelist()
	def build_tree(self):
		frappe.db.delete("Bisect Nodes")

		# Convert str to datetime format
		dt_format = guess_date_format(self.from_date)
		from_date = datetime.datetime.strptime(self.from_date, dt_format)
		to_date = datetime.datetime.strptime(self.to_date, dt_format)

		if self.algorithm == "BFS":
			self.bfs(from_date, to_date)

		if self.algorithm == "DFS":
			self.dfs(from_date, to_date)

		# set root as current node
		root = frappe.db.get_all("Bisect Nodes", filters={"root": ["is", "not set"]})[0]
		self.current_node = root.name
		self.current_from_date = self.from_date
		self.current_to_date = self.to_date

		self.get_report_summary()
		self.save()

	def get_report_summary(self):
		filters = {
			"company": self.company,
			"filter_based_on": "Date Range",
			"period_start_date": self.current_from_date,
			"period_end_date": self.current_to_date,
			"periodicity": "Yearly",
		}
		pl_summary = frappe.get_doc("Report", "Profit and Loss Statement")
		self.p_l_summary = pl_summary.execute_script_report(filters=filters)[5]
		bs_summary = frappe.get_doc("Report", "Balance Sheet")
		self.b_s_summary = bs_summary.execute_script_report(filters=filters)[5]
		self.difference = abs(self.p_l_summary - self.b_s_summary)

	def update_node(self):
		current_node = frappe.get_doc("Bisect Nodes", self.current_node)
		current_node.balance_sheet_summary = self.b_s_summary
		current_node.profit_loss_summary = self.p_l_summary
		current_node.difference = self.difference
		current_node.generated = True
		current_node.save()

	def current_node_has_summary_info(self):
		"Assertion method"
		return frappe.db.get_value("Bisect Nodes", self.current_node, "generated")

	def fetch_summary_info_from_current_node(self):
		current_node = frappe.get_doc("Bisect Nodes", self.current_node)
		self.p_l_summary = current_node.balance_sheet_summary
		self.b_s_summary = current_node.profit_loss_summary
		self.difference = abs(self.p_l_summary - self.b_s_summary)

	def fetch_or_calculate(self):
		if self.current_node_has_summary_info():
			self.fetch_summary_info_from_current_node()
		else:
			self.get_report_summary()
			self.update_node()

	@frappe.whitelist()
	def bisect_left(self):
		if self.current_node is not None:
			cur_node = frappe.get_doc("Bisect Nodes", self.current_node)
			if cur_node.left_child is not None:
				lft_node = frappe.get_doc("Bisect Nodes", cur_node.left_child)
				self.current_node = cur_node.left_child
				self.current_from_date = lft_node.period_from_date
				self.current_to_date = lft_node.period_to_date
				self.fetch_or_calculate()
				self.save()
			else:
				frappe.msgprint(_("No more children on Left"))

	@frappe.whitelist()
	def bisect_right(self):
		if self.current_node is not None:
			cur_node = frappe.get_doc("Bisect Nodes", self.current_node)
			if cur_node.right_child is not None:
				rgt_node = frappe.get_doc("Bisect Nodes", cur_node.right_child)
				self.current_node = cur_node.right_child
				self.current_from_date = rgt_node.period_from_date
				self.current_to_date = rgt_node.period_to_date
				self.fetch_or_calculate()
				self.save()
			else:
				frappe.msgprint(_("No more children on Right"))

	@frappe.whitelist()
	def move_up(self):
		if self.current_node is not None:
			cur_node = frappe.get_doc("Bisect Nodes", self.current_node)
			if cur_node.root is not None:
				root = frappe.get_doc("Bisect Nodes", cur_node.root)
				self.current_node = cur_node.root
				self.current_from_date = root.period_from_date
				self.current_to_date = root.period_to_date
				self.fetch_or_calculate()
				self.save()
			else:
				frappe.msgprint(_("Reached Root"))
