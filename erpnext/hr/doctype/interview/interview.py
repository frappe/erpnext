# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe import _
from frappe.utils import get_link_to_form, get_datetime
from frappe.model.document import Document

class DuplicateInterviewRoundError(frappe.ValidationError): pass

class Interview(Document):
	def validate(self):
		self.validate_duplicate_interview()
		self.validate_designation()

	def before_submit(self):
		self.original_date = self.scheduled_on

	def on_submit(self):
		if self.status not in ['Cleared', 'Rejected']:
			frappe.throw(_('Only Interviews with Cleared or Rejected status can be submitted.'), title=_('Not Allowed'))

	def validate_duplicate_interview(self):
		duplicate_interview = frappe.db.exists('Interview', {
				'job_applicant': self.job_applicant,
				'interview_round': self.interview_round,
				'docstatus': 1
			}
		)

		if duplicate_interview:
			frappe.throw(_('Job Applicants are not allowed to appear twice for the same Interview round. Interview {0} already scheduled for Job Applicant {1}').format(
				frappe.bold(get_link_to_form('Interview', duplicate_interview))),
				frappe.bold(self.job_applicant)
			)

	def validate_designation(self):
		applicant_designation = frappe.db.get_value('Job Applicant', self.job_applicant, 'designation')
		if self.designation :
			if self.designation != applicant_designation:
				frappe.throw(_('Interview Round: {0} is only for Designation: {1}. Job Applicant: {2} has applied for the role: {3}').format(
					self.interview_round, self.designation, applicant_designation), exc = DuplicateInterviewRoundError)
		else:
			self.designation = applicant_designation

	@frappe.whitelist()
	def reschedule_interview(self, scheduled_on):
		recipients = get_recipients(self.name)
		self.db_set('scheduled_on', scheduled_on)
		self.notify_update()

		try:
			frappe.sendmail(
				recipients= recipients,
				subject=_('Interview: {0} Rescheduled').format(interview.name),
				message=_('Your Interview session is rescheduled from {0} to {1}').format(
					interview.original_date, scheduled_on),
				reference_doctype=interview.doctype,
				reference_name=interview.name
			)
		except Exception:
			frappe.msgprint(_('Failed to send the Interview Reschedule notification. Please configure your email account.'))

		frappe.msgprint(_('Interview Rescheduled successfully'), indicator='green')


def get_recipients(name, for_feedback=0):
	interview = frappe.get_doc('Interview', name)

	if for_feedback:
		recipients = [d.interviewer for d in interview.interview_details if not d.interview_feedback]
	else:
		recipients = [d.interviewer for d in interview.interview_details]
		recipients.append(frappe.db.get_value('Job Applicant', interview.job_applicant, 'email_id'))

	return recipients


@frappe.whitelist()
def get_interviewer(interview_round):
	return frappe.get_all('Interviewer', filters={'parent': interview_round}, fields=['user as interviewer'])


def send_interview_reminder():
	reminder_settings = frappe.db.get_value('HR Settings', 'HR Settings',
		['send_interview_reminder', 'interview_reminder_message'])

	if not reminder_settings.send_interview_reminder:
		return

	remind_before = frappe.db.get_single_value('HR Settings',  'remind_before') or '01:00:00'
	remind_before = datetime.datetime.strptime(remind_before, '%H:%M:%S')
	reminder_date_time = datetime.datetime.now() + datetime.timedelta(
		hours=remind_before.hour, minutes=remind_before.minute, seconds=remind_before.second)

	interviews = frappe.get_all('Interview', filters={
		'scheduled_on': ['between', (datetime.datetime.now(), reminder_date_time)],
		'status': 'Scheduled',
		'reminded': 0,
		'docstatus': 1
	})

	for d in interviews:
		doc = frappe.get_doc('Interview', d.name)
		context = {'doc': doc}
		message = frappe.render_template(message, context)
		recipients = get_recipients(doc.name)

		frappe.sendmail(
			recipients= recipients,
			subject=_('Interview Reminder'),
			message=reminder_settings.interview_reminder_message,
			reference_doctype=doc.doctype,
			reference_name=doc.name
		)

		doc.db_set('reminded', 1)


def send_daily_feedback_reminder():
	if not frappe.db.get_single_value('HR Settings', 'send_interview_feedback_reminder'):
		return

	interviews = frappe.get_all('Interview', filters={'status': 'In Review', 'docstatus': 1})

	for entry in interviews:
		recipients = get_recipients(entry.name, for_feedback=1)

		doc = frappe.get_doc('Interview', entry.name)
		context = {'doc': doc}

		message = frappe.db.get_single_value('HR Settings', 'feedback_reminder_message')
		message = frappe.render_template(message, context)

		if len(recipients):
			frappe.sendmail(
				recipients= recipients,
				subject=_('Interview Feedback Submission Reminder'),
				message=message,
				reference_doctype='Interview',
				reference_name=entry.name
			)


@frappe.whitelist()
def get_expected_skill_set(interview_round):
	return frappe.get_all('Expected Skill Set', filters ={'parent': interview_round}, fields=['skill'])


@frappe.whitelist()
def create_interview_feedback(data, interview_name, interviewer, job_applicant):
	import json
	from six import string_types

	if isinstance(data, string_types):
		data = frappe._dict(json.loads(data))

	if frappe.session.user != interviewer:
		frappe.throw(_('Only Interviewer Are allowed to submit Interview Feedback'))

	interview_feedback = frappe.new_doc('Interview Feedback')
	interview_feedback.interview = interview_name
	interview_feedback.interviewer = interviewer
	interview_feedback.job_applicant = job_applicant

	for d in data.skill_set:
		d = frappe._dict(d)
		interview_feedback.append('skill_assessment', {'skill': d.skill, 'rating': d.rating})

	interview_feedback.feedback = data.feedback
	interview_feedback.result = data.result

	interview_feedback.save()
	interview_feedback.submit()

	frappe.msgprint(_('Interview Feedback {0} submitted successfully').format(
		get_link_to_form('Interview Feedback', interview_feedback.name)))


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
