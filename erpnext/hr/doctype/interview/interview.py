# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, math, datetime
from frappe import _
from frappe.utils import get_link_to_form, today, get_datetime
from frappe.model.document import Document
from erpnext.hr.utils import validate_interviewer_roles


class Interview(Document):

	def validate(self):
		validate_interviewer_roles([d.interviewer for d in self.interview_detail])
		self.validate_duplicate_interview()
		self.set_status()


	def validate_duplicate_interview(self):
		duplicate_interview = frappe.db.exists("Interview", {
				"job_applicant": self.job_applicant,
				"interview_round": self.interview_round,
				"docstatus": 1
			}
		)
		if duplicate_interview:
			frappe.throw(_("Job Applicant are not allowed to appear twice for same Interview round. Interview already scheduled for Job Applicant: {0}, Reference: {1}").format(
				frappe.bold(self.job_applicant),
				frappe.bold(get_link_to_form("Interview", duplicate_interview)))
			)

	def set_status(self):
		if get_datetime() > get_datetime(self.scheduled_on):
			self.status = "In Review"

	def before_submit(self):
		self.original_date = self.scheduled_on

	def before_cancel(self):
		self.status = "Cancelled"

def update_rating(interview_name , interviewer, reference=None, feedback=None, avg_rating=0, revert=0):
	doc = frappe.get_doc("Interview", interview_name)
	total_rating = 0
	feedback_submitted_by_all_interviewer = 1
	for d in doc.interview_detail:
		if d.interviewer == interviewer:
			d.average_rating = avg_rating
			d.average_rating_value = avg_rating
			d.interview_feedback = reference

		if not d.interview_feedback:
			feedback_submitted_by_all_interviewer = 0

		if d.average_rating_value:
			total_rating += d.average_rating_value


	if feedback_submitted_by_all_interviewer:
		doc.status = "Completed"
	else:
		doc.status = "In Review"

	average_rating_value = total_rating/len(doc.interview_detail) if len(doc.interview_detail) else 1
	doc.average_rating = average_rating_value
	doc.average_rating_value = float(average_rating_value)
	doc.save()

	if doc.status == "In Review":
		send_review_reminder(doc.name)

@frappe.whitelist()
def get_interviewer(interview_round):
	interview_round = frappe.get_all("Interviewer", filters={"parent": interview_round}, fields = ["user as interviewer"])
	return interview_round

def get_recipients(name, for_feedback=0):
	interview = frappe.get_doc("Interview", name)
	if for_feedback == 0:
		recipients = [d.interviewer for d in interview.interview_detail]
		recipients .append(frappe.db.get_value("Job Applicant", interview.job_applicant, "email_id"))
	else:
		recipients = [d.interviewer for d in interview.interview_detail if not d.interview_feedback]

	return recipients

@frappe.whitelist()
def reschedule_interview(name, scheduled_on):
	recipients = get_recipients(name)

	interview = frappe.get_doc("Interview", name)
	interview.db_set("scheduled_on", scheduled_on)

	frappe.sendmail(
		recipients= recipients,
		subject='Interview: {0} Rescheduled'.format(interview.name),
		message='<p>Your Interview session is rescheduled from {0} to {1} </p>'.format(
			interview.original_date, scheduled_on),
		reference_doctype=interview.doctype,
		reference_name=interview.name
	)

@frappe.whitelist()
def send_review_reminder(interview_name):
	if frappe.db.get_single_value('Hr Settings', 'interview_feedback_reminder'):
		recipients = get_recipients(interview_name, for_feedback=1)

		doc = frappe.get_doc("Interview", interview_name)
		context = {'doc': doc}

		message = frappe.db.get_single_value('Hr Settings', 'feedback_reminder_message')
		message = frappe.render_template(message, context)

		if len(recipients):
			frappe.sendmail(
				recipients= recipients,
				subject='Interview Feedback Submission Reminder'.format(interview_name),
				message=message,
				reference_doctype="Interview",
				reference_name=interview_name
			)

def send_interview_reminder():
	if frappe.db.get_single_value('Hr Settings', 'interview_feedback_reminder'):
		remind_before = frappe.db.get_single_value('Hr Settings',  'remind_before')
		remind_before = datetime.datetime.strptime(remind_before, '%H:%M:%S')
		reminder_date_time = datetime.datetime.now() + datetime.timedelta(
			hours=remind_before.hour, minutes=remind_before.minute, seconds=remind_before.second)

		interviews =  frappe.get_all("Interview", filters={
			'scheduled_on': ['between', (datetime.datetime.now(), reminder_date_time)],
			'status': "Scheduled",
			'reminded': 0,
			'docstatus': 1})

		if len(interviews):
			message = frappe.db.get_single_value('Hr Settings', 'interview_reminder_message')

		for d in interviews:
			doc = frappe.get_doc("Interview", d.name)
			context = {'doc': doc}
			message = frappe.render_template(message, context)
			recipients = get_recipients(doc.name)

			frappe.sendmail(
				recipients= recipients,
				subject='Interview Reminder '.format(doc.name),
				message=message,
				reference_doctype=doc.doctype,
				reference_name=doc.name
			)

			doc.db_set("reminded", 1)


def send_daily_feedback_reminder():
	interviews = frappe.get_all("Interview", filters={"status": "In Review", "docstatus": 1})

	for d in interviews:
		send_review_reminder(d.name)


@frappe.whitelist()
def get_expected_skill_set(interview_round):
	return frappe.get_all("Expected Skill Set", filters ={"parent": interview_round}, fields=["skill"])

@frappe.whitelist()
def create_interview_feedback(data, interview_name, interviewer):
	import json
	from six import string_types

	if isinstance(data, string_types):
		data = frappe._dict(json.loads(data))

	if frappe.session.user != interviewer:
		frappe.throw(_("Only Interviewer Are allowed to submit Interview Feedback"))

	interview_feedback = frappe.new_doc("Interview Feedback")
	interview_feedback.interview = interview_name
	interview_feedback.interviewer = interviewer

	for d in data.skill_set:
		d = frappe._dict(d)
		interview_feedback.append("skill_assessment", {"skill": d.skill, "rating": d.rating})

	interview_feedback.feedback = data.feedback

	interview_feedback.save()
	interview_feedback.submit()

	frappe.msgprint(_("Interview Feedback Submitted Successfully. Reference {0}").format(get_link_to_form("Interview Feedback", interview_feedback.name)))

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_interviewer_list(doctype, txt, searchfield, start, page_len, filters):
	filters = [
		['Has Role', 'parent', 'like', '%{}%'.format(txt)],
		['Has Role', 'role', '=', 'interviewer'],
		['Has Role', 'parenttype', '=', 'User']
	]

	if filters and isinstance(filters, list):
		filters.extend(filters)

	return frappe.get_all('Has Role', limit_start=start, limit_page_length=page_len,
		filters=filters, fields = ['parent'], as_list=1)
