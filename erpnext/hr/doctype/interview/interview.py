# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_datetime, get_link_to_form


class DuplicateInterviewRoundError(frappe.ValidationError):
	pass


class Interview(Document):
	def validate(self):
		self.validate_duplicate_interview()
		self.validate_designation()
		self.validate_overlap()

	def on_submit(self):
		if self.status not in ["Cleared", "Rejected"]:
			frappe.throw(
				_("Only Interviews with Cleared or Rejected status can be submitted."), title=_("Not Allowed")
			)

	def validate_duplicate_interview(self):
		duplicate_interview = frappe.db.exists(
			"Interview",
			{"job_applicant": self.job_applicant, "interview_round": self.interview_round, "docstatus": 1},
		)

		if duplicate_interview:
			frappe.throw(
				_(
					"Job Applicants are not allowed to appear twice for the same Interview round. Interview {0} already scheduled for Job Applicant {1}"
				).format(
					frappe.bold(get_link_to_form("Interview", duplicate_interview)),
					frappe.bold(self.job_applicant),
				)
			)

	def validate_designation(self):
		applicant_designation = frappe.db.get_value("Job Applicant", self.job_applicant, "designation")
		if self.designation:
			if self.designation != applicant_designation:
				frappe.throw(
					_(
						"Interview Round {0} is only for Designation {1}. Job Applicant has applied for the role {2}"
					).format(
						self.interview_round, frappe.bold(self.designation), applicant_designation
					),
					exc=DuplicateInterviewRoundError,
				)
		else:
			self.designation = applicant_designation

	def validate_overlap(self):
		interviewers = [entry.interviewer for entry in self.interview_details] or [""]

		overlaps = frappe.db.sql(
			"""
			SELECT interview.name
			FROM `tabInterview` as interview
			INNER JOIN `tabInterview Detail` as detail
			WHERE
				interview.scheduled_on = %s and interview.name != %s and interview.docstatus != 2
				and (interview.job_applicant = %s or detail.interviewer IN %s) and
				((from_time < %s and to_time > %s) or
				(from_time > %s and to_time < %s) or
				(from_time = %s))
			""",
			(
				self.scheduled_on,
				self.name,
				self.job_applicant,
				interviewers,
				self.from_time,
				self.to_time,
				self.from_time,
				self.to_time,
				self.from_time,
			),
		)

		if overlaps:
			overlapping_details = _("Interview overlaps with {0}").format(
				get_link_to_form("Interview", overlaps[0][0])
			)
			frappe.throw(overlapping_details, title=_("Overlap"))

	@frappe.whitelist()
	def reschedule_interview(self, scheduled_on, from_time, to_time):
		original_date = self.scheduled_on
		original_from_time = self.from_time
		original_to_time = self.to_time

		self.db_set({"scheduled_on": scheduled_on, "from_time": from_time, "to_time": to_time})
		self.notify_update()

		recipients = get_recipients(self.name)

		try:
			frappe.sendmail(
				recipients=recipients,
				subject=_("Interview: {0} Rescheduled").format(self.name),
				message=_("Your Interview session is rescheduled from {0} {1} - {2} to {3} {4} - {5}").format(
					original_date,
					original_from_time,
					original_to_time,
					self.scheduled_on,
					self.from_time,
					self.to_time,
				),
				reference_doctype=self.doctype,
				reference_name=self.name,
			)
		except Exception:
			frappe.msgprint(
				_("Failed to send the Interview Reschedule notification. Please configure your email account.")
			)

		frappe.msgprint(_("Interview Rescheduled successfully"), indicator="green")


def get_recipients(name, for_feedback=0):
	interview = frappe.get_doc("Interview", name)

	if for_feedback:
		recipients = [d.interviewer for d in interview.interview_details if not d.interview_feedback]
	else:
		recipients = [d.interviewer for d in interview.interview_details]
		recipients.append(frappe.db.get_value("Job Applicant", interview.job_applicant, "email_id"))

	return recipients


@frappe.whitelist()
def get_interviewers(interview_round):
	return frappe.get_all(
		"Interviewer", filters={"parent": interview_round}, fields=["user as interviewer"]
	)


def send_interview_reminder():
	reminder_settings = frappe.db.get_value(
		"HR Settings",
		"HR Settings",
		["send_interview_reminder", "interview_reminder_template"],
		as_dict=True,
	)

	if not reminder_settings.send_interview_reminder:
		return

	remind_before = cstr(frappe.db.get_single_value("HR Settings", "remind_before")) or "01:00:00"
	remind_before = datetime.datetime.strptime(remind_before, "%H:%M:%S")
	reminder_date_time = datetime.datetime.now() + datetime.timedelta(
		hours=remind_before.hour, minutes=remind_before.minute, seconds=remind_before.second
	)

	interviews = frappe.get_all(
		"Interview",
		filters={
			"scheduled_on": ["between", (datetime.datetime.now(), reminder_date_time)],
			"status": "Pending",
			"reminded": 0,
			"docstatus": ["!=", 2],
		},
	)

	interview_template = frappe.get_doc(
		"Email Template", reminder_settings.interview_reminder_template
	)

	for d in interviews:
		doc = frappe.get_doc("Interview", d.name)
		context = doc.as_dict()
		message = frappe.render_template(interview_template.response, context)
		recipients = get_recipients(doc.name)

		frappe.sendmail(
			recipients=recipients,
			subject=interview_template.subject,
			message=message,
			reference_doctype=doc.doctype,
			reference_name=doc.name,
		)

		doc.db_set("reminded", 1)


def send_daily_feedback_reminder():
	reminder_settings = frappe.db.get_value(
		"HR Settings",
		"HR Settings",
		["send_interview_feedback_reminder", "feedback_reminder_notification_template"],
		as_dict=True,
	)

	if not reminder_settings.send_interview_feedback_reminder:
		return

	interview_feedback_template = frappe.get_doc(
		"Email Template", reminder_settings.feedback_reminder_notification_template
	)
	interviews = frappe.get_all(
		"Interview", filters={"status": ["in", ["Under Review", "Pending"]], "docstatus": ["!=", 2]}
	)

	for entry in interviews:
		recipients = get_recipients(entry.name, for_feedback=1)

		doc = frappe.get_doc("Interview", entry.name)
		context = doc.as_dict()

		message = frappe.render_template(interview_feedback_template.response, context)

		if len(recipients):
			frappe.sendmail(
				recipients=recipients,
				subject=interview_feedback_template.subject,
				message=message,
				reference_doctype="Interview",
				reference_name=entry.name,
			)


@frappe.whitelist()
def get_expected_skill_set(interview_round):
	return frappe.get_all("Expected Skill Set", filters={"parent": interview_round}, fields=["skill"])


@frappe.whitelist()
def create_interview_feedback(data, interview_name, interviewer, job_applicant):
	import json

	from six import string_types

	if isinstance(data, string_types):
		data = frappe._dict(json.loads(data))

	if frappe.session.user != interviewer:
		frappe.throw(_("Only Interviewer Are allowed to submit Interview Feedback"))

	interview_feedback = frappe.new_doc("Interview Feedback")
	interview_feedback.interview = interview_name
	interview_feedback.interviewer = interviewer
	interview_feedback.job_applicant = job_applicant

	for d in data.skill_set:
		d = frappe._dict(d)
		interview_feedback.append("skill_assessment", {"skill": d.skill, "rating": d.rating})

	interview_feedback.feedback = data.feedback
	interview_feedback.result = data.result

	interview_feedback.save()
	interview_feedback.submit()

	frappe.msgprint(
		_("Interview Feedback {0} submitted successfully").format(
			get_link_to_form("Interview Feedback", interview_feedback.name)
		)
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_interviewer_list(doctype, txt, searchfield, start, page_len, filters):
	filters = [
		["Has Role", "parent", "like", "%{}%".format(txt)],
		["Has Role", "role", "=", "interviewer"],
		["Has Role", "parenttype", "=", "User"],
	]

	if filters and isinstance(filters, list):
		filters.extend(filters)

	return frappe.get_all(
		"Has Role",
		limit_start=start,
		limit_page_length=page_len,
		filters=filters,
		fields=["parent"],
		as_list=1,
	)


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions

	events = []

	event_color = {
		"Pending": "#fff4f0",
		"Under Review": "#d3e8fc",
		"Cleared": "#eaf5ed",
		"Rejected": "#fce7e7",
	}

	conditions = get_event_conditions("Interview", filters)

	interviews = frappe.db.sql(
		"""
			SELECT DISTINCT
				`tabInterview`.name, `tabInterview`.job_applicant, `tabInterview`.interview_round,
				`tabInterview`.scheduled_on, `tabInterview`.status, `tabInterview`.from_time as from_time,
				`tabInterview`.to_time as to_time
			from
				`tabInterview`
			where
				(`tabInterview`.scheduled_on between %(start)s and %(end)s)
				and docstatus != 2
				{conditions}
			""".format(
			conditions=conditions
		),
		{"start": start, "end": end},
		as_dict=True,
		update={"allDay": 0},
	)

	for d in interviews:
		subject_data = []
		for field in ["name", "job_applicant", "interview_round"]:
			if not d.get(field):
				continue
			subject_data.append(d.get(field))

		color = event_color.get(d.status)
		interview_data = {
			"from": get_datetime("%s %s" % (d.scheduled_on, d.from_time or "00:00:00")),
			"to": get_datetime("%s %s" % (d.scheduled_on, d.to_time or "00:00:00")),
			"name": d.name,
			"subject": "\n".join(subject_data),
			"color": color if color else "#89bcde",
		}

		events.append(interview_data)

	return events
