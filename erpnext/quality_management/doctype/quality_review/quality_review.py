# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_last_day


class QualityReview(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.quality_management.doctype.quality_review_objective.quality_review_objective import (
			QualityReviewObjective,
		)

		additional_information: DF.Text | None
		date: DF.Date | None
		goal: DF.Link
		procedure: DF.Link | None
		reviews: DF.Table[QualityReviewObjective]
		status: DF.Literal["Open", "Passed", "Failed"]
	# end: auto-generated types

	def validate(self):
		if not self.reviews:
			self.set_objectives()
		elif self.has_value_changed("goal"):
			self.validate_objectives()

		self.set_status()

	def set_objectives(self):
		for d in frappe.get_doc("Quality Goal", self.goal).objectives:
			self.append("reviews", dict(objective=d.objective, target=d.target, uom=d.uom, status="Open"))

	def validate_objectives(self):
		objectives = frappe.get_all(
			"Quality Goal Objective",
			filters={"parent": self.goal, "parenttype": "Quality Goal"},
			pluck="objective",
		)
		for d in self.reviews:
			if d.objective not in objectives:
				frappe.throw(
					_("Row #{0}: Objective {1} is not part of Quality Goal {2}").format(
						d.idx, frappe.bold(d.objective), frappe.bold(self.goal)
					)
				)

	def set_status(self):
		# if any child item is failed, fail the parent
		if not self.reviews or any(d.status not in ("Passed", "Failed") for d in self.reviews):
			self.status = "Open"
		elif any([d.status == "Failed" for d in self.reviews]):
			self.status = "Failed"
		else:
			self.status = "Passed"


def review():
	today = frappe.utils.getdate()
	weekday = today.strftime("%A")
	month = today.strftime("%B")

	for goal in frappe.get_list("Quality Goal", fields=["name", "frequency", "date", "weekday"]):
		if goal.frequency == "Daily":
			create_review(goal.name)

		elif goal.frequency == "Weekly" and goal.weekday == weekday:
			create_review(goal.name)

		elif goal.frequency == "Monthly" and is_review_date(goal.date, today):
			create_review(goal.name)

		elif goal.frequency == "Quarterly" and is_review_date(goal.date, today) and get_quarter(month):
			create_review(goal.name)


def is_review_date(goal_date, today):
	return min(cint(goal_date), get_last_day(today).day) == today.day


def create_review(goal):
	date = frappe.utils.getdate()
	if frappe.db.exists("Quality Review", {"goal": goal, "date": date}):
		return

	review = frappe.get_doc({"doctype": "Quality Review", "goal": goal, "date": date})

	review.insert(ignore_permissions=True)


def get_quarter(month):
	if month in ["January", "April", "July", "October"]:
		return True
	else:
		return False
