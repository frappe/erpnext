# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class QualityReview(Document):
	pass

def review():
	day = frappe.utils.getdate().day
	weekday = frappe.utils.getdate().strftime("%A")
	month = frappe.utils.getdate().strftime("%B")

	for goal in frappe.get_list("Quality Goal", fields=['name', 'frequency', 'date', 'weekday']):
		if goal.frequency == 'Daily':
			create_review(goal.name)

		elif goal.frequency == 'Weekly' and goal.weekday == weekday:
			create_review(goal.name)

		elif goal.frequency == 'Monthly' and goal.date == str(day):
			create_review(goal.name)

		elif goal.frequency == 'Quarterly' and goal.data == str(day) and get_quarter(month):
			create_review(goal.name)

def create_review(goal):
	goal = frappe.get_doc("Quality Goal", goal)

	review = frappe.get_doc({
		"doctype": "Quality Review",
		"goal": goal.name,
		"date": frappe.utils.getdate()
	})

	for objective in goal.objectives:
		review.append("reviews",
			{
				"objective": objective.objective,
				"target": objective.target,
				"uom": objective.uom
			}
		)

	review.insert(ignore_permissions=True)

def get_quarter(month):
	if month in  ["January", "April", "July", "October"]:
		return True
	else:
		return False