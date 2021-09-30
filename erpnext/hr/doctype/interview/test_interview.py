# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import datetime
import os
import unittest

import frappe
from frappe import _
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.utils import add_days, getdate, nowtime

from erpnext.hr.doctype.designation.test_designation import create_designation
from erpnext.hr.doctype.interview.interview import DuplicateInterviewRoundError
from erpnext.hr.doctype.job_applicant.test_job_applicant import create_job_applicant


class TestInterview(unittest.TestCase):
	def test_validations_for_designation(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, designation='_Test_Sales_manager', save=0)
		self.assertRaises(DuplicateInterviewRoundError, interview.save)

	def test_notification_on_rescheduling(self):
		job_applicant = create_job_applicant()
		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=add_days(getdate(), -4))

		previous_scheduled_date = interview.scheduled_on
		frappe.db.sql("DELETE FROM `tabEmail Queue`")

		interview.reschedule_interview(add_days(getdate(previous_scheduled_date), 2),
			from_time=nowtime(), to_time=nowtime())
		interview.reload()

		self.assertEqual(interview.scheduled_on, add_days(getdate(previous_scheduled_date), 2))

		notification = frappe.get_all("Email Queue", filters={"message": ("like", "%Your Interview session is rescheduled from%")})
		self.assertIsNotNone(notification)

	def test_notification_for_scheduling(self):
		from erpnext.hr.doctype.interview.interview import send_interview_reminder

		setup_reminder_settings()

		job_applicant = create_job_applicant()
		scheduled_on = datetime.datetime.now() + datetime.timedelta(minutes=10)

		interview = create_interview_and_dependencies(job_applicant.name, scheduled_on=scheduled_on)

		frappe.db.sql("DELETE FROM `tabEmail Queue`")
		send_interview_reminder()

		interview.reload()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue("Subject: Interview Reminder" in email_queue[0].message)

	def test_notification_for_feedback_submission(self):
		from erpnext.hr.doctype.interview.interview import send_daily_feedback_reminder

		setup_reminder_settings()

		job_applicant = create_job_applicant()
		scheduled_on = add_days(getdate(), -4)
		create_interview_and_dependencies(job_applicant.name, scheduled_on=scheduled_on)

		frappe.db.sql("DELETE FROM `tabEmail Queue`")
		send_daily_feedback_reminder()

		email_queue = frappe.db.sql("""select * from `tabEmail Queue`""", as_dict=True)
		self.assertTrue("Subject: Interview Feedback Reminder" in email_queue[0].message)

	def tearDown(self):
		frappe.db.rollback()


def create_interview_and_dependencies(job_applicant, scheduled_on=None, from_time=None, to_time=None, designation=None, save=1):
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
	interview.scheduled_on = scheduled_on or getdate()
	interview.from_time = from_time or nowtime()
	interview.to_time = to_time or nowtime()

	interview.append("interview_details", {"interviewer": interviewer_1.name})
	interview.append("interview_details", {"interviewer": interviewer_2.name})

	if save:
		interview.save()

	return interview

def create_interview_round(name, skill_set, interviewers=[], designation=None, save=True):
	create_skill_set(skill_set)
	interview_round = frappe.new_doc("Interview Round")
	interview_round.round_name = name
	interview_round.interview_type = create_interview_type()
	interview_round.expected_average_rating = 4
	if designation:
		interview_round.designation = designation

	for skill in skill_set:
		interview_round.append("expected_skill_set", {"skill": skill})

	for interviewer in interviewers:
		interview_round.append("interviewer", {
			"user": interviewer
		})

	if save:
		interview_round.save()

	return interview_round

def create_skill_set(skill_set):
	for skill in skill_set:
		if not frappe.db.exists("Skill", skill):
			doc = frappe.new_doc("Skill")
			doc.skill_name = skill
			doc.save()

def create_interview_type(name="test_interview_type"):
	if frappe.db.exists("Interview Type", name):
		return frappe.get_doc("Interview Type", name).name
	else:
		doc = frappe.new_doc("Interview Type")
		doc.name = name
		doc.description = "_Test_Description"
		doc.save()

		return doc.name

def setup_reminder_settings():
	if not frappe.db.exists('Email Template', _('Interview Reminder')):
		base_path = frappe.get_app_path('erpnext', 'hr', 'doctype')
		response = frappe.read_file(os.path.join(base_path, 'interview/interview_reminder_notification_template.html'))

		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _('Interview Reminder'),
			'response': response,
			'subject': _('Interview Reminder'),
			'owner': frappe.session.user,
		}).insert(ignore_permissions=True)

	if not frappe.db.exists('Email Template', _('Interview Feedback Reminder')):
		base_path = frappe.get_app_path('erpnext', 'hr', 'doctype')
		response = frappe.read_file(os.path.join(base_path, 'interview/interview_feedback_reminder_template.html'))

		frappe.get_doc({
			'doctype': 'Email Template',
			'name': _('Interview Feedback Reminder'),
			'response': response,
			'subject': _('Interview Feedback Reminder'),
			'owner': frappe.session.user,
		}).insert(ignore_permissions=True)

	hr_settings = frappe.get_doc('HR Settings')
	hr_settings.interview_reminder_template = _('Interview Reminder')
	hr_settings.feedback_reminder_notification_template = _('Interview Feedback Reminder')
	hr_settings.save()
