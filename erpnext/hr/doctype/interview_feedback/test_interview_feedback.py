# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import add_days, get_datetime, flt
from erpnext.hr.doctype.job_applicant.test_job_applicant import create_job_applicant
from erpnext.hr.doctype.interview_round.test_interview_round import create_skill_set
from erpnext.hr.doctype.interview.test_interview import create_interview_and_dependencies
from erpnext.hr.doctype.interview_feedback.interview_feedback import UnexpectedSkillError
class TestInterviewFeedback(unittest.TestCase):

	def tearDown(self):
		frappe.db.sql("DELETE FROM `tabInterview Round`")
		frappe.db.sql("DELETE FROM `tabInterview Feedback`")
		frappe.db.sql("DELETE FROM `tabInterview`")
		frappe.db.sql("DELETE FROM `tabExpected Skill Set`")
		frappe.db.sql("DELETE FROM `tabInterview Detail`")
		frappe.db.sql("DELETE FROM `tabSkill Assessment`")


	def test_validation_for_skill_set(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=add_days(get_datetime(), -1), save_and_submit=True)
		skill_ratings = get_skills_rating(interview.interview_round)

		interviewer = interview.interview_detail[0].interviewer

		interview_feedback = create_interview_feedback(interview.name, interviewer, skill_ratings)
		create_skill_set(['Leadership'])
		interview_feedback.append("skill_assessment", {"skill": 'Leadership', 'rating': 4})
		frappe.set_user(interviewer)

		self.assertRaises(UnexpectedSkillError, interview_feedback.save)

	def test_average_ratings_and_status_on_feedback_submission_and_cancellation(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=add_days(get_datetime(), -1), save_and_submit=True)
		skill_ratings = get_skills_rating(interview.interview_round)

		'''For First Interviewer Feedback'''

		interviewer = interview.interview_detail[0].interviewer
		frappe.set_user(interviewer)

		#calculating Average
		interview_feedback_1 = create_interview_feedback(interview.name, interviewer, skill_ratings, save_and_submit=True)
		total_rating = 0
		for d in interview_feedback_1.skill_assessment:
			if d.rating:
				total_rating += d.rating

		avg_rating = total_rating/len(interview_feedback_1.skill_assessment) if len(interview_feedback_1.skill_assessment) else 1

		self.assertEqual(flt(avg_rating, 3), interview_feedback_1.average_rating_value)

		avg_on_interview_detail = frappe.get_all("Interview Detail",
			filters={"interview_feedback": interview_feedback_1.name},
			fields = ['interviewer', 'average_rating_value']
		)[0]

		# 1. average should be refelected in Interview Detail.
		self.assertEqual(avg_on_interview_detail["average_rating_value"], interview_feedback_1.average_rating_value)

		# 2. Status Should be "In Review" after first feedback submission no matter what it was before
		interview.reload()
		self.assertEqual(interview.status, "In Review")

		'''For Second Interviewer Feedback'''
		interviewer = interview.interview_detail[1].interviewer
		frappe.set_user(interviewer)


		# 3. When all review are submitted it status should be "Completed" for interview
		interview_feedback_2 = create_interview_feedback(interview.name, interviewer, skill_ratings, save_and_submit=True)
		interview.reload()
		self.assertEqual(interview.status, "Completed")

		# 4. if any reviewer cancel there feed back it should be moved again to "In Review"
		interview_feedback_2.cancel()
		interview.reload()
		self.assertEqual(interview.status, "In Review")


def create_interview_feedback(interview, interviewer, skills_ratings, save=False, save_and_submit=False):
	interview_feedback = frappe.new_doc("Interview Feedback")
	interview_feedback.interview = interview
	interview_feedback.interviewer = interviewer

	for rating in skills_ratings:
		interview_feedback.append("skill_assessment", rating)


	if save or save_and_submit:
		interview_feedback.save()

	if save_and_submit:
		interview_feedback.submit()

	return interview_feedback


def get_skills_rating(interview_round):
	import random

	skills = frappe.get_all("Expected Skill Set", filters={"parent": interview_round}, fields = ["skill"])
	for d in skills:
		d["rating"] = random.randint(0, 5)
	return skills
