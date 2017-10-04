# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ChapterMessage(Document):
	def validate(self):
		chapter = frappe.get_doc('Chapter', self.chapter)
		if frappe.session.user != chapter.chapter_head:
			frappe.throw(_('You are not athourize to send message for this Chapter.'))

	def on_update(self):
		chapter = frappe.get_doc('Chapter', self.chapter)
		recipients = [d.user for d in chapter.members]
		message = self.message
		message += "Chapter Title: " + self.chapter
		# chapter_title = self.chapter

		frappe.sendmail(recipients = recipients,
				message = self.message,
				subject = self.subject)
				# reference_doctype=self.doctype, reference_name=self.name)


def get_members_emails(chapterTitle):

	members_list = frappe.get_all('User', fields=['email'],
		filters={'chapter.title': chapterTitle})

	out = []
	for e in members_list:
		if e.email:
				# don't add if holiday
			out.append(e.email)
			print out
	return out