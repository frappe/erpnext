# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_link_to_form, getdate


class InterviewFeedback(Document):
	def validate(self):
		self.validate_interviewer()
		self.validate_interview_date()
		self.validate_duplicate()
		self.calculate_average_rating()

	def on_submit(self):
		self.update_interview_details()

	def on_cancel(self):
		self.update_interview_details()

	def validate_interviewer(self):
		applicable_interviewers = get_applicable_interviewers(self.interview)
		if self.interviewer not in applicable_interviewers:
			frappe.throw(
				_("{0} is not allowed to submit Interview Feedback for the Interview: {1}").format(
					frappe.bold(self.interviewer), frappe.bold(self.interview)
				)
			)

	def validate_interview_date(self):
		scheduled_date = frappe.db.get_value("Interview", self.interview, "scheduled_on")

		if getdate() < getdate(scheduled_date) and self.docstatus == 1:
			frappe.throw(
				_("{0} submission before {1} is not allowed").format(
					frappe.bold("Interview Feedback"), frappe.bold("Interview Scheduled Date")
				)
			)

	def validate_duplicate(self):
		duplicate_feedback = frappe.db.exists(
			"Interview Feedback",
			{"interviewer": self.interviewer, "interview": self.interview, "docstatus": 1},
		)

		if duplicate_feedback:
			frappe.throw(
				_(
					"Feedback already submitted for the Interview {0}. Please cancel the previous Interview Feedback {1} to continue."
				).format(
					self.interview, get_link_to_form("Interview Feedback", duplicate_feedback)
				)
			)

	def calculate_average_rating(self):
		total_rating = 0
		for d in self.skill_assessment:
			if d.rating:
				total_rating += d.rating

		self.average_rating = flt(
			total_rating / len(self.skill_assessment) if len(self.skill_assessment) else 0
		)

	def update_interview_details(self):
		doc = frappe.get_doc("Interview", self.interview)

		if self.docstatus == 2:
			for entry in doc.interview_details:
				if entry.interview_feedback == self.name:
					entry.average_rating = entry.interview_feedback = entry.comments = entry.result = None
					break
		else:
			for entry in doc.interview_details:
				if entry.interviewer == self.interviewer:
					entry.average_rating = self.average_rating
					entry.interview_feedback = self.name
					entry.comments = self.feedback
					entry.result = self.result

		doc.save()
		doc.notify_update()


@frappe.whitelist()
def get_applicable_interviewers(interview):
	data = frappe.get_all("Interview Detail", filters={"parent": interview}, fields=["interviewer"])
	return [d.interviewer for d in data]
