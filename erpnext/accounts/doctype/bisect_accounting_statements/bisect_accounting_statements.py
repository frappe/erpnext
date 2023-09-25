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


class Node(object):
	def __init__(self):
		self.parent = None
		self.left_child = None
		self.right_child = None

		self.current_period = None
		self.difference = 0.0
		self.profit_and_loss_summary = 0.0
		self.balance_sheet_summary = 0.0

	def update_parent(self):
		pass

	def update_left_child(self):
		pass

	def update_right_child(self):
		pass

	def make_node(
		self,
		parent: int = None,
		period: (datetime, datetime) = None,
		left: int = None,
		right: int = None,
	):
		current_period = period


class BisectAccountingStatements(Document):
	def bfs(self):
		period_list = deque([(getdate(self.from_date), getdate(self.to_date))])
		periods = []
		dates = []
		while period_list:
			cur_frm_date, cur_to_date = period_list.popleft()
			delta = cur_to_date - cur_frm_date
			periods.append((cur_frm_date, cur_to_date, delta))
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				left = (cur_frm_date, (cur_frm_date + relativedelta(days=+cur_floor)))
				right = ((cur_frm_date + relativedelta(days=+(cur_floor + 1))), cur_to_date)
				period_list.append(left)
				period_list.append(right)
		return periods

	def dfs(self):
		period_list = [(getdate(self.from_date), getdate(self.to_date))]
		periods = []
		while period_list:
			cur_frm_date, cur_to_date = period_list.pop()
			delta = cur_to_date - cur_frm_date
			periods.append((cur_frm_date, cur_to_date, delta))
			if delta.days == 0:
				continue
			else:
				cur_floor = floor(delta.days / 2)
				left = (cur_frm_date, (cur_frm_date + relativedelta(days=+cur_floor)))
				right = ((cur_frm_date + relativedelta(days=+(cur_floor + 1))), cur_to_date)
				period_list.append(left)
				period_list.append(right)
		return periods

	@frappe.whitelist()
	def bisect(self):
		if self.algorithm == "BFS":
			periods = self.bfs()

		if self.algorithm == "DFS":
			periods = self.dfs()

		print("Periods: ", len(periods))
		for x in periods:
			print(x)

	def validate(self):
		self.validate_dates()

	def validate_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(
				_("From Date: {0} cannot be greater than To date: {1}").format(
					frappe.bold(self.from_date), frappe.bold(self.to_date)
				)
			)
