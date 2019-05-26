# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import datetime
class QualityReview(Document):

	def get_quality_goal(self, goal):
		# self.reviews = [:]
		doc = frappe.get_doc("Quality Goal", goal)

		for objective in doc.objectives:
			self.append("reviews",
				{
					"objective": objective.objective,
					"target": objective.target,
					"uom": objective.uom
				}
			)

def review():
	now = datetime.datetime.now()
	day = now.day
	weekday = now.strftime("%A")

	for goal in frappe.get_all("Quality Goal",fields=['name', 'frequency', 'date', 'weekday']):
		if goal.frequency == 'Daily':
			create_review(goal.name)

		elif goal.frequency == 'Weekly' and goal.weekday == weekday:
			create_review(goal.name)

		elif goal.frequency == 'Monthly' and goal.date == str(day):
				create_review(goal.name)

def create_review(goal):
	goal = frappe.get_doc("Quality Goal", goal)

	doc = frappe.get_doc({
		"doctype": "Quality Review",
		"goal": name,
		"date": frappe.utils.nowdate()
	})

	for objective in goal.objectives:
		doc.append("reviews",
			{
				"objective": objective.objective,
				"target": objective.target,
				"uom": objective.uom
			}
		)

	doc.insert(ignore_permissions=True)