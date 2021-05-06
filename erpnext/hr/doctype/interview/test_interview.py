# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import datetime
from erpnext.hr.doctype.job_applicant.test_job_applicant import create_job_applicant
from erpnext.hr.doctype.designation.test_designation import create_designation
from frappe.core.doctype.user_permission.test_user_permission import create_user
from erpnext.hr.doctype.interview_round.test_interview_round import create_interview_round
from frappe.utils import get_datetime, add_days, add_to_date
from erpnext.hr.doctype.interview.interview import DuplicateInterviewRoundError


class TestInterview(unittest.TestCase):

	def tearDown(self):
		frappe.db.sql("DELETE FROM `tabInterview Round`")
		frappe.db.sql("DELETE FROM `tabInterview`")
		frappe.db.sql("DELETE FROM `tabExpected Skill Set`")
		frappe.db.sql("DELETE FROM `tabInterview Detail`")

	def test_validations_for_designation(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, designation='_Test_Sales_manager')
		self.assertRaises(DuplicateInterviewRoundError, interview.save)

	def test_status_for_backdated_interviews(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=add_days(get_datetime(), -1), save=True)
		self.assertEqual(interview.status, "In Review")

	def test_notification_on_rescheduling(self):
		from erpnext.hr.doctype.interview.interview import reschedule_interview

		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=add_days(get_datetime(), -4), save_and_submit=True)

		previous_scheduled_date = interview.scheduled_on
		frappe.db.sql("DELETE FROM `tabEmail Queue`")

		reschedule_interview(interview.name, add_days(get_datetime(previous_scheduled_date), 2))
		interview.reload()

		self.assertEqual(interview.scheduled_on, add_days(get_datetime(previous_scheduled_date), 2))

		notification = frappe.get_all("Email Queue", filters={"message": ("like", "%Your Interview session is rescheduled from%")} )
		self.assertIsNotNone(notification)

	def test_notification_for_scheduling(self):
		from erpnext.hr.doctype.interview.interview import send_interview_reminder

		frappe.db.set_value("HR Settings", None, "interview_reminder", 1)
		message = frappe.get_single("HR Settings").interview_reminder_message
		if not message:
			set_reminder_message_and_set_remind_before()


		job_applicant = create_job_applicant()
		scheduled_on = datetime.datetime.now() + datetime.timedelta(minutes=10)

		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=scheduled_on, save_and_submit=True)

		frappe.db.sql("DELETE FROM `tabEmail Queue`")
		send_interview_reminder()

		interview.reload()
		self.assertEqual(interview.reminded, 1)
		notification = frappe.get_all("Email Queue", filters={"message": ("like", "%Interview Reminder%")} )
		self.assertIsNotNone(notification)


	def test_notification_for_feedback_submission(self):
		from erpnext.hr.doctype.interview.interview import send_daily_feedback_reminder

		frappe.db.set_value("HR Settings", None, "interview_feedback_reminder", 1)
		message = frappe.get_single("HR Settings").feedback_reminder_message
		if not message:
			set_reminder_message_and_set_remind_before()


		job_applicant = create_job_applicant()
		scheduled_on = add_days(get_datetime(), -4)
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=scheduled_on, save_and_submit=True)


		frappe.db.sql("DELETE FROM `tabEmail Queue`")
		send_daily_feedback_reminder()

		notification = frappe.get_all("Email Queue", filters={"message": ("like", "%Interview Reminder%")} )
		self.assertIsNotNone(notification)


def set_reminder_message_and_set_remind_before():
	message = "Message for test"
	frappe.db.set_value("HR Settings", None, "interview_reminder_message", message)
	frappe.db.set_value("HR Settings", None, "remind_before", "00:15:00")
	frappe.db.set_value("HR Settings", None, "feedback_reminder_message", message)

def create_interview_and_dependencies(job_applicant, scheduled_on=None, save=False, save_and_submit = False, designation=None ):
	if designation:
		designation=create_designation(designation_name = "_Test_Sales_manager").name

	interviewer_1 = create_user("test_interviewer1@example.com", "Interviewer")
	interviewer_2 = create_user("test_interviewer2@example.com", "Interviewer")

	interview_round = create_interview_round(
		"Technical Round", ["Python", "JS"],
		designation=designation, save=True
	)

	interview = frappe.new_doc("Interview")
	interview.interview_round = interview_round.name
	interview.job_applicant = job_applicant
	interview.scheduled_on = scheduled_on or get_datetime()

	interview.append("interview_detail", {"interviewer": interviewer_1.name})
	interview.append("interview_detail", {"interviewer": interviewer_2.name})

	if save or save_and_submit:
		interview.save()

	if save_and_submit:
		interview.submit()

	return interview
