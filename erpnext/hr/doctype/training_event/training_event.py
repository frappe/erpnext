# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.desk.form.load import get_attachments
from frappe.core.doctype.communication.email import make
from frappe.utils.user import get_user_fullname
from frappe.utils import get_url_to_form

STANDARD_USERS = ("Guest", "Administrator")

class TrainingEvent(Document):
	def on_update(self):
		if self.docstatus == 1:
			self.invite_employee()

	def on_update_after_submit(self):
		self.invite_employee()

	def invite_employee(self):
		if self.event_status == "Scheduled" and self.send_email:
			subject = _("""You are invited for to attend {0} - {1} scheduled from {2} to {3} at {4}."""\
				.format(self.type, self.event_name, self.start_time, self.end_time, self.location))

			for emp in self.employees:
				if emp.status== "Open":
					self.send_training_mail(emp)
					emp.status= "Invited"

	def get_link(self, employee, status):
		return get_url_to_form("Training Event",self.name) + "?employee=" + employee + "&status=" + status

	def send_training_mail(self, data):
		full_name = get_user_fullname(frappe.session['user'])
		if full_name == "Guest":
			full_name = "Administrator"

		args = {
			'message': frappe.render_template(self.introduction, data.as_dict()),
			'confirm_link': self.get_link(data.name, "Confirmed"),
			'reject_link': self.get_link(data.name, "Withdrawn"),
			'complete_link': self.get_link(data.name, "Attended"),
			'event_link': get_url_to_form("Training Event",self.name),
			'self_study': 1 if self.type == "Self-Study" else 0,
			'attendance': data.attendance,
			'user_fullname': full_name
		}

		args.update(self.as_dict())
		subject = _("Training Event")
		template = "templates/emails/training_event.html"
		sender = frappe.session.user not in STANDARD_USERS and frappe.session.user or None
		message = frappe.get_template(template).render(args)
		attachments = self.get_attachments()

		self.send_invitation_email(data, sender, subject, message, attachments)

	def send_invitation_email(self, data, sender, subject, message, attachments):
		email = frappe.db.get_value("Employee", data.employee, "company_email")
		if email:
			make(subject = subject, content=message,recipients=email,
				sender=sender,attachments = attachments, send_email=True,
					doctype=self.doctype, name=self.name)["name"]
			frappe.msgprint(_("Email sent to {0}").format(data.employee_name))

	def get_attachments(self):
		if self.include_attachments:
			attachments = [d.name for d in get_attachments(self.doctype, self.name)]
		else:
			attachments = []
		return attachments

@frappe.whitelist(allow_guest=True)
def set_response(event, response):
	doc = frappe.get_doc('Training Event Employee', event)

	if doc:
		doc.status = response
		doc.save()
		frappe.msgprint("Status for this training event as been updated")