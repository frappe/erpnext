# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class Announcement(Document):
	def validate(self):
		self.validate_receiver()
		self.set_posted_by()

	def validate_receiver(self):
		if self.receiver == "Student":
			if not self.student:
				frappe.throw(_("Please select a Student"))
				self.student_group = None
		elif self.receiver == "Student Group":
			if not self.student_group:
				frappe.throw(_("Please select a Student Group"))
				self.student = None
		else:
			self.student_group = None
			self.student = None

	def set_posted_by(self):
		if self.instructor:
			self.posted_by = frappe.db.get_value("Instructor", self.instructor, "instructor_name")
		else:
			self.posted_by = frappe.session.user




def get_message_list(doctype, txt, filters, limit_start, limit_page_length=20):
	user = frappe.session.user
	student = frappe.db.sql("select name from `tabStudent` where student_email_id= %s", user)
	if student:
		sg_list = frappe.db.sql("""select parent from `tabStudent Group Student` as sgs
				where sgs.student = %s """,(student))

		data = frappe.db.sql("""select name, receiver, subject, description, posted_by, modified,
			student, student_group
		    from `tabAnnouncement` as announce
			where (announce.receiver = "Student" and announce.student = %s)
			or (announce.receiver = "Student Group" and announce.student_group in %s)
			or announce.receiver = "All Students"
			and announce.docstatus = 1	
			order by announce.idx asc limit {0} , {1}"""
			.format(limit_start, limit_page_length), (student,sg_list), as_dict = True)

		for announcement in data:
			try:
				num_attachments = frappe.db.sql(""" select count(file_url) from tabFile as file
													where file.attached_to_name=%s 
													and file.attached_to_doctype=%s""",(announcement.name,"Announcement"))

			except IOError or frappe.DoesNotExistError:
				pass
				frappe.local.message_log.pop()

			announcement.num_attachments = num_attachments[0][0]

		return data

def get_list_context(context=None):
	return {
		"show_sidebar": True,
		'no_breadcrumbs': True,
		"title": _("Announcements"),
		"get_list": get_message_list,
		"row_template": "templates/includes/announcement/announcement_row.html"
	}