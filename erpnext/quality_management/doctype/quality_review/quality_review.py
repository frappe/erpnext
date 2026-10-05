# Copyright (c) 2018, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


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
	day = frappe.utils.getdate().day
	weekday = frappe.utils.getdate().strftime("%A")
	month = frappe.utils.getdate().strftime("%B")

	for goal in frappe.get_list("Quality Goal", fields=["name", "frequency", "date", "weekday"]):
		if goal.frequency == "Daily":
			create_review(goal.name)

		elif goal.frequency == "Weekly" and goal.weekday == weekday:
			create_review(goal.name)

		elif goal.frequency == "Monthly" and goal.date == str(day):
			create_review(goal.name)

		elif goal.frequency == "Quarterly" and goal.date == str(day) and get_quarter(month):
			create_review(goal.name)


def create_review(goal):
	goal = frappe.get_doc("Quality Goal", goal)

	review = frappe.get_doc({"doctype": "Quality Review", "goal": goal.name, "date": frappe.utils.getdate()})

	review.insert(ignore_permissions=True)


def get_quarter(month):
	if month in ["January", "April", "July", "October"]:
		return True
	else:
		return False
